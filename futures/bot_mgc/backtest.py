"""Fase A: backtest op historische 1-minuutdata (GC-prijzen, MGC-tickwaarde en -kosten). Geen API, geen orders.

Gebruik: python -m bot_mgc.backtest [--data pad.csv]
Uitvoer: bot_mgc/reports/backtest.html + CSV's, en de backtest-trades in bot_mgc/journal_bot.csv (account mgc-backtest).
"""
import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from .account import VirtueelAccount
from .fills import simuleer_dag
from .instellingen import BOT, ROOT, load_calendar, load_firm, load_personal, load_strategy
from .kalender_mgc import Kalender, vergelijk_rolls_v0
from .statistiek import in_periode, per_jaar, stats
from .strategie import (ALLE_VARIANTEN, GEHALVEERD_NUL, INSTAP_TE_LAAT, WEEKSTOP, beslis, bouw_dagen, contracten,
                        variant_spec)

REPORTS = BOT / "reports"


def _sim_modules():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from sim.montecarlo import run_montecarlo  # noqa: E402  (gedeelde infrastructuur, alleen lezen)
    from sim.rules import simulate  # noqa: E402
    return simulate, run_montecarlo


def run_variant(dagen, strat, firm, variant="A", stress=False, filter_dagen=None, stop_factor=None, kosten=None, vanaf=None):
    """Speelt alle dagen af met dezelfde beslis- en fill-code als paper/sim. Geeft (uitkomsten, account).
    vanaf: pas vanaf die datum handelen (eerdere dagen tellen alleen als historie), zoals de forward test."""
    kosten = strat["kosten_per_contract_rt"] if kosten is None else kosten
    acc = VirtueelAccount(firm)
    historie = []
    week, week_pnl = None, 0.0
    out = []
    for d in dagen:
        wk = d.datum.isocalendar()[:2]
        if wk != week:
            week, week_pnl = wk, 0.0
        if vanaf is not None and d.datum < vanaf:
            if d.geldig:
                historie.append(d)
            continue
        b = beslis(d, historie, strat, variant, filter_dagen, stop_factor)
        u = {"datum": d.datum, "variant": variant, "beslissing": b, "status": b.reden or "", "trade": None, "fomc": d.fomc}
        if b.is_trade:
            if week_pnl <= -strat["weekstop_usd"]:
                u["status"] = WEEKSTOP
            else:
                n, reden = contracten(b.stop_afstand, strat, acc.afstand_tot_bodem())
                b.contracten = n
                if n == 0:
                    u["status"] = reden
                    if reden == GEHALVEERD_NUL and strat["backtest"].get("herstart_bij_vastlopen", True):
                        acc.herstart_na_vastlopen()
                else:
                    sim = simuleer_dag(d.bars, b.richting, b.stop_afstand, n, strat, stress)
                    if not sim.gevuld:
                        u["status"] = INSTAP_TE_LAAT
                    else:
                        res = sim.resultaat(kosten)
                        u["status"] = "gevuld"
                        u["trade"] = dict(res, datum=d.datum, variant=variant, richting=b.richting, signaal=b.signaal,
                                          instap=sim.instap, uitstap=sim.uitstap, stop=sim.stop, stop_afstand=b.stop_afstand,
                                          contracten=n, instap_bar=sim.instap_bar, uitstap_bar=sim.uitstap_bar_tijd,
                                          uitstapreden=sim.uitstapreden, rod=b.rod, onfh=b.onfh, mediaan=b.mediaan,
                                          fomc=d.fomc)
                        acc.verwerk_trade(res["netto"], res["mae"])
                        week_pnl += res["netto"]
        acc.einde_dag()
        if d.geldig:
            historie.append(d)
        out.append(u)
    return out, acc


def trades_van(uitkomsten):
    return [u["trade"] for u in uitkomsten if u["trade"]]


def avonden(trades):
    """Per handelsdag de trades als [{'net_pnl','mae','kosten'}] (formaat van sim/)."""
    dagen = {}
    for t in sorted(trades, key=lambda x: x["datum"]):
        dagen.setdefault(t["datum"], []).append({"net_pnl": t["netto"], "mae": t["mae"], "kosten": t["kosten"]})
    return sorted(dagen.items())


def topstep_sim(trades, firm, starts):
    simulate, _ = _sim_modules()
    reeks = avonden(trades)
    res = []
    for s in starts:
        tr = simulate(firm, [x for x in reeks if x[0] >= s])
        res.append({"start": s, "status": tr.status, "einde": tr.end_date, "reden": tr.reason})
    return res


def monte_carlo(trades, firm, rules, runs, seed=1):
    _, run_montecarlo = _sim_modules()
    return run_montecarlo(firm, rules, [t for _, t in avonden(trades)], runs=runs, seed=seed)


def correlaties(trades_a):
    """Correlatie dag-P&L met de MES-backtest (bot\\reports\\dag_pnl*.csv) en ZN (bot_zn\\reports\\dag_pnl_A.csv)."""
    mijn = {}
    for t in trades_a:
        mijn[t["datum"]] = mijn.get(t["datum"], 0.0) + t["netto"]
    out = []
    for naam, sub in (("MES", "bot"), ("ZN", "bot_zn")):
        map_ = ROOT / sub / "reports"
        paden = sorted(map_.glob("dag_pnl*.csv")) if map_.exists() else []
        if not paden:
            out.append((naam, None, "geen backtest gevonden in %s\\reports" % sub))
            continue
        ander = {}
        with open(paden[0], newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    ander[dt.date.fromisoformat(r["datum"])] = float(r["pnl"])
                except (KeyError, ValueError):
                    continue
        gedeeld = sorted(set(mijn) | set(ander))
        out.append((naam, _pearson([mijn.get(d, 0.0) for d in gedeeld], [ander.get(d, 0.0) for d in gedeeld]),
                    "%d dagen" % len(gedeeld)))
    return out


def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = sum((a - mx) ** 2 for a in xs) ** 0.5
    sy = sum((b - my) ** 2 for b in ys) ** 0.5
    return sxy / (sx * sy) if sx and sy else None


def varianten(strat):
    return [v for v in (strat.get("paper_varianten") or ALLE_VARIANTEN)]


def richtinggevend(strat):
    return [v for v in strat.get("richtinggevende_varianten", ["A"]) if v in varianten(strat)]


def criteria(strat, res, var="A"):
    """De 9 criteria uit plan §8 (out-of-sample), plus 2 eisen omdat er meerdere varianten getest worden:
    10. t-stat ≥ 2,50 (Bonferroni-correctie voor 4 geteste varianten) en 11. beter dan de willekeurige controle R."""
    c = strat["criteria"]
    oos, oos_s = res[var]["oos"], res[var + "_stress"]["oos"]
    jaren = res[var]["oos_jaren"]
    n_jaren = len(jaren)
    jaren_ok = sum(1 for _, m in jaren if (m.get("expectancy_R") or 0) >= 0)
    tot = oos.get("netto_totaal") or 0
    max_jaar = max(((m.get("netto_totaal") or 0) for _, m in jaren), default=0)
    aandeel = max_jaar / tot if tot > 0 else None
    gv = res["gevoeligheid"].get(var) if isinstance(res["gevoeligheid"], dict) and var in res["gevoeligheid"] else res["gevoeligheid"]
    cellen = [x for rij in gv["tabel"] for x in rij]
    pos = sum(1 for x in cellen if x is not None and x > 0)
    exp, ts = oos.get("expectancy_R"), oos.get("t_stat")
    pf_s = oos_s.get("profit_factor")
    mc = res["monte_carlo"].get(var) if isinstance(res["monte_carlo"], dict) and "pass_pct" not in res["monte_carlo"] else res["monte_carlo"]
    mc_pct = mc["pass_pct"] if mc else None
    ex_b = res["B"]["oos"].get("expectancy_R") if "B" in res else None
    ex_r = res["R"]["oos"].get("expectancy_R") if "R" in res else None
    ex_is = res[var]["is"].get("expectancy_R")
    t_min = strat.get("min_t_stat_gecorrigeerd", 2.5)

    def f(x, s):
        return "–" if x is None else s % x

    lijst = [
        ("1. ≥ %d trades" % c["min_trades"], oos.get("trades", 0) >= c["min_trades"], "%d trades" % oos.get("trades", 0)),
        ("2. Expectancy ≥ +%.2fR na kosten, t-stat ≥ %.1f" % (c["min_expectancy_R"], c["min_t_stat"]),
         exp is not None and ts is not None and exp >= c["min_expectancy_R"] and ts >= c["min_t_stat"],
         "expectancy %s, t-stat %s" % (f(exp, "%+.3fR"), f(ts, "%.2f"))),
        ("3. Profit factor ≥ %.2f met stresskosten" % c["min_profit_factor_stress"],
         pf_s is not None and pf_s >= c["min_profit_factor_stress"], "profit factor (stress) %s" % f(pf_s, "%.2f")),
        ("4. Minstens %d van de %d jaren expectancy ≥ 0; geen jaar > %d%% van de winst"
         % (max(0, n_jaren - c["max_jaren_negatief"]), n_jaren, 100 * c["max_aandeel_een_jaar"]),
         n_jaren > 0 and jaren_ok >= n_jaren - c["max_jaren_negatief"] and aandeel is not None
         and aandeel <= c["max_aandeel_een_jaar"],
         "%d van %d jaren ≥ 0; grootste jaar = %s van de winst"
         % (jaren_ok, n_jaren, f(None if aandeel is None else 100 * aandeel, "%.0f%%"))),
        ("5. Maximale drawdown < $%d" % c["max_drawdown_usd"],
         oos.get("max_dd") is not None and oos["max_dd"] < c["max_drawdown_usd"], "max drawdown %s" % f(oos.get("max_dd"), "$%.0f")),
        ("6. Monte Carlo-slagingskans Topstep 50K ≥ %d%%" % c["min_monte_carlo_pct"],
         mc_pct is not None and mc_pct >= c["min_monte_carlo_pct"], "slagingskans %s" % f(mc_pct, "%.1f%%")),
        ("7. Gevoeligheidstabel overwegend positief (≥ %d%% van de cellen)" % (100 * c["min_aandeel_gevoeligheid_positief"]),
         bool(cellen) and pos / len(cellen) >= c["min_aandeel_gevoeligheid_positief"], "%d van %d cellen positief" % (pos, len(cellen))),
        ("8. %s beter dan benchmark B" % var, exp is not None and ex_b is not None and exp > ex_b,
         "%s %s vs B %s" % (var, f(exp, "%+.3fR"), f(ex_b, "%+.3fR"))),
        ("9. In-sample expectancy > 0", ex_is is not None and ex_is > 0, "in-sample %s %s" % (var, f(ex_is, "%+.3fR"))),
        ("10. t-stat ≥ %.2f (correctie: %d varianten getest)" % (t_min, len(richtinggevend(strat))),
         ts is not None and ts >= t_min, "t-stat %s" % f(ts, "%.2f")),
        ("11. %s beter dan willekeurige controle R" % var, exp is not None and ex_r is not None and exp > ex_r,
         "%s %s vs R %s" % (var, f(exp, "%+.3fR"), f(ex_r, "%+.3fR"))),
    ]
    ontbreekt = [x[0] for x in lijst if not x[1]]
    return {"criteria": lijst, "oordeel": "GO" if not ontbreekt else "NO-GO", "ontbreekt": ontbreekt}


def controle_r(trades):
    """Negatieve controle: zonder richtingskennis hoort de expectancy ≈ −(kosten ÷ risico) te zijn.
    OK als het verschil binnen 2 standaardfouten valt; anders zit er waarschijnlijk een fout in de backtest."""
    rs = [t["R"] for t in trades if t.get("R") is not None and t.get("risico")]
    n = len(rs)
    if n < 30:
        return {"trades": n, "ok": None, "uitleg": "te weinig trades (%d) voor de controle" % n}
    gem = sum(rs) / n
    sd = (sum((x - gem) ** 2 for x in rs) / (n - 1)) ** 0.5
    se = sd / n ** 0.5
    verwacht = -sum(t["kosten"] / t["risico"] for t in trades if t.get("risico")) / n
    z = (gem - verwacht) / se if se else None
    ok = z is not None and abs(z) <= 2.0
    return {"trades": n, "expectancy_R": gem, "verwacht_R": verwacht, "se": se, "z": z, "ok": ok,
            "uitleg": ("in orde: R verdient wat je zonder richtingskennis verwacht (min de kosten)" if ok else
                       "AFWIJKING: R wijkt meer dan 2 standaardfouten af van −kosten. Zoek eerst de fout in de backtest "
                       "(vooruitkijken, fills of kosten) voordat je A-E vertrouwt.")}


def marktstatistiek(dagen):
    """Alleen loggen: per jaar het gemiddelde rendement overnacht (slot gisteren 13:30 -> 08:20) en overdag
    (08:20 -> 13:30), in basispunten, met t-stat. Overnight-posities kunnen bij Topstep niet; dit is alleen ter info."""
    per = {}
    vorige = None
    for d in dagen:
        b = d.bars or {}
        o820 = b.get("08:20", (None,))[0] if b else None
        if o820 and d.slot and d.geldig:
            g = per.setdefault(d.datum.year, {"nacht": [], "dag": []})
            g["dag"].append(1e4 * (d.slot / o820 - 1))
            if vorige is not None and vorige.slot and vorige.contract == d.contract:
                g["nacht"].append(1e4 * (o820 / vorige.slot - 1))
        vorige = d
    out = []
    from .statistiek import t_stat
    for jaar in sorted(per):
        rij = {"jaar": jaar}
        for k in ("nacht", "dag"):
            xs = per[jaar][k]
            rij[k] = (sum(xs) / len(xs)) if xs else None
            rij[k + "_t"] = t_stat(xs)
            rij[k + "_n"] = len(xs)
        out.append(rij)
    return out


def gevoeligheid(dagen, strat, firm, var, oos_van):
    g = strat["gevoeligheid"]
    met_filter = variant_spec(var, strat)["filter"]
    fds = g["filter_dagen"] if met_filter else [None]
    tabel, aantallen = [], []
    for fd in fds:
        rij, nr = [], []
        for sf in g["stop_factor"]:
            u, _ = run_variant(dagen, strat, firm, var, filter_dagen=fd, stop_factor=sf)
            m = stats(in_periode(trades_van(u), oos_van))
            rij.append(m.get("expectancy_R"))
            nr.append(m.get("trades", 0))
        tabel.append(rij)
        aantallen.append(nr)
    return {"filter_dagen": fds, "stop_factor": g["stop_factor"], "tabel": tabel, "aantallen": aantallen}


def analyseer(dagen, strat, firm, rules, log=print, mc_runs=None):
    bt = strat["backtest"]
    is_van, is_tot = (dt.date.fromisoformat(x) for x in bt["in_sample"])
    oos_van = dt.date.fromisoformat(bt["out_of_sample_start"])
    laatste = dagen[-1].datum if dagen else oos_van
    res = {"periodes": {"in_sample": (is_van, is_tot), "out_of_sample": (oos_van, laatste)}}

    def deel(uitk):
        tr = trades_van(uitk)
        return {"uitkomsten": uitk, "trades": tr, "is": stats(in_periode(tr, is_van, is_tot)),
                "oos": stats(in_periode(tr, oos_van)), "oos_jaren": per_jaar(in_periode(tr, oos_van))}

    vs = varianten(strat)
    res["varianten"] = vs
    for var in vs:
        log("Strategie %s ..." % var)
        u, acc = run_variant(dagen, strat, firm, var)
        res[var] = deel(u)
        res[var]["herstarts"] = acc.herstarts
        res[var]["vastgelopen"] = getattr(acc, "vastgelopen", 0)
        u, _ = run_variant(dagen, strat, firm, var, stress=True)
        res[var + "_stress"] = deel(u)
        tr = res[var]["trades"]
        # extra uitsplitsingen: in-sample in twee tijdperken (pithandel tot 2015) en long/short apart
        res[var]["is_delen"] = [("2010–2014", stats(in_periode(tr, is_van, dt.date(2014, 12, 31)))),
                                ("2015–2019", stats(in_periode(tr, dt.date(2015, 1, 1), is_tot)))]
        oos_tr = in_periode(tr, oos_van)
        res[var]["oos_richting"] = [("long", stats([t for t in oos_tr if t["richting"] > 0])),
                                    ("short", stats([t for t in oos_tr if t["richting"] < 0]))]
    rg = richtinggevend(strat)
    log("Gevoeligheidstabellen ...")
    res["gevoeligheid"] = {var: gevoeligheid(dagen, strat, firm, var, oos_van) for var in rg}
    log("Topstep-regelsimulator en Monte Carlo ...")
    res["topstep"] = topstep_sim(res["A"]["trades"], firm, [is_van, oos_van])
    res["monte_carlo"] = {var: monte_carlo(in_periode(res[var]["trades"], oos_van), firm, rules,
                                           mc_runs or bt["monte_carlo_runs"]) for var in rg}
    res["correlaties"] = correlaties(res["A"]["trades"])
    res["oordelen"] = {var: criteria(strat, res, var) for var in rg}
    res["oordeel"] = res["oordelen"]["A"]
    if "R" in res:
        res["controle_r"] = controle_r(in_periode(res["R"]["trades"], oos_van))
    res["markt"] = marktstatistiek(dagen)
    return res


def samenvatting(res):
    a = res["A"]
    per = {}
    for var in res.get("varianten", "ABC"):
        m = res[var]["oos"]
        per[var] = {"expectancy_R": m.get("expectancy_R"), "winrate": m.get("winrate"), "trades": m.get("trades"),
                    "t_stat": m.get("t_stat"),
                    "oordeel": res.get("oordelen", {}).get(var, {}).get("oordeel", "benchmark")}
    return {"expectancy_R": a["oos"].get("expectancy_R"), "winrate": a["oos"].get("winrate"),
            "trades": a["oos"].get("trades"), "oordeel": res["oordeel"]["oordeel"], "datum": dt.date.today().isoformat(),
            "varianten": per}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from .data import DATA_BESTAND, lees_data, v0_rolls
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA_BESTAND))
    a = ap.parse_args(argv)
    if not Path(a.data).exists():
        print("Geen data gevonden (%s). Eerst: data_mgc_kosten.bat en data_mgc_download.bat" % a.data)
        return 1
    strat, cal = load_strategy(), load_calendar()
    firm, rules = load_firm("topstep_50k"), load_personal()
    kal = Kalender(cal, strat)
    print("Data lezen ...")
    ruwe = lees_data(a.data)
    rolls = v0_rolls(ruwe)
    dagen = bouw_dagen(ruwe, kal, strat, roll_dagen=set(rolls))
    print("%d handelsdagen (%s t/m %s), %d rolls in .v.0" % (len(dagen), dagen[0].datum, dagen[-1].datum, len(rolls)))
    afwijkingen = vergelijk_rolls_v0(kal, rolls, strat["roll"]["max_afwijking_dagen_v0"])
    REPORTS.mkdir(exist_ok=True)
    from .logboek import Logboek
    lg = Logboek("backtest", echo=False)
    for m in afwijkingen:
        lg.info("ROLL-AFWIJKING: .v.0 rolde op %s, vaste regel op %s (%+d handelsdagen)"
                % (m["v0_roll"], m["regel_roll"], m["verschil_handelsdagen"]))
    res = analyseer(dagen, strat, firm, rules)
    res["roll_afwijkingen"], res["rolls"] = afwijkingen, rolls
    from .rapport import schrijf_backtest_rapport
    pad = schrijf_backtest_rapport(res, strat, REPORTS)
    with open(REPORTS / "backtest_samenvatting.json", "w", encoding="utf-8") as f:
        json.dump(samenvatting(res), f, indent=2)
    from .journal_mgc import schrijf_backtest_journal
    n = schrijf_backtest_journal({v: res[v]["trades"] for v in res["varianten"]})
    print("\nRapport: %s" % pad)
    print("Journal: %d backtest-trades in bot_mgc\\journal_bot.csv" % n)
    print("Roll-afwijkingen > %d dagen: %d (zie logs)" % (strat["roll"]["max_afwijking_dagen_v0"], len(afwijkingen)))
    for var, o in res["oordelen"].items():
        print("\n%s: %s" % (variant_spec(var, strat)["naam"], o["oordeel"]))
        for naam, ok, detail in o["criteria"]:
            print("  [%s] %s — %s" % ("GROEN" if ok else "ROOD ", naam, detail))
    if res.get("controle_r"):
        print("\nControle R: %s" % res["controle_r"]["uitleg"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
