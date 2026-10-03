"""Mijn persoonlijke dagregels (rules/personal.json): toepassen in simulaties en waarschuwen bij invoer."""
import math

from .kalender import day_info, in_window
from .rules import Tracker


def plan_evening(trades, rules, balance, floor):
    """Past dagstop, winstplafond, max trades en halveren toe op de trades van één avond.
    Geeft de trades terug die ik volgens mijn regels echt zou nemen (eventueel gehalveerd)."""
    kept, pnl, losses = [], 0.0, 0
    for t in trades:
        if len(kept) >= rules["max_trades_per_avond"]:
            break
        if losses >= rules["dagstop_verliezen"] or pnl <= -rules["dagstop_usd"]:
            break
        if pnl >= rules["winstplafond_usd"]:
            break
        factor = 0.5 if (balance + pnl) - floor <= rules["halveren_binnen_usd_van_bodem"] else 1.0
        mae, kosten = t.get("mae"), t.get("kosten")
        nt = {"net_pnl": t["net_pnl"] * factor, "mae": None if mae is None else mae * factor}
        if kosten is not None:
            nt["kosten"] = kosten * factor
        kept.append(nt)
        pnl += nt["net_pnl"]
        if nt["net_pnl"] < 0:
            losses += 1
    return kept


def simulate_personal(firm, rules, days, consistency=None):
    """days = iterable van (datum, weeksleutel, [trades]). Past persoonlijke regels + firmaregels toe.
    Geeft (tracker, overgeslagen_dagen, aantal_dagen) terug."""
    tr = Tracker(firm, consistency)
    week, week_pnl, skipped, n = None, 0.0, [], 0
    for date, wk, trades in days:
        n += 1
        if wk != week:
            week, week_pnl = wk, 0.0
        if week_pnl <= -rules["weekstop_usd"]:
            skipped.append(date)
            continue
        kept = plan_evening(trades, rules, tr.balance, tr.floor)
        before = tr.balance
        tr.process_day(date, kept)
        week_pnl += tr.balance - before
        if tr.status != "RUNNING":
            break
    return tr, skipped, n


def contracten_voor(risico, stop_punten, config, instrument="MES"):
    """Contracten = risico ÷ (stop × puntwaarde), naar beneden afgerond, maximaal max_contracten."""
    if not stop_punten or stop_punten <= 0:
        return 0
    pv = config["instrumenten"].get(instrument, config["instrumenten"]["MES"])["punt_waarde"]
    return max(0, min(config["max_contracten"], math.floor(risico / (stop_punten * pv) + 1e-9)))


def waarschuwingen(datum, instaptijd, stop_punten, contracten, risico, eerdere, rules, config, cal,
                   afstand_tot_bodem=None, instrument="MES"):
    """eerdere = records (niet-replay) die al in het journal staan. Geeft een lijst waarschuwingen."""
    w = []
    info = day_info(datum, cal, config)
    if not info["traden"]:
        w.append("Geen tradedag: " + "; ".join(info["redenen"]))
    if instaptijd and not in_window(instaptijd, info):
        w.append("Instap %s valt buiten het venster %s–%s" % (instaptijd, *info["venster"]))
    if stop_punten and stop_punten > config["max_stop_punten"]:
        w.append("Stop > %s punten: trade overslaan" % config["max_stop_punten"])
    advies = contracten_voor(risico, stop_punten, config, instrument)
    if afstand_tot_bodem is not None and afstand_tot_bodem <= rules["halveren_binnen_usd_van_bodem"]:
        advies = advies // 2
        w.append("Saldo zit $%.0f boven de bodem (≤ $%s): halveer je positie (max %d)"
                 % (afstand_tot_bodem, rules["halveren_binnen_usd_van_bodem"], advies))
    if contracten and contracten > advies:
        w.append("%d contracten is meer dan het advies (%d)" % (contracten, advies))
    vandaag = [t for t in eerdere if t["datum"] == datum]
    dag_pnl = sum(t["netto_pnl"] for t in vandaag)
    verliezen = sum(1 for t in vandaag if t["netto_pnl"] < 0)
    if len(vandaag) >= rules["max_trades_per_avond"]:
        w.append("Al %d trades vanavond: maximum is %d" % (len(vandaag), rules["max_trades_per_avond"]))
    if verliezen >= rules["dagstop_verliezen"] or dag_pnl <= -rules["dagstop_usd"]:
        w.append("Dagstop geraakt (%d verliezen, dag-P&L $%.2f): stoppen voor vandaag" % (verliezen, dag_pnl))
    if dag_pnl >= rules["winstplafond_usd"]:
        w.append("Winstplafond geraakt (dag-P&L $%.2f): stoppen voor vandaag" % dag_pnl)
    wk = datum.isocalendar()[:2]
    week_pnl = sum(t["netto_pnl"] for t in eerdere if t["datum"].isocalendar()[:2] == wk and t["datum"] <= datum)
    if week_pnl <= -rules["weekstop_usd"]:
        w.append("Weekstop geraakt (week-P&L $%.2f): rest van de week niet traden" % week_pnl)
    return w
