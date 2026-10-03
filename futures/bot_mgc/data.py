"""Historische goud-data van Databento (GLBX.MDP3, ohlcv-1m, GC.v.0). GC heeft dezelfde prijs als MGC.

Gebruik (vanuit de daytrading-map):
  python -m bot_mgc.data kosten      -> vraagt alleen de kostenschatting op (gratis), koopt niets
  python -m bot_mgc.data download    -> toont de kosten, vraagt 'JA', downloadt per jaar

Alleen de bars tussen 08:15-08:55 ET (ochtendsignaal, strategie D/E) en 12:30-13:40 ET worden bewaard
(bot_mgc/data/GC_1m_venster.csv); meer is niet nodig. De prijs van de data verandert daar niet door.
De API-key staat in .env als DATABENTO_API_KEY en komt nooit in code of logs.
"""
import base64
import csv
import datetime as dt
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .instellingen import BOT, lees_env, load_strategy
from .tijd import ET, UTC

BASIS = "https://hist.databento.com/v0/"
DATA_DIR = BOT / "data"
DATA_BESTAND = DATA_DIR / "GC_1m_venster.csv"
KOLOMMEN = ["datum", "tijd_et", "open", "high", "low", "close", "volume", "instrument_id", "symbool"]


def _get(endpoint, params, key, timeout=600):
    url = BASIS + endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Basic " + base64.b64encode((key + ":").encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError("Databento gaf fout %s: %s" % (e.code, body)) from None


def periode(strat, vandaag=None):
    """Start = datastart (2010-06-06). Eind = eerste dag van de huidige maand (dus t/m de laatste volle maand)."""
    vandaag = vandaag or dt.date.today()
    return strat["backtest"]["data_start"], vandaag.replace(day=1).isoformat()


def kosten(key, strat, start=None, eind=None):
    s, e = periode(strat)
    db = strat["databento"]
    raw = _get("metadata.get_cost", {"dataset": db["dataset"], "symbols": db["symbool"], "schema": db["schema"],
                                     "stype_in": db["stype_in"], "start": start or s, "end": eind or e}, key, 120)
    return float(json.loads(raw))


def vensters(strat):
    bt = strat["backtest"]
    return [tuple(v) for v in bt.get("vensters_et") or [bt["venster_et"]]]


def _filter_csv(tekst, venster):
    """Databento-CSV (pretty_ts, pretty_px, map_symbols) -> rijen binnen de ET-vensters.
    venster = (van, tot) of een lijst daarvan."""
    lijst = [venster] if isinstance(venster[0], str) else list(venster)
    out = []
    for r in csv.DictReader(io.StringIO(tekst)):
        ts = dt.datetime.strptime(r["ts_event"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC).astimezone(ET)
        hm = ts.strftime("%H:%M")
        if not any(v[0] <= hm <= v[1] for v in lijst):
            continue
        out.append({"datum": ts.date().isoformat(), "tijd_et": hm, "open": r["open"], "high": r["high"],
                    "low": r["low"], "close": r["close"], "volume": r["volume"],
                    "instrument_id": r["instrument_id"], "symbool": r.get("symbol", "")})
    return out


def download(key, strat, uitvoer=DATA_BESTAND, log=print):
    s, e = periode(strat)
    db = strat["databento"]
    venster = vensters(strat)
    rijen = []
    jaar_start = dt.date.fromisoformat(s)
    eind = dt.date.fromisoformat(e)
    while jaar_start < eind:
        jaar_eind = min(dt.date(jaar_start.year + 1, 1, 1), eind)
        log("Download %s t/m %s ..." % (jaar_start, jaar_eind - dt.timedelta(days=1)))
        raw = _get("timeseries.get_range", {
            "dataset": db["dataset"], "symbols": db["symbool"], "schema": db["schema"], "stype_in": db["stype_in"],
            "start": jaar_start.isoformat(), "end": jaar_eind.isoformat(), "encoding": "csv",
            "pretty_px": "true", "pretty_ts": "true", "map_symbols": "true", "compression": "none"}, key)
        nieuw = _filter_csv(raw.decode("utf-8"), venster)
        log("  %d bars in het venster" % len(nieuw))
        rijen.extend(nieuw)
        jaar_start = jaar_eind
    Path(uitvoer).parent.mkdir(parents=True, exist_ok=True)
    with open(uitvoer, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KOLOMMEN)
        w.writeheader()
        w.writerows(rijen)
    log("Opgeslagen: %s (%d bars)" % (uitvoer, len(rijen)))
    return len(rijen)


def lees_data(pad=DATA_BESTAND):
    """-> [(datum, contract, {'HH:MM': (o,h,l,c)}), ...] gesorteerd. contract = instrument_id van de 12:59-bar
    (of de meest voorkomende in het venster)."""
    per = {}
    with open(pad, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = per.setdefault(r["datum"], {"bars": {}, "ids": {}, "sym": {}})
            d["bars"][r["tijd_et"]] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
            d["ids"][r["tijd_et"]] = r["instrument_id"]
            d["sym"][r["instrument_id"]] = r.get("symbool", "")
    out = []
    for ds in sorted(per):
        d = per[ds]
        ids = d["ids"]
        cid = ids.get("12:59")
        if cid is None:
            tel = {}
            for v in ids.values():
                tel[v] = tel.get(v, 0) + 1
            cid = max(tel, key=tel.get)
        # alleen bars van dat contract (bij een roll midden in het venster)
        bars = {m: b for m, b in d["bars"].items() if ids[m] == cid}
        out.append((dt.date.fromisoformat(ds), cid, bars))
    return out


def v0_rolls(ruwe):
    """Eerste dagen waarop .v.0 een ander contract (instrument_id) heeft dan de vorige dag in de data."""
    rolls, vorige = [], None
    for datum, cid, _ in ruwe:
        if vorige is not None and cid != vorige:
            rolls.append(datum)
        vorige = cid
    return rolls


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:] if argv is None else argv
    actie = argv[0] if argv else "kosten"
    strat = load_strategy()
    key = lees_env().get("DATABENTO_API_KEY")
    if not key:
        print("Geen DATABENTO_API_KEY gevonden. Zet in het bestand .env (in de daytrading-map) een regel:\n"
              "  DATABENTO_API_KEY=db-...")
        return 1
    s, e = periode(strat)
    print("Databento %s %s %s, %s t/m %s (eind exclusief)" % (strat["databento"]["dataset"], strat["databento"]["schema"],
                                                            strat["databento"]["symbool"], s, e))
    prijs = kosten(key, strat)
    print("Kostenschatting: $%.2f (gedeeld gratis tegoed: $%d, samen met MES en ZN)" % (prijs, strat["databento"]["gratis_tegoed_usd"]))
    (BOT / "reports").mkdir(exist_ok=True)
    with open(BOT / "reports" / "datakosten.txt", "w", encoding="utf-8") as f:
        f.write("%s: kostenschatting GC.v.0 ohlcv-1m %s t/m %s = $%.2f\n" % (dt.date.today(), s, e, prijs))
    if actie != "download":
        print("Er is niets gekocht. Downloaden: dubbelklik data_mgc_download.bat")
        return 0
    if input("Typ JA om deze data te kopen en te downloaden: ").strip() != "JA":
        print("Afgebroken, er is niets gekocht.")
        return 0
    download(key, strat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
