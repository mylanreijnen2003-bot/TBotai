"""Forward test (paper) via GitHub Actions: elke werkdag na het slot alle strategieën afspelen op gratis Yahoo-data.

Gebruik (vanuit de map futures):  python -m bot_mgc.forward
Geen account, geen API-sleutel, geen orders. Alles wordt opgeslagen in futures/mgc_paper/ (journal, signalen,
koerscache, dagrapport) en door de workflow in de repo gecommit.

Waarom dit eerlijk is zonder live mee te kijken: de beslissing om 13:00 ET gebruikt alleen koersen tot en met 13:00
(ROD) en 08:50 (ochtendsignaal) van die dag en eerdere dagen. De bot rekent de dag pas na het slot uit, met
precies dezelfde beslis- en fillcode als de backtest (strategie.beslis + fills.simuleer_dag). Gemiste dagen worden
de volgende run ingehaald, zolang Yahoo de 1-minuutdata nog heeft (30 dagen).
"""
import argparse
import csv
import datetime as dt
import os
import sys
from pathlib import Path

from .account import account_uit_trades
from .fills import simuleer_dag
from .instellingen import BOT, load_calendar, load_firm, load_strategy
from .journal_mgc import live_trades, voeg_live_trade_toe
from .kalender_mgc import Kalender, contract_code
from .logboek import Logboek
from .strategie import (INSTAP_TE_LAAT, WEEKSTOP, beslis, contracten, dag_uit_prijzen, ochtendprijs, signaalprijs,
                        slotprijs)
from .tijd import ET

ACCOUNT = "mgc-paper"
STATE = BOT.parent / "mgc_paper"
CACHE_KOLOMMEN = ["datum", "contract", "ochtend", "signaal", "slot", "bron"]
VERWERKT_KOLOMMEN = ["datum", "contract", "status", "verwerkt_op"]


# ---------------------------------------------------------------- opslag
def _lees_csv(pad):
    if not Path(pad).exists():
        return []
    with open(pad, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _schrijf_csv(pad, kolommen, rijen):
    Path(pad).parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen, extrasaction="ignore")
        w.writeheader()
        w.writerows(rijen)


class Cache:
    """Per (datum, contract) de drie prijzen die de strategie nodig heeft. 1-minuutdata wint van 5-minuutdata."""

    def __init__(self, pad):
        self.pad = Path(pad)
        self.d = {}
        for r in _lees_csv(self.pad):
            self.d[(r["datum"], r["contract"])] = {k: (float(r[k]) if r.get(k) not in (None, "") else None)
                                                   for k in ("ochtend", "signaal", "slot")} | {"bron": r.get("bron", "")}

    def heeft(self, datum, contract):
        return (datum.isoformat(), contract) in self.d

    def zet(self, datum, contract, bars, strat, bron):
        k = (datum.isoformat(), contract)
        if k in self.d and self.d[k].get("bron") == "1m" and bron != "1m":
            return
        self.d[k] = {"ochtend": ochtendprijs(bars, strat), "signaal": signaalprijs(bars, strat),
                     "slot": slotprijs(bars, strat), "bron": bron}

    def get(self, datum, contract):
        return self.d.get((datum.isoformat(), contract))

    def bewaar(self):
        rijen = [{"datum": d, "contract": c, **{k: ("" if v[k] is None else v[k]) for k in ("ochtend", "signaal", "slot")},
                  "bron": v.get("bron", "")} for (d, c), v in sorted(self.d.items())]
        _schrijf_csv(self.pad, CACHE_KOLOMMEN, rijen)


# ---------------------------------------------------------------- data
def haal(bron, jm, van, tot, interval, strat):
    """Probeert het specifieke contract (bijv. GCZ26.CMX), anders GC=F. -> (contractlabel, {datum: bars})."""
    from .yahoo import TERUGVAL, ticker
    data = bron.bars(ticker(*jm), van, tot, interval)
    if data:
        return contract_code(*jm, root="GC"), data
    data = bron.bars(TERUGVAL, van, tot, interval)
    return ("GC=F", data) if data else (contract_code(*jm, root="GC"), {})


def historie(d, label, kal, strat, cache):
    """Geldige dagen vóór d op hetzelfde contract (oudste eerst), uit de cache."""
    start = d - dt.timedelta(days=strat["live"]["historie_kalenderdagen"])
    out, h = [], start
    while h < d:
        if kal.is_handelsdag(h):
            p = cache.get(h, label)
            vp = cache.get(kal.vorige_handelsdag(h), label)
            if p:
                dag = dag_uit_prijzen(h, label, p["signaal"], p["slot"], vp["slot"] if vp else None, kal, strat,
                                      ochtend=p["ochtend"])
                if dag.geldig:
                    out.append(dag)
        h += dt.timedelta(days=1)
    return out


# ---------------------------------------------------------------- één dag
def _week_pnl(d, setup, journal):
    wk = d.isocalendar()[:2]
    return sum(n for dd, n, _, _ in live_trades(ACCOUNT, journal, setup=setup) if dd.isocalendar()[:2] == wk and dd <= d)


def _rij(b):
    return {"rod": None if b.rod is None else "%.6f" % b.rod, "onfh": None if b.onfh is None else "%.6f" % b.onfh,
            "mediaan": None if b.mediaan is None else "%.6f" % b.mediaan, "signaal": b.signaal, "richting": b.richting,
            "stop_punten": b.stop_afstand, "filter": "" if b.mediaan is None else ("zwak" if b.reden == "filter_zwak" else "sterk")}


def speel_dag(d, label, bars, hist, vorig_slot, strat, kal, firm, map_, log):
    """Alle strategieën voor één dag, met dezelfde code als de backtest. Schrijft journal en signalen."""
    journal = Path(map_) / "journal_bot.csv"
    dag = dag_uit_prijzen(d, label, signaalprijs(bars, strat), None, vorig_slot, kal, strat, ochtend=ochtendprijs(bars, strat))
    uit = {}
    for var in strat.get("paper_varianten") or ["A"]:
        b = beslis(dag, hist, strat, var)
        rij = dict(_rij(b), datum=d.isoformat(), account=ACCOUNT, variant=var)
        status, reden = "geen", b.reden
        if b.is_trade:
            setup = "G-" + var
            if _week_pnl(d, setup, journal) <= -strat["weekstop_usd"]:
                reden = WEEKSTOP
            else:
                acc = account_uit_trades(firm, [(x, n, m) for x, n, m, _ in live_trades(ACCOUNT, journal, setup=setup)])
                n, reden = contracten(b.stop_afstand, strat, acc.afstand_tot_bodem())
                b.contracten = rij["contracten"] = n
                if n > 0:
                    sim = simuleer_dag(bars, b.richting, b.stop_afstand, n, strat)
                    if not sim.gevuld:
                        reden = INSTAP_TE_LAAT
                    else:
                        res = sim.resultaat(strat["kosten_per_contract_rt"])
                        t = dict(res, datum=d, variant=var, richting=b.richting, signaal=b.signaal, instap=sim.instap,
                                 uitstap=sim.uitstap, stop=sim.stop, stop_afstand=b.stop_afstand, contracten=n,
                                 instap_bar=sim.instap_bar, uitstap_bar=sim.uitstap_bar_tijd,
                                 uitstapreden=sim.uitstapreden, rod=b.rod, onfh=b.onfh, mediaan=b.mediaan,
                                 fomc=kal.is_fomc(d), notitie="forward test, Yahoo %s 1m" % label)
                        voeg_live_trade_toe(t, ACCOUNT, setup=setup, pad=journal)
                        status, reden = "gevuld", ""
                        rij.update({"instap": t["instap"], "uitstap": t["uitstap"], "uitstapreden": t["uitstapreden"],
                                    "netto": "%.2f" % t["netto"], "R": "%.3f" % (t["R"] or 0)})
        rij.update(status=status, reden=reden)
        log.signaal(rij)
        uit[var] = rij
    return uit


# ---------------------------------------------------------------- de run
def te_verwerken(kal, start, vandaag, nu_et, verwerkt, max_terug):
    """Handelsdagen vanaf start t/m vandaag die nog niet verwerkt zijn. Vandaag pas na 13:45 ET."""
    out, gemist = [], []
    d = start
    while d <= vandaag:
        if kal.is_handelsdag(d) and d.isoformat() not in verwerkt:
            if d == vandaag and nu_et.strftime("%H:%M") < "13:45":
                pass
            elif (vandaag - d).days > max_terug:
                gemist.append(d)
            else:
                out.append(d)
        d += dt.timedelta(days=1)
    return out, gemist


def run(bron, map_=STATE, nu=None, strat=None):
    strat = strat or load_strategy()
    kal = Kalender(load_calendar(), strat)
    firm = load_firm("topstep_50k")
    map_ = Path(map_)
    nu_et = (nu or dt.datetime.now(dt.timezone.utc)).astimezone(ET)
    vandaag = nu_et.date()
    log = Logboek("mgc_paper", map_ / "logs", echo=True, klok=lambda: nu_et)
    if (BOT.parent.parent / "KILL").exists() or (map_ / "STOP").exists():
        log.alarm("Noodstop (bestand KILL of STOP): niets gedaan.")
        return {"verwerkt": [], "gestopt": True}

    # eerste handelsdag ná het vastleggen van de hypotheses (strategy.json forward.startdatum)
    start = dt.date.fromisoformat(strat["forward"]["startdatum"])

    verwerkt_rijen = _lees_csv(map_ / "verwerkt.csv")
    verwerkt = {r["datum"] for r in verwerkt_rijen}
    dagen, gemist = te_verwerken(kal, start, vandaag, nu_et, verwerkt, strat["forward"]["max_dagen_terug_1m"])
    for d in gemist:
        log.waarschuwing("%s gemist: Yahoo heeft geen 1-minuutdata meer van die dag." % d)
        verwerkt_rijen.append({"datum": d.isoformat(), "contract": "", "status": "gemist", "verwerkt_op": nu_et.isoformat()})
        for var in strat.get("paper_varianten") or ["A"]:
            log.signaal({"datum": d.isoformat(), "account": ACCOUNT, "variant": var, "status": "geen", "reden": "gemist"})
    cache = Cache(map_ / "koersen" / "dagen.csv")
    klaar = []

    per_contract = {}
    for d in dagen:
        per_contract.setdefault(kal.contract_voor(d), []).append(d)
    if not dagen:   # niets te doen: wel alvast de historie opwarmen (en zo controleren dat Yahoo werkt)
        jm = kal.contract_voor(max(start, vandaag))
        oudste = vandaag - dt.timedelta(days=strat["forward"]["max_dagen_terug_5m"])
        label = contract_code(*jm, root="GC")
        ontbreekt = [h for h in _dagen(oudste, vandaag) if kal.is_handelsdag(h) and not cache.heeft(h, label)]
        if ontbreekt:
            label5, data5 = haal(bron, jm, ontbreekt[0], ontbreekt[-1], "5m", strat)
            for h, bars in data5.items():
                cache.zet(h, label5, bars, strat, "5m")
            log.info("Opwarmen %s: %d dagen met 5-minuutdata (nog geen dag om te verwerken; start %s)." % (
                label5, len(data5), start))
    for jm, ds in sorted(per_contract.items()):
        # opwarmen: 5-minuutdata voor de historie (alleen wat nog ontbreekt en Yahoo nog heeft)
        oudste = vandaag - dt.timedelta(days=strat["forward"]["max_dagen_terug_5m"])
        h_van = max(oudste, ds[0] - dt.timedelta(days=strat["live"]["historie_kalenderdagen"]))
        label = contract_code(*jm, root="GC")
        ontbreekt = [h for h in _dagen(h_van, ds[-1]) if kal.is_handelsdag(h) and not cache.heeft(h, label)]
        if ontbreekt:
            label5, data5 = haal(bron, jm, ontbreekt[0], ontbreekt[-1], "5m", strat)
            for h, bars in data5.items():
                cache.zet(h, label5, bars, strat, "5m")
            log.info("Opwarmen %s: %d dagen met 5-minuutdata." % (label5, len(data5)))
        label1, data1 = haal(bron, jm, ds[0], ds[-1], "1m", strat)
        for d in ds:
            bars = data1.get(d, {})
            for h, b in data1.items():
                if h < d:
                    cache.zet(h, label1, b, strat, "1m")
            if not bars or slotprijs(bars, strat) is None:
                if (vandaag - d).days <= strat["forward"]["wachtdagen_bij_geen_data"]:
                    log.info("%s: nog geen complete 1-minuutdata van %s; volgende run opnieuw." % (d, label1))
                    continue
                status, uitkomst = "geen_data", None
                for var in strat.get("paper_varianten") or ["A"]:
                    log.signaal({"datum": d.isoformat(), "account": ACCOUNT, "variant": var, "status": "geen",
                                 "reden": "geen_data"})
            else:
                redenen = kal.redenen_geen_trade(d)
                vp = cache.get(kal.vorige_handelsdag(d), label1)
                hist = historie(d, label1, kal, strat, cache)
                if redenen:
                    status = "geen_handel"
                    for var in strat.get("paper_varianten") or ["A"]:
                        log.signaal({"datum": d.isoformat(), "account": ACCOUNT, "variant": var, "status": "geen",
                                     "reden": "+".join(redenen)})
                    uitkomst = None
                else:
                    uitkomst = speel_dag(d, label1, bars, hist, vp["slot"] if vp else None, strat, kal, firm, map_, log)
                    status = "ok"
                    n = sum(1 for r in uitkomst.values() if r["status"] == "gevuld")
                    log.info("%s (%s): %d van %d strategieën handelden; historie %d dagen." % (
                        d, label1, n, len(uitkomst), len(hist)))
                cache.zet(d, label1, bars, strat, "1m")
            verwerkt_rijen.append({"datum": d.isoformat(), "contract": label1, "status": status, "verwerkt_op": nu_et.isoformat()})
            klaar.append((d, uitkomst))
    cache.bewaar()
    _schrijf_csv(map_ / "verwerkt.csv", VERWERKT_KOLOMMEN, sorted(verwerkt_rijen, key=lambda r: r["datum"]))
    return {"verwerkt": klaar, "gestopt": False, "strat": strat, "kal": kal, "firm": firm, "start": start}


def _dagen(van, tot):
    d = van
    while d <= tot:
        yield d
        d += dt.timedelta(days=1)


def rapporteer(res, map_=STATE):
    """Dagrapport (HTML + Markdown voor GitHub) en een korte Telegram-melding als daar secrets voor zijn."""
    from .dagrapport import schrijf_dagrapport, schrijf_dagrapport_md, telegram_tekst
    strat, kal, firm = res["strat"], res["kal"], res["firm"]
    rijen = [r for r in _lees_csv(Path(map_) / "verwerkt.csv") if r["status"] in ("ok", "geen_handel", "geen_data")]
    if not rijen:
        return None
    laatste = dt.date.fromisoformat(max(r["datum"] for r in rijen))
    schrijf_dagrapport(laatste, ACCOUNT, map_, strat, firm, kal)
    md = schrijf_dagrapport_md(laatste, ACCOUNT, map_, strat, firm, kal)
    if res["verwerkt"]:
        tekst = telegram_tekst(laatste, ACCOUNT, map_, strat, [d for d, _ in res["verwerkt"]])
        if _telegram(tekst):
            print("Telegram-melding verstuurd.")
    return md


def _telegram(tekst):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        import json
        import urllib.request
        req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token,
                                     data=json.dumps({"chat_id": chat, "text": tekst[:4000],
                                                      "disable_web_page_preview": True}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def datatest(bron):
    """Laat per dag zien welke prijzen de bot uit Yahoo haalt (1m en 5m), zonder iets op te slaan."""
    strat = load_strategy()
    kal = Kalender(load_calendar(), strat)
    vandaag = dt.datetime.now(dt.timezone.utc).astimezone(ET).date()
    jm = kal.contract_voor(vandaag)
    ok = True
    for interval, terug in (("1m", 7), ("5m", 20)):
        label, data = haal(bron, jm, vandaag - dt.timedelta(days=terug), vandaag, interval, strat)
        print("%s %s: %d dagen" % (label, interval, len(data)))
        for d in sorted(data):
            b = data[d]
            print("  %s  %3d bars  08:50 %s  13:00 %s  13:30 %s" % (d, len(b), ochtendprijs(b, strat), signaalprijs(b, strat),
                                                                 slotprijs(b, strat)))
        ok = ok and bool(data)
    return 0 if ok else 1


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(STATE))
    ap.add_argument("--datatest", action="store_true", help="alleen controleren of Yahoo data geeft; schrijft niets")
    a = ap.parse_args(argv)
    from .yahoo import YahooBron
    if a.datatest:
        return datatest(YahooBron())
    res = run(YahooBron(), a.map)
    if res.get("gestopt"):
        return 0
    md = rapporteer(res, a.map)
    print("Verwerkt: %s" % (", ".join(str(d) for d, _ in res["verwerkt"]) or "niets nieuws"))
    if md:
        print("Dagrapport: %s" % md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
