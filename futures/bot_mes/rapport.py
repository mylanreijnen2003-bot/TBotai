"""DAGRAPPORT.md (leesbaar op github.com) en de korte Telegram-melding voor de MES-bot."""
import datetime as dt
from pathlib import Path

from .account import account_uit_trades
from .forward import journal_trades, lees_csv
from .statistiek import fmt, geld, stats

REDENEN = {
    "geen_bias": "geen duidelijke trend om 14:45", "geen_trigger": "geen instapsignaal na een pullback",
    "pullback_te_ver_van_vwap": "pullback bleef te ver boven/onder de VWAP", "instap_buiten_venster": "signaal na 15:45",
    "filter_zwak": "beweging kleiner dan normaal (filter)", "te_weinig_historie": "nog te weinig historie",
    "geen_richting": "geen richting", "geen_data": "geen koersen", "stop_te_klein": "stop kleiner dan 2 punten",
    "stop_te_groot": "stop te groot voor $200 risico", "gehalveerd_naar_0": "virtueel account te dicht bij de bodem",
    "weekstop": "weekstop (−$800 deze week)", "fomc": "FOMC-dag", "feestdag": "beursfeestdag",
    "vervroegde_sluiting": "vervroegde sluiting", "kerstperiode": "kerstperiode", "gemist": "gemist (geen data meer)",
    "geen_uitbraak": "koers bleef binnen de ruisband", "trailing": "trailing stop (band/VWAP)",
    "tijd": "tijdsuitstap", "stop": "stop geraakt", "doel": "doel geraakt", "tijd_geen_bar": "laatste koers",
}


def tekst(r):
    return " + ".join(REDENEN.get(x, x) for x in str(r or "").split("+") if x) or "–"


def oordeel(trades, strat, var):
    f = strat["forward_test"]
    tr = trades.get(var, [])
    m = stats(tr) if tr else {"trades": 0}
    ex = m.get("expectancy_R")
    exb = stats(trades["B"]).get("expectancy_R") if trades.get("B") else None
    exr = stats(trades["R"]).get("expectancy_R") if trades.get("R") else None
    lijst = [m["trades"] >= f["min_trades"], ex is not None and ex >= f["min_expectancy_R"],
             (m.get("t_stat") or -9) >= f["min_t_stat"], (m.get("profit_factor") or 0) >= f["min_profit_factor"],
             m.get("max_dd") is not None and m["max_dd"] < f["max_drawdown_usd"],
             ex is not None and exb is not None and ex > exb, ex is not None and exr is not None and ex > exr]
    if m["trades"] < f["min_trades"]:
        return "loopt (%d/%d trades)" % (m["trades"], f["min_trades"])
    return "GO" if all(lijst) else "NO-GO"


def dagrapport_md(map_, strat, firm, kal=None):
    map_ = Path(map_)
    sig = lees_csv(map_ / "signalen.csv")
    laatste = max((r["datum"] for r in sig if r["reden"] != "gemist"), default=None)
    trades = {v: journal_trades(map_, v) for v in strat["varianten"]}
    naam = {v: d["naam"] for v, d in strat["varianten"].items()}
    titel = dt.date.fromisoformat(laatste).strftime("%d-%m-%Y") if laatste else "(nog geen dag)"
    m = ["# MES-bot – dagrapport %s" % titel, "",
         "Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een "
         "order naar een broker. Start %s. Bijgewerkt %s UTC." % (strat["forward"]["startdatum"],
                                                                  dt.datetime.now(dt.timezone.utc).strftime("%d-%m-%Y %H:%M")), ""]
    if laatste:
        m += ["## Laatste handelsdag", "", "| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |",
              "|---|---|---:|---|---:|---:|"]
        d = dt.date.fromisoformat(laatste)
        for v in strat["varianten"]:
            vt = [t for t in trades[v] if t["datum"] == d]
            r = next((x for x in sig if x["datum"] == laatste and x["strategie"] == v), {})
            if vt:
                for t in vt:
                    m.append("| %s | %s, %s | %s | %s %s → %s | %s | %s |" % (naam[v], t["richting"], tekst(t["uitstapreden"]),
                             t["contracten"], t["instap_minuut"], t["instap"], t["uitstap"], geld(t["netto"]),
                             fmt("expectancy_R", t["R"])))
            else:
                m.append("| %s | geen trade: %s | | | | |" % (naam[v], tekst(r.get("reden"))))
    m += ["", "## Sinds de start", "",
          "| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for v in strat["varianten"]:
        tr = trades[v]
        s = stats(tr) if tr else {"trades": 0}
        acc = account_uit_trades(firm, [(t["datum"], t["netto"], t["mae"]) for t in tr])
        oo = oordeel(trades, strat, v) if v in strat["richtinggevende_varianten"] else "vergelijking"
        m.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (naam[v], s.get("trades", 0), fmt("winrate", s.get("winrate")),
                 fmt("expectancy_R", s.get("expectancy_R")), fmt("t_stat", s.get("t_stat")), fmt("netto_totaal", s.get("netto_totaal")),
                 fmt("max_dd", s.get("max_dd")), geld(acc.saldo), oo))
    f = strat["forward_test"]
    m += ["", "Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij %d trades: "
          "expectancy ≥ +%.2fR, t-stat ≥ %.2f, profit factor ≥ %.2f, max drawdown < $%d, beter dan B én R. Elke strategie "
          "heeft een eigen virtueel Topstep 50K-account." % (f["min_trades"], f["min_expectancy_R"], f["min_t_stat"],
                                                            f["min_profit_factor"], f["max_drawdown_usd"]), ""]
    pad = map_ / "DAGRAPPORT.md"
    map_.mkdir(parents=True, exist_ok=True)
    pad.write_text("\n".join(m), encoding="utf-8")
    if laatste:
        (map_ / "dagrapporten").mkdir(exist_ok=True)
        (map_ / "dagrapporten" / ("%s.md" % laatste)).write_text("\n".join(m), encoding="utf-8")
    return pad


def telegram_tekst(map_, strat, dagen):
    d = max(dagen)
    trades = {v: journal_trades(map_, v) for v in strat["varianten"]}
    regels = ["MES forward test – %s%s" % (d.strftime("%d-%m-%Y"), "" if len(dagen) <= 1 else " (%d dagen)" % len(dagen))]
    for v in strat["varianten"]:
        vt = [t for t in trades[v] if t["datum"] == d]
        nu = ", ".join("%s %s" % (t["richting"], geld(t["netto"])) for t in vt) or "geen trade"
        regels.append("%s: %s | totaal %s, %d trades" % (v, nu, geld(sum(t["netto"] for t in trades[v])), len(trades[v])))
    return "\n".join(regels)
