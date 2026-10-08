"""ZN-fronttest op GitHub Actions: gratis Yahoo-koersen, geen account, geen sleutel, geen orders.

Gebruik (vanuit de map futures):  python -m bot_zn.github [--datatest]
Speelt elke werkdag na het slot alle strategieën uit strategieen.json af met dezelfde code als de laptopversie
(dagelijks.Fronttest + multi.speel_dag) en schrijft alles naar futures/zn_paper/ (journal, signalen, koerscache,
rapporten). DAGRAPPORT.md is leesbaar op github.com; met de Telegram-secrets van de repo komt er ook een melding.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

from .dagelijks import ACCOUNT, Fronttest, setup
from .instellingen import BOT
from .journal_zn import live_trades
from .statistiek import fmt, geld, stats
from .tijd import ET

STATE = BOT.parent / "zn_paper"
STARTDATUM = "2026-10-05"     # eerste handelsdag na het vastleggen van de strategieën (3 okt 2026)
FISCALDATA = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
              "?filter=auction_date:gte:%s,auction_date:lte:%s&fields=auction_date,security_type,original_security_term,"
              "closing_time_comp,inflation_index_security&page[size]=1000")
OORDEEL_MIN_TRADES = 100      # strategieen.json 'oordeel.min_trades_oos'


def veilingen_online(van, tot, open_url=urllib.request.urlopen):
    """Veilingen van 13:00 ET (Notes en Bonds, geen TIPS) uit de gratis API van het Amerikaanse ministerie van
    Financiën. Vult de kalender aan na 2026. Mislukt het, dan blijft alleen de kalender over."""
    try:
        with open_url(FISCALDATA % (van.isoformat(), tot.isoformat()), timeout=20) as r:
            data = json.loads(r.read().decode("utf-8")).get("data", [])
    except Exception:
        return {}
    out = {}
    for x in data:
        if x.get("security_type") not in ("Note", "Bond") or x.get("inflation_index_security") == "Yes":
            continue
        if (x.get("closing_time_comp") or "").strip().upper() != "01:00 PM":
            continue
        d = dt.date.fromisoformat(x["auction_date"])
        out.setdefault(d, []).append("%s %s" % (x.get("original_security_term", "").strip(), x["security_type"]))
    return {d: ", ".join(sorted(set(v))) for d, v in out.items()}


def zet_start(ft):
    """Eerste run: begin bij STARTDATUM (niet bij gisteren), zodat de test pas start na het vastleggen."""
    if not ft.status_pad.exists():
        vorige = ft.kal.vorige_handelsdag(dt.date.fromisoformat(STARTDATUM))
        ft.status_pad.parent.mkdir(parents=True, exist_ok=True)
        ft.status_pad.write_text(json.dumps({"laatst_verwerkt": vorige.isoformat()}, indent=2), encoding="utf-8")


def _trades(sid, journal):
    return [{"datum": d, "netto": n, "mae": m, "R": r} for d, n, m, r in live_trades(ACCOUNT, journal, setup(sid))]


def dagrapport_md(ft):
    """DAGRAPPORT.md: laatste dag + totaal per strategie, plus voortgang naar het oordeel."""
    sig = []
    if ft.signalen_pad.exists():
        import csv
        with open(ft.signalen_pad, newline="", encoding="utf-8") as f:
            sig = list(csv.DictReader(f))
    status = json.loads(ft.status_pad.read_text(encoding="utf-8")) if ft.status_pad.exists() else {}
    laatste = max((r["datum"] for r in sig), default=None)
    namen = {sid: d["naam"] for sid, d in ft.alg["strategieen"].items()}
    m = ["# ZN-bot – dagrapport %s" % (dt.date.fromisoformat(laatste).strftime("%d-%m-%Y") if laatste else "(nog geen dag)"), "",
         "Fronttest (paper) van de 10-jaars Treasury-future op gratis Yahoo-koersen. Er gaat nooit een order naar een "
         "broker. Start: %s. Bijgewerkt %s UTC." % (status.get("start", STARTDATUM),
                                                    dt.datetime.now(dt.timezone.utc).strftime("%d-%m-%Y %H:%M")), ""]
    if laatste:
        m += ["## Laatste handelsdag", "", "| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |",
              "|---|---|---:|---|---:|---:|"]
        for sid in ft.alg["strategieen"]:
            r = next((x for x in sig if x["datum"] == laatste and x["strategie"] == sid), None)
            if r is None:
                m.append("| %s | – | | | | |" % namen[sid])
            elif r["status"] == "gevuld":
                m.append("| %s | %s (%s) | %s | %s → %s | %s | %s |" % (namen[sid], r["richting"], r["uitstapreden"],
                         r["contracten"], r["instap"], r["uitstap"], geld(float(r["netto"])), r["R"]))
            else:
                m.append("| %s | geen trade: %s | | | | |" % (namen[sid], (r["reden"] or r["status"]).replace("_", " ")))
    m += ["", "## Sinds de start", "",
          "| Strategie | Trades | Winrate | Gem. R per trade | t-stat | Netto | Max drawdown | Voortgang oordeel |",
          "|---|---:|---:|---:|---:|---:|---:|---|"]
    for sid in ft.alg["strategieen"]:
        tr = _trades(sid, ft.journal_pad)
        s = stats(tr) if tr else {"trades": 0}
        m.append("| %s | %d | %s | %s | %s | %s | %s | %d / %d trades |" % (
            namen[sid], s.get("trades", 0), fmt("winrate", s.get("winrate")), fmt("expectancy_R", s.get("expectancy_R")),
            fmt("t_stat", s.get("t_stat")), fmt("netto_totaal", s.get("netto_totaal")), fmt("max_dd", s.get("max_dd")),
            s.get("trades", 0), OORDEEL_MIN_TRADES))
    m += ["", "R = winst of verlies gedeeld door het geplande risico (± $200). G is een controlegroep: als die \"wint\", "
          "is dat toeval. Pas na tientallen trades per strategie zegt dit iets. Volledige tabel met grafiek: "
          "`reports/fronttest.html`.", ""]
    pad = ft.map / "DAGRAPPORT.md"
    pad.write_text("\n".join(m), encoding="utf-8")
    if laatste:
        (ft.map / "reports" / "dagrapporten").mkdir(parents=True, exist_ok=True)
        (ft.map / "reports" / "dagrapporten" / ("%s.md" % laatste)).write_text("\n".join(m), encoding="utf-8")
    return pad, laatste, sig


def telegram_tekst(ft, laatste, sig):
    regels = ["ZN fronttest – %s" % laatste]
    for sid in ft.alg["strategieen"]:
        r = next((x for x in sig if x["datum"] == laatste and x["strategie"] == sid), None)
        tot = sum(t["netto"] for t in _trades(sid, ft.journal_pad))
        nu = "–" if r is None else ("%s %sR" % (r["richting"], r["R"]) if r["status"] == "gevuld" else "geen trade")
        regels.append("%s: %s | totaal %s" % (sid, nu, geld(tot)))
    return "\n".join(regels)


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


def run(broker, map_=STATE, nu=None, veilingen_bron=veilingen_online, log=print):
    map_ = Path(map_)
    if (BOT.parent.parent / "KILL").exists() or (map_ / "STOP").exists():
        log("Noodstop (bestand KILL of STOP): niets gedaan.")
        return None
    ft = Fronttest(broker, map_, cfg={}, log=log)
    zet_start(ft)
    vandaag = (nu or dt.datetime.now(ET)).astimezone(ET).date()
    laatste_kal = max(ft.veilingen) if ft.veilingen else vandaag
    if vandaag > laatste_kal - dt.timedelta(days=14):
        extra = veilingen_bron(laatste_kal - dt.timedelta(days=60), vandaag + dt.timedelta(days=7))
        for d, v in extra.items():
            ft.veilingen.setdefault(d, v)
        if extra:
            log("Veilingkalender aangevuld met %d dagen uit fiscaldata.treasury.gov." % len(extra))
    dagen = ft.te_doen(nu)
    log("Te verwerken: %s" % (", ".join(str(d) for d in dagen) or "niets"))
    ft.draai(nu=nu)
    pad, laatste, sig = dagrapport_md(ft)
    return {"ft": ft, "dagen": dagen, "rapport": pad, "laatste": laatste, "sig": sig}


def datatest(broker, map_=STATE):
    from .kalender_zn import Kalender
    from .instellingen import load_calendar, load_strategy
    kal = Kalender(load_calendar(), load_strategy())
    vandaag = dt.datetime.now(ET).date()
    cid = broker.contract_id(*kal.contract_voor(vandaag))
    ok, regels = True, ["Datatest %s UTC" % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")]
    for terug, naam in ((6, "1m"), (40, "5m")):
        van = vandaag - dt.timedelta(days=terug)
        tot = van + dt.timedelta(days=4)
        bars = broker.bars(cid, dt.datetime(van.year, van.month, van.day, tzinfo=ET),
                           dt.datetime(tot.year, tot.month, tot.day, tzinfo=ET))
        per = {}
        for b in bars:
            per.setdefault(b["t"].astimezone(ET).date(), []).append(b)
        regels.append("%s %s (%s t/m %s): %d dagen, %d bars" % (broker.terugval.get(cid, cid), naam, van, tot, len(per), len(bars)))
        for d in sorted(per):
            b = {x["t"].astimezone(ET).strftime("%H:%M"): x for x in per[d]}
            regels.append("  %s: %d bars, eerste %s, laatste %s, 14:25-bar slot %s" % (
                d, len(per[d]), min(b), max(b), b["14:25"]["c"] if "14:25" in b else "–"))
        ok = ok and bool(bars)
    regels.append("Veilingen (fiscaldata): %s" % veilingen_online(vandaag - dt.timedelta(days=30), vandaag))
    tekst = "\n".join(regels)
    print(tekst)
    Path(map_).mkdir(parents=True, exist_ok=True)
    (Path(map_) / "datatest.txt").write_text(tekst + "\n", encoding="utf-8")
    return 0 if ok else 1


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from .broker import VerbindingsFout
    from .yahoo import YahooBroker
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(STATE))
    ap.add_argument("--datatest", action="store_true")
    a = ap.parse_args(argv)
    broker = YahooBroker()
    if a.datatest:
        return datatest(broker, a.map)
    fout_pad = Path(a.map) / "LAATSTE_FOUT.txt"
    try:
        res = run(broker, a.map)
    except VerbindingsFout as e:
        tekst = "Koersen ophalen mislukt (%s). De volgende run haalt de gemiste dagen in." % e
        print(tekst)
        Path(a.map).mkdir(parents=True, exist_ok=True)
        fout_pad.write_text("%s UTC\n%s\n" % (dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), tekst),
                            encoding="utf-8")       # zichtbaar in de repo i.p.v. alleen in het Actions-log
        return 0
    if fout_pad.exists():
        fout_pad.unlink()
    if res is None:
        return 0
    print("Dagrapport: %s" % res["rapport"])
    if res["dagen"] and res["laatste"] and _telegram(telegram_tekst(res["ft"], res["laatste"], res["sig"])):
        print("Telegram-melding verstuurd.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
