"""Forward test MES (paper) via GitHub Actions: elke werkdag na het slot alle strategieën afspelen op gratis Yahoo-data.

Gebruik (vanuit de map futures):  python -m bot_mes.forward [--datatest]
Alles komt in futures/mes_paper/: journal.csv (trades), signalen.csv (per dag en strategie wat er gebeurde),
koersen/dagen.csv (historie), verwerkt.csv, DAGRAPPORT.md. Er gaat nooit een order naar een broker.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

from .account import account_uit_trades
from .kalender import Kalender, contract_code
from .strategieen import Dag, Rekening, maak_dag, prijzen, speel
from .tijd import ET

BOT = Path(__file__).resolve().parent
ROOT = BOT.parent
STATE = ROOT / "mes_paper"
JOURNAL_KOLOMMEN = ["datum", "strategie", "richting", "contracten", "instap_minuut", "instap", "stop", "doel",
                    "uitstap_minuut", "uitstap", "uitstapreden", "bruto", "kosten", "netto", "risico", "R", "mae", "mfe"]
SIGNAAL_KOLOMMEN = ["datum", "strategie", "status", "reden", "trades", "netto", "verwerkt_op"]


def laad():
    with open(BOT / "strategy.json", encoding="utf-8") as f:
        strat = json.load(f)
    with open(ROOT / "calendar.json", encoding="utf-8") as f:
        cal = json.load(f)
    with open(ROOT / "firms" / "topstep_50k.json", encoding="utf-8") as f:
        firm = json.load(f)
    return strat, Kalender(cal, strat), firm


def lees_csv(pad):
    if not Path(pad).exists():
        return []
    with open(pad, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def schrijf_csv(pad, kolommen, rijen, toevoegen=False):
    Path(pad).parent.mkdir(parents=True, exist_ok=True)
    nieuw = not Path(pad).exists() or not toevoegen
    with open(pad, "a" if toevoegen else "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen, extrasaction="ignore")
        if nieuw:
            w.writeheader()
        w.writerows(rijen)


def journal_trades(map_, strategie=None):
    out = []
    for r in lees_csv(Path(map_) / "journal.csv"):
        if strategie and r["strategie"] != strategie:
            continue
        out.append({"datum": dt.date.fromisoformat(r["datum"]), "strategie": r["strategie"], "netto": float(r["netto"]),
                    "R": float(r["R"]) if r["R"] else None, "mae": float(r["mae"] or 0), "richting": r["richting"],
                    "contracten": r["contracten"], "instap": r["instap"], "uitstap": r["uitstap"],
                    "uitstapreden": r["uitstapreden"], "instap_minuut": r["instap_minuut"]})
    return out


class Cache:
    """Per (datum, contract) de prijzen van 10:00, 15:30 en 16:00 (historie voor C, D, E en R)."""

    def __init__(self, pad):
        self.pad = Path(pad)
        self.d = {}
        for r in lees_csv(self.pad):
            self.d[(r["datum"], r["contract"])] = {k: (float(r[k]) if r[k] else None) for k in ("p1000", "p1530", "p1600")}
            self.d[(r["datum"], r["contract"])]["bron"] = r["bron"]

    def zet(self, datum, contract, bars, bron):
        k = (datum.isoformat(), contract)
        if k in self.d and self.d[k]["bron"] == "1m" and bron != "1m":
            return
        p1000, p1530, p1600 = prijzen(bars)
        self.d[k] = {"p1000": p1000, "p1530": p1530, "p1600": p1600, "bron": bron}

    def get(self, datum, contract):
        return self.d.get((datum.isoformat(), contract))

    def bewaar(self):
        schrijf_csv(self.pad, ["datum", "contract", "p1000", "p1530", "p1600", "bron"],
                    [{"datum": d, "contract": c, **{k: ("" if v[k] is None else v[k]) for k in ("p1000", "p1530", "p1600")},
                      "bron": v["bron"]} for (d, c), v in sorted(self.d.items())])


def haal(bron, jm, van, tot, interval):
    from .yahoo import TERUGVAL, ticker
    data = bron.bars(ticker(*jm), van, tot, interval)
    if data:
        return contract_code(*jm), data
    data = bron.bars(TERUGVAL, van, tot, interval)
    return ("ES=F", data) if data else (contract_code(*jm), {})


def historie(d, label, kal, strat, cache):
    out, h = [], d - dt.timedelta(days=strat["forward"]["historie_kalenderdagen"])
    while h < d:
        p = cache.get(h, label) if kal.is_handelsdag(h) else None
        if p:
            vp = cache.get(kal.vorige_handelsdag(h), label)
            dag = Dag(h, label, {}, p["p1000"], p["p1530"], p["p1600"], vp["p1600"] if vp else None, kal.redenen_geen_trade(h))
            if dag.geldig:
                out.append(dag)
        h += dt.timedelta(days=1)
    return out


def speel_dag(d, label, bars, hist, vorig_slot, strat, kal, firm, map_):
    """Alle strategieën voor één dag. Elke strategie heeft een eigen virtueel 50K-account (uit het journal)."""
    dag = maak_dag(d, label, bars, vorig_slot, kal)
    rijen, sig = [], []
    for var in strat["varianten"]:
        eerdere = [t for t in journal_trades(map_, var) if t["datum"] < d]
        acc = account_uit_trades(firm, [(t["datum"], t["netto"], t["mae"]) for t in eerdere])
        wk = d.isocalendar()[:2]
        rek = Rekening(acc.afstand_tot_bodem(), sum(t["netto"] for t in eerdere if t["datum"].isocalendar()[:2] == wk))
        trades, reden = speel(var, dag, hist, strat, rek)
        for t in trades:
            rijen.append(dict({k: t.get(k) for k in JOURNAL_KOLOMMEN}, datum=d.isoformat(),
                              richting="long" if t["richting"] > 0 else "short"))
        sig.append({"datum": d.isoformat(), "strategie": var, "status": "gevuld" if trades else "geen", "reden": reden,
                    "trades": len(trades), "netto": "%.2f" % sum(t["netto"] for t in trades) if trades else ""})
        if trades:     # direct wegschrijven: de volgende strategie leest zijn eigen account opnieuw uit het journal
            schrijf_csv(Path(map_) / "journal.csv", JOURNAL_KOLOMMEN, rijen[-len(trades):], toevoegen=True)
    return sig


def run(bron, map_=STATE, nu=None, strat=None, log=print):
    laden = laad()
    strat = strat or laden[0]
    kal, firm = laden[1], laden[2]
    map_ = Path(map_)
    nu_et = (nu or dt.datetime.now(dt.timezone.utc)).astimezone(ET)
    vandaag = nu_et.date()
    if (ROOT.parent / "KILL").exists() or (map_ / "STOP").exists():
        log("Noodstop (bestand KILL of STOP): niets gedaan.")
        return None
    f = strat["forward"]
    start = dt.date.fromisoformat(f["startdatum"])
    verwerkt = lees_csv(map_ / "verwerkt.csv")
    gedaan = {r["datum"] for r in verwerkt}
    dagen, d = [], start
    while d <= vandaag:
        if kal.is_handelsdag(d) and d.isoformat() not in gedaan and not (d == vandaag and nu_et.strftime("%H:%M") < f["klaar_na_et"]):
            if (vandaag - d).days > f["max_dagen_terug_1m"]:
                verwerkt.append({"datum": d.isoformat(), "contract": "", "status": "gemist", "verwerkt_op": nu_et.isoformat()})
                schrijf_csv(map_ / "signalen.csv", SIGNAAL_KOLOMMEN,
                            [{"datum": d.isoformat(), "strategie": v, "status": "geen", "reden": "gemist"} for v in strat["varianten"]],
                            toevoegen=True)
            else:
                dagen.append(d)
        d += dt.timedelta(days=1)
    cache = Cache(map_ / "koersen" / "dagen.csv")
    per_contract = {}
    for d in dagen:
        per_contract.setdefault(kal.contract_voor(d), []).append(d)
    if not dagen:      # niets te doen: wel de historie alvast opwarmen
        per_contract = {kal.contract_voor(max(start, vandaag)): []}
    klaar = []
    for jm, ds in sorted(per_contract.items()):
        label = contract_code(*jm)
        eerste = ds[0] if ds else max(start, vandaag)
        h_van = max(vandaag - dt.timedelta(days=f["max_dagen_terug_5m"]), eerste - dt.timedelta(days=f["historie_kalenderdagen"]))
        ontbreekt = [x for x in _dagen(h_van, eerste - dt.timedelta(days=1)) if kal.is_handelsdag(x) and not cache.get(x, label)]
        if ontbreekt:
            l5, data5 = haal(bron, jm, ontbreekt[0], ontbreekt[-1], "5m")
            for x, b in data5.items():
                cache.zet(x, l5, b, "5m")
            log("Opwarmen %s: %d dagen met 5-minuutdata." % (l5, len(data5)))
        if not ds:
            continue
        l1, data1 = haal(bron, jm, ds[0], ds[-1], "1m")
        for d in ds:
            bars = {k: v for k, v in data1.get(d, {}).items() if "09:25" <= k <= "16:05"}
            if not any("15:55" <= k <= "15:59" for k in bars):
                if (vandaag - d).days <= f["wachtdagen_bij_geen_data"]:
                    log("%s: nog geen complete 1-minuutdata; volgende run opnieuw." % d)
                    continue
                status, sig = "geen_data", [{"datum": d.isoformat(), "strategie": v, "status": "geen", "reden": "geen_data"}
                                            for v in strat["varianten"]]
            else:
                vp = cache.get(kal.vorige_handelsdag(d), l1)
                sig = speel_dag(d, l1, bars, historie(d, l1, kal, strat, cache), vp["p1600"] if vp else None,
                                strat, kal, firm, map_)
                cache.zet(d, l1, bars, "1m")
                status = "ok"
                log("%s (%s): %d van %d strategieën handelden." % (d, l1, sum(1 for s in sig if s["status"] == "gevuld"), len(sig)))
            for s in sig:
                s["verwerkt_op"] = nu_et.strftime("%Y-%m-%d %H:%M")
            schrijf_csv(map_ / "signalen.csv", SIGNAAL_KOLOMMEN, sig, toevoegen=True)
            verwerkt.append({"datum": d.isoformat(), "contract": l1, "status": status, "verwerkt_op": nu_et.isoformat()})
            klaar.append(d)
    cache.bewaar()
    schrijf_csv(map_ / "verwerkt.csv", ["datum", "contract", "status", "verwerkt_op"], sorted(verwerkt, key=lambda r: r["datum"]))
    from .rapport import dagrapport_md
    pad = dagrapport_md(map_, strat, firm, kal)
    return {"verwerkt": klaar, "rapport": pad, "strat": strat}


def _dagen(van, tot):
    d = van
    while d <= tot:
        yield d
        d += dt.timedelta(days=1)


def _telegram(tekst):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token,
                                     data=json.dumps({"chat_id": chat, "text": tekst[:4000]}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def datatest(bron, map_=STATE):
    strat, kal, _ = laad()
    vandaag = dt.datetime.now(dt.timezone.utc).astimezone(ET).date()
    jm = kal.contract_voor(vandaag)
    regels = ["Datatest %s UTC" % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")]
    ok = True
    for interval, terug in (("1m", 7), ("5m", 20)):
        label, data = haal(bron, jm, vandaag - dt.timedelta(days=terug), vandaag, interval)
        regels.append("%s %s: %d dagen" % (label, interval, len(data)))
        for d in sorted(data):
            b = data[d]
            vol = sum(x[4] for k, x in b.items() if "09:30" <= k <= "15:59")
            regels.append("  %s  %4d bars  10:00 %s  15:30 %s  16:00 %s  volume RTH %.0f" % (d, len(b), *prijzen(b), vol))
        ok = ok and bool(data)
    tekst = "\n".join(regels)
    print(tekst)
    Path(map_).mkdir(parents=True, exist_ok=True)
    (Path(map_) / "datatest.txt").write_text(tekst + "\n", encoding="utf-8")
    return 0 if ok else 1


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(STATE))
    ap.add_argument("--datatest", action="store_true")
    a = ap.parse_args(argv)
    from .yahoo import YahooBron
    if a.datatest:
        return datatest(YahooBron(), a.map)
    res = run(YahooBron(), a.map)
    if res is None:
        return 0
    print("Verwerkt: %s" % (", ".join(str(d) for d in res["verwerkt"]) or "niets nieuws"))
    if res["verwerkt"]:
        from .rapport import telegram_tekst
        if _telegram(telegram_tekst(a.map, res["strat"], res["verwerkt"])):
            print("Telegram-melding verstuurd.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
