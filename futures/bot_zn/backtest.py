"""Fase A: backtest op historische 1-minuutdata. Geen API, geen orders.

Gebruik: python -m bot_zn.backtest [--data pad.csv]
Uitvoer: bot_zn/reports/backtest.html + CSV's, en de backtest-trades in bot_zn/journal_bot.csv (account zn-backtest).
"""
import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from .account import VirtueelAccount
from .fills import simuleer_dag
from .instellingen import BOT, ROOT, load_calendar, load_firm, load_strategy
from .kalender_zn import Kalender, vergelijk_rolls_v0
from .statistiek import in_periode, per_jaar, stats
from .strategie import GEHALVEERD_NUL, VARIANTEN, WEEKSTOP, beslis, bouw_dagen, contracten

REPORTS = BOT / "reports"


def run_variant(dagen, strat, firm, variant="A", stress=False, filter_dagen=None, stop_factor=None, kosten=None):
    """Speelt alle dagen af met dezelfde beslis- en fill-code als paper/sim.
    Geeft (uitkomsten, account). Eén uitkomst per handelsdag in de data."""
    v = VARIANTEN[variant]
    kosten = strat["kosten_per_contract_rt"] if kosten is None else kosten
    acc = VirtueelAccount(firm)
    historie = []
    week, week_pnl = None, 0.0
    out = []
    for d in dagen:
        wk = d.datum.isocalendar()[:2]
        if wk != week:
            week, week_pnl = wk, 0.0
        b = beslis(d, historie, strat, variant, filter_dagen, stop_factor)
        u = {"datum": d.datum, "variant": variant, "beslissing": b, "status": b.reden or "", "trade": None,
             "gemist": None, "veiling": d.veiling, "contract": d.contract}
        if b.is_trade:
            if week_pnl <= -strat["weekstop_usd"]:
                u["status"] = WEEKSTOP
            else:
                n, reden = contracten(b.stop_ticks, strat, acc.afstand_tot_bodem())
                b.contracten = n
                if n == 0:
                    u["status"] = reden
                    if reden == GEHALVEERD_NUL and strat["backtest"].get("herstart_bij_vastlopen", True):
                        # zonder trades verandert het saldo nooit meer: het account zit vast. Zie README.
                        acc.herstart_na_vastlopen()
                else:
                    u["status"] = "signaal"
                    sim = simuleer_dag(d.bars, b.richting, b.limiet, b.stop_ticks, n, strat, v["instap"], stress)
                    if not sim.gevuld:
                        u["status"] = "niet_gevuld"
                        # wat zou de market-instap op dit gemiste signaal hebben opgeleverd?
                        m = simuleer_dag(d.bars, b.richting, b.limiet, b.stop_ticks, n, strat, "market", stress)
                        res = m.resultaat(kosten)
                        if res:
                            u["gemist"] = {"datum": d.datum, "netto": res["netto"], "R": res["R"], "mae": res["mae"]}
                    else:
                        res = sim.resultaat(kosten)
                        u["status"] = "gevuld"
                        u["trade"] = dict(res, datum=d.datum, variant=variant, richting=b.richting, instap=sim.instap,
                                          uitstap=sim.uitstap, stop=sim.stop, limiet=b.limiet, stop_ticks=b.stop_ticks,
                                          contracten=n, instap_bar=sim.instap_bar, uitstap_bar=sim.uitstap_bar_tijd,
                                          uitstapreden=sim.uitstapreden, rod=b.rod, mediaan=b.mediaan,
                                          veiling=d.veiling)
                        acc.verwerk_trade(res["netto"], res["mae"])
                        week_pnl += res["netto"]
        acc.einde_dag()
        if d.geldig:
            historie.append(d)
        out.append(u)
    return out, acc


def trades_van(uitkomsten):
    return [u["trade"] for u in uitkomsten if u["trade"]]


def vulgraad(uitkomsten, van=None, tot=None):
    sel = [u for u in uitkomsten if u["status"] in ("gevuld", "niet_gevuld")
           and (van is None or u["datum"] >= van) and (tot is None or u["datum"] <= tot)]
    if not sel:
        return None, 0, 0
    g = sum(1 for u in sel if u["status"] == "gevuld")
    return g / len(sel), g, len(sel)


def gemist(uitkomsten, van=None, tot=None):
    return [u["gemist"] for u in uitkomsten if u["gemist"]
            and (van is None or u["datum"] >= van) and (tot is None or u["datum"] <= tot)]


def topstep_sim(trades, firm, starts):
    """Bestaande regelsimulator (sim/) op de echte volgorde van de trades, vanaf elke startdatum."""
    sys.path.insert(0, str(ROOT))
    from sim.rules import simulate  # noqa: E402  (gedeelde infrastructuur, alleen lezen)
    dagen = {}
    for t in sorted(trades, key=lambda x: x["datum"]):
        dagen.setdefault(t["datum"], []).append({"net_pnl": t["netto"], "mae": t["mae"], "kosten": t["kosten"]})
    reeks = sorted(dagen.items())
    res = []
    for s in starts:
        sub = [x for x in reeks if x[0] >= s]
        tr = simulate(firm, sub)
        res.append({"start": s, "status": tr.status, "einde": tr.end_date, "reden": tr.reason})
    return res


def maand_starts(van, tot):
    out, d = [], dt.date(van.year, van.month, 1)
    while d <= tot:
        out.append(max(d, van))
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


def correlaties(trades_a):
    """Correlatie dag-P&L met MES- of MGC-backtests, als die er zijn (bot/reports/dag_pnl*.csv, kolommen datum,pnl)."""
    mijn = {}
    for t in trades_a:
        mijn[t["datum"]] = mijn.get(t["datum"], 0.0) + t["netto"]
    out = []
    for naam, sub in (("MES", "bot"), ("MGC", "bot_mgc")):
        paden = sorted((ROOT / sub / "reports").glob("dag_pnl*.csv")) if (ROOT / sub / "reports").exists() else []
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
        xs = [mijn.get(d, 0.0) for d in gedeeld]
        ys = [ander.get(d, 0.0) for d in gedeeld]
        out.append((naam, _pearson(xs, ys), "%d dagen" % len(gedeeld)))
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


def criteria(strat, res):
    """De 9 criteria uit plan §8 (out-of-sample, strategie A). res = dict met de berekende onderdelen."""
    c = strat["criteria"]
    oos, oos_s = res["A"]["oos"], res["A_stress"]["oos"]
    jaren = res["A"]["oos_jaren"]
    n_jaren = len(jaren)
    jaren_ok = sum(1 for _, m in jaren if (m.get("expectancy_R") or 0) >= 0)
    tot = oos.get("netto_totaal") or 0
    max_jaar = max(((m.get("netto_totaal") or 0) for _, m in jaren), default=0)
    aandeel = max_jaar / tot if tot > 0 else None
    sens = res["gevoeligheid"]
    cellen = [x for rij in sens["tabel"] for x in rij]
    pos = sum(1 for x in cellen if x is not None and x > 0)
    sens_ok = cellen and pos / len(cellen) >= c["min_aandeel_gevoeligheid_positief"]
    exp, ts = oos.get("expectancy_R"), oos.get("t_stat")
    pf_s = oos_s.get("profit_factor")
    vg = res["A"]["oos_vulgraad"]
    ex_b = res["B"]["oos"].get("expectancy_R")
    ex_is = res["A"]["is"].get("expectancy_R")
    r22 = res["A"]["vanaf_2022"].get("expectancy_R")

    def f(x, s):
        return "–" if x is None else s % x

    lijst = [
        ("1. ≥ %d gevulde trades" % c["min_trades"], oos.get("trades", 0) >= c["min_trades"],
         "%d trades" % oos.get("trades", 0)),
        ("2. Expectancy ≥ +%.2fR na kosten, t-stat ≥ %.1f" % (c["min_expectancy_R"], c["min_t_stat"]),
         exp is not None and ts is not None and exp >= c["min_expectancy_R"] and ts >= c["min_t_stat"],
         "expectancy %s, t-stat %s" % (f(exp, "%+.3fR"), f(ts, "%.2f"))),
        ("3. Profit factor ≥ %.2f met stresskosten" % c["min_profit_factor_stress"],
         pf_s is not None and pf_s >= c["min_profit_factor_stress"], "profit factor (stress) %s" % f(pf_s, "%.2f")),
        ("4. Minstens %d van de %d jaren expectancy ≥ 0; geen jaar > %d%% van de winst"
         % (max(0, n_jaren - c["max_jaren_negatief"]), n_jaren, 100 * c["max_aandeel_een_jaar"]),
         n_jaren > 0 and jaren_ok >= n_jaren - c["max_jaren_negatief"] and aandeel is not None
         and aandeel <= c["max_aandeel_een_jaar"],
         "%d van %d jaren ≥ 0; grootste jaar = %s van de winst" % (jaren_ok, n_jaren, f(None if aandeel is None else 100 * aandeel, "%.0f%%"))),
        ("5. 2022–nu apart: expectancy ≥ 0", r22 is not None and r22 >= 0, "expectancy 2022–nu %s" % f(r22, "%+.3fR")),
        ("6. Maximale drawdown < $%d" % c["max_drawdown_usd"],
         oos.get("max_dd") is not None and oos["max_dd"] < c["max_drawdown_usd"], "max drawdown %s" % f(oos.get("max_dd"), "$%.0f")),
        ("7. Vulgraad ≥ %d%%" % (100 * c["min_vulgraad"]), vg is not None and vg >= c["min_vulgraad"],
         "vulgraad %s" % f(None if vg is None else 100 * vg, "%.0f%%")),
        ("8. Gevoeligheidstabel overwegend positief (≥ %d%% van de cellen)" % (100 * c["min_aandeel_gevoeligheid_positief"]),
         bool(sens_ok), "%d van %d cellen positief" % (pos, len(cellen))),
        ("9. A beter dan B; in-sample expectancy > 0",
         exp is not None and ex_b is not None and exp > ex_b and ex_is is not None and ex_is > 0,
         "A %s vs B %s; in-sample A %s" % (f(exp, "%+.3fR"), f(ex_b, "%+.3fR"), f(ex_is, "%+.3fR"))),
    ]
    ontbreekt = [x[0] for x in lijst if not x[1]]
    return {"criteria": lijst, "oordeel": "GO" if not ontbreekt else "NO-GO", "ontbreekt": ontbreekt}


def analyseer(dagen, strat, firm, log=print):
    """Draait alles en geeft één resultaat-dict voor het rapport."""
    bt = strat["backtest"]
    is_van, is_tot = (dt.date.fromisoformat(x) for x in bt["in_sample"])
    oos_van = dt.date.fromisoformat(bt["out_of_sample_start"])
    v22 = dt.date.fromisoformat(bt["apart_vanaf"])
    laatste = dagen[-1].datum if dagen else oos_van
    res = {"periodes": {"in_sample": (is_van, is_tot), "out_of_sample": (oos_van, laatste), "vanaf_2022": (v22, laatste)}}

    def deel(uitk):
        tr = trades_van(uitk)
        vg_oos = vulgraad(uitk, oos_van)
        return {
            "uitkomsten": uitk, "trades": tr,
            "is": stats(in_periode(tr, is_van, is_tot)),
            "oos": stats(in_periode(tr, oos_van)),
            "vanaf_2022": stats(in_periode(tr, v22)),
            "oos_jaren": per_jaar(in_periode(tr, oos_van)),
            "is_vulgraad": vulgraad(uitk, is_van, is_tot)[0],
            "oos_vulgraad": vg_oos[0], "oos_gevuld": vg_oos[1], "oos_signalen": vg_oos[2],
            "gemist_oos": stats(gemist(uitk, oos_van)),
            "gemist_is": stats(gemist(uitk, is_van, is_tot)),
        }

    for var in "ABCD":
        log("Strategie %s ..." % var)
        u, acc = run_variant(dagen, strat, firm, var)
        res[var] = deel(u)
        res[var]["herstarts"] = acc.herstarts
        res[var]["vastgelopen"] = getattr(acc, "vastgelopen", 0)
        u, acc = run_variant(dagen, strat, firm, var, stress=True)
        res[var + "_stress"] = deel(u)
    log("Gevoeligheidstabel ...")
    g = strat["gevoeligheid"]
    tabel, aantallen = [], []
    for fd in g["filter_dagen"]:
        rij, nr = [], []
        for sf in g["stop_factor"]:
            u, _ = run_variant(dagen, strat, firm, "A", filter_dagen=fd, stop_factor=sf)
            m = stats(in_periode(trades_van(u), oos_van))
            rij.append(m.get("expectancy_R"))
            nr.append(m.get("trades", 0))
        tabel.append(rij)
        aantallen.append(nr)
    res["gevoeligheid"] = {"filter_dagen": g["filter_dagen"], "stop_factor": g["stop_factor"], "tabel": tabel, "aantallen": aantallen}
    log("Topstep-regelsimulator ...")
    a_tr = res["A"]["trades"]
    res["topstep_oos"] = topstep_sim(a_tr, firm, [oos_van])
    res["topstep_is"] = topstep_sim(a_tr, firm, [is_van])
    res["topstep_rollend"] = topstep_sim(in_periode(a_tr, oos_van), firm, maand_starts(oos_van, laatste))
    res["correlaties"] = correlaties(a_tr)
    res["oordeel"] = criteria(strat, res)
    return res


def samenvatting(res):
    """Kort overzicht voor de live-bewaking (live_vs_backtest)."""
    a = res["A"]
    return {"expectancy_R": a["oos"].get("expectancy_R"), "winrate": a["oos"].get("winrate"),
            "vulgraad": a["oos_vulgraad"], "trades": a["oos"].get("trades"),
            "oordeel": res["oordeel"]["oordeel"], "datum": dt.date.today().isoformat()}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    from .data import DATA_BESTAND, lees_data, v0_rolls
    ap.add_argument("--data", default=str(DATA_BESTAND))
    a = ap.parse_args(argv)
    if not Path(a.data).exists():
        print("Geen data gevonden (%s). Eerst: data_zn_kosten.bat en data_zn_download.bat" % a.data)
        return 1
    strat, cal = load_strategy(), load_calendar()
    firm = load_firm("topstep_50k")
    kal = Kalender(cal, strat)
    print("Data lezen ...")
    ruwe = lees_data(a.data)
    rolls = v0_rolls(ruwe)
    dagen = bouw_dagen(ruwe, kal, strat, roll_dagen=set(rolls))
    print("%d handelsdagen (%s t/m %s), %d rolls in .v.0" % (len(dagen), dagen[0].datum, dagen[-1].datum, len(rolls)))
    afwijkingen = vergelijk_rolls_v0(kal, rolls, strat["roll"]["max_afwijking_dagen_v0"])
    REPORTS.mkdir(exist_ok=True)
    from .logboek import Logboek
    lg = Logboek("backtest")
    for m in afwijkingen:
        lg.info("ROLL-AFWIJKING: .v.0 rolde op %s, vaste regel op %s (%+d handelsdagen)"
                % (m["v0_roll"], m["regel_roll"], m["verschil_handelsdagen"]))
    res = analyseer(dagen, strat, firm)
    res["roll_afwijkingen"] = afwijkingen
    res["rolls"] = rolls
    from .rapport import schrijf_backtest_rapport
    pad = schrijf_backtest_rapport(res, strat, REPORTS)
    with open(REPORTS / "backtest_samenvatting.json", "w", encoding="utf-8") as f:
        json.dump(samenvatting(res), f, indent=2)
    from .journal_zn import schrijf_backtest_journal
    n = schrijf_backtest_journal({v: res[v]["trades"] for v in "ABCD"}, strat)
    print("\nRapport: %s" % pad)
    print("Journal: %d backtest-trades in bot_zn\\journal_bot.csv" % n)
    print("\nEindoordeel: %s" % res["oordeel"]["oordeel"])
    for naam, ok, detail in res["oordeel"]["criteria"]:
        print("[%s] %s — %s" % ("GROEN" if ok else "ROOD ", naam, detail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
