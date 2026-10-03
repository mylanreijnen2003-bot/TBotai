"""Historische ZN-data van Databento (GLBX.MDP3, ohlcv-1m, ZN.v.0).

Gebruik (vanuit de daytrading-map):
  python -m bot_zn.data kosten      -> vraagt alleen de kostenschatting op (gratis), koopt niets
  python -m bot_zn.data download    -> toont de kosten, vraagt 'JA', downloadt per jaar

Alleen de bars tussen 08:00 en 15:15 ET worden bewaard (bot_zn/data/ZN_1m_venster.csv); meer is niet nodig.
Daarnaast wordt opgezocht welk contract (bijv. ZNZ6) .v.0 op elke dag was (data/ZN_symbolen.json).
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
DATA_BESTAND = DATA_DIR / "ZN_1m_venster.csv"
SYMBOLEN_BESTAND = DATA_DIR / "ZN_symbolen.json"
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


def _filter_csv(tekst, venster):
    """Databento-CSV (pretty_ts, pretty_px, map_symbols) -> rijen binnen het ET-venster."""
    out = []
    for r in csv.DictReader(io.StringIO(tekst)):
        ts = dt.datetime.strptime(r["ts_event"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC).astimezone(ET)
        hm = ts.strftime("%H:%M")
        if not (venster[0] <= hm <= venster[1]):
            continue
        out.append({"datum": ts.date().isoformat(), "tijd_et": hm, "open": r["open"], "high": r["high"],
                    "low": r["low"], "close": r["close"], "volume": r["volume"],
                    "instrument_id": r["instrument_id"], "symbool": r.get("symbol", "")})
    return out


def download(key, strat, uitvoer=DATA_BESTAND, log=print):
    s, e = periode(strat)
    db = strat["databento"]
    venster = strat["backtest"]["venster_et"]
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
    try:
        raw = _get("symbology.resolve", {"dataset": db["dataset"], "symbols": db["symbool"], "stype_in": db["stype_in"],
                                         "stype_out": "raw_symbol", "start_date": s, "end_date": e}, key, 120)
        res = json.loads(raw).get("result", {}).get(db["symbool"], [])
        with open(Path(uitvoer).parent / SYMBOLEN_BESTAND.name, "w", encoding="utf-8") as f:
            json.dump(res, f)
        log("Contractnamen per periode opgeslagen (%d periodes)." % len(res))
    except (RuntimeError, ValueError, OSError) as ex:
        log("Contractnamen konden niet worden opgehaald (%s); de bot gebruikt dan het instrument-ID." % ex)
    return len(rijen)


def lees_symbolen(pad):
    """[(d0, d1, symbool)] uit ZN_symbolen.json (d1 exclusief), of [] als het bestand er niet is."""
    p = Path(pad)
    if not p.exists():
        return []
    try:
        return sorted((x["d0"], x["d1"], x["s"]) for x in json.loads(p.read_text(encoding="utf-8")))
    except (ValueError, KeyError):
        return []


def symbool_op(perioden, datum_iso):
    for d0, d1, s in perioden:
        if d0 <= datum_iso < d1:
            return s
    return None


def lees_data(pad=DATA_BESTAND):
    """-> [(datum, contract, {'HH:MM': (o,h,l,c)}), ...] gesorteerd. contract = instrument_id van de 14:29-bar
    (of de meest voorkomende in het venster); staat er een contractnaam (bijv. ZNZ6) in ZN_symbolen.json,
    dan wordt die gebruikt, zodat de data aansluit op de contractcodes van de live bot."""
    per = {}
    perioden = lees_symbolen(Path(pad).parent / SYMBOLEN_BESTAND.name)
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
        cid = ids.get("14:29")
        if cid is None:
            tel = {}
            for v in ids.values():
                tel[v] = tel.get(v, 0) + 1
            cid = max(tel, key=tel.get)
        # alleen bars van dat contract (bij een roll midden in het venster)
        bars = {m: b for m, b in d["bars"].items() if ids[m] == cid}
        naam = symbool_op(perioden, ds) if perioden else None
        out.append((dt.date.fromisoformat(ds), naam or cid, bars))
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
    print("Kostenschatting: $%.2f (gedeeld gratis tegoed: $%d, samen met MES en MGC)" % (prijs, strat["databento"]["gratis_tegoed_usd"]))
    (BOT / "reports").mkdir(exist_ok=True)
    with open(BOT / "reports" / "datakosten.txt", "w", encoding="utf-8") as f:
        f.write("%s: kostenschatting ZN.v.0 ohlcv-1m %s t/m %s = $%.2f\n" % (dt.date.today(), s, e, prijs))
    if actie != "download":
        print("Er is niets gekocht. Downloaden: dubbelklik data_zn_download.bat")
        return 0
    if input("Typ JA om deze data te kopen en te downloaden: ").strip() != "JA":
        print("Afgebroken, er is niets gekocht.")
        return 0
    download(key, strat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
