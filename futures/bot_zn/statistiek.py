"""Statistieken over trades. Een trade is een dict met minstens: datum, netto, R, mae."""
import math
from collections import OrderedDict

WEEKDAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]


def t_stat(waarden):
    n = len(waarden)
    if n < 2:
        return None
    m = sum(waarden) / n
    var = sum((x - m) ** 2 for x in waarden) / (n - 1)
    if var <= 0:
        return None
    return m / math.sqrt(var / n)


def stats(trades):
    n = len(trades)
    if n == 0:
        return {"trades": 0}
    rs = [t["R"] for t in trades if t["R"] is not None]
    wins = [t for t in trades if t["netto"] > 0]
    losses = [t for t in trades if t["netto"] < 0]
    gw = sum(t["netto"] for t in wins)
    gl = -sum(t["netto"] for t in losses)
    eq = piek = 0.0
    dd = dd_mae = 0.0
    for t in sorted(trades, key=lambda x: x["datum"]):
        laag = eq + min(t["netto"], t.get("mae") or 0.0, 0.0)
        dd_mae = max(dd_mae, piek - laag)
        eq += t["netto"]
        dd = max(dd, piek - eq)
        piek = max(piek, eq)
    dagen = OrderedDict()
    for t in trades:
        dagen[t["datum"]] = dagen.get(t["datum"], 0.0) + t["netto"]
    totaal = sum(t["netto"] for t in trades)
    beste = max(dagen.values())
    win_r = [t["R"] for t in wins if t["R"] is not None]
    los_r = [t["R"] for t in losses if t["R"] is not None]
    return {
        "trades": n,
        "winrate": len(wins) / n,
        "gem_winst_R": sum(win_r) / len(win_r) if win_r else None,
        "gem_verlies_R": sum(los_r) / len(los_r) if los_r else None,
        "expectancy_R": sum(rs) / len(rs) if rs else None,
        "t_stat": t_stat(rs),
        "profit_factor": gw / gl if gl > 0 else None,
        "netto_totaal": totaal,
        "max_dd": dd,
        "max_dd_mae": dd_mae,
        "beste_dag": beste,
        "beste_dag_aandeel": beste / totaal if totaal > 0 else None,
    }


def in_periode(trades, van=None, tot=None):
    return [t for t in trades if (van is None or t["datum"] >= van) and (tot is None or t["datum"] <= tot)]


def per_groep(trades, sleutel):
    g = OrderedDict()
    for t in sorted(trades, key=lambda x: x["datum"]):
        g.setdefault(sleutel(t), []).append(t)
    return [(k, stats(v)) for k, v in g.items()]


def per_jaar(trades):
    return per_groep(trades, lambda t: t["datum"].year)


def per_weekdag(trades):
    res = dict(per_groep(trades, lambda t: WEEKDAGEN[t["datum"].weekday()]))
    return [(d, res[d]) for d in WEEKDAGEN if d in res]


def fmt(key, v):
    if v is None:
        return "–"
    if key in ("winrate", "beste_dag_aandeel", "vulgraad"):
        return "%.0f%%" % (100 * v)
    if key.endswith("_R"):
        return "%+.3f" % v
    if key in ("profit_factor", "t_stat"):
        return "%.2f" % v
    if key == "trades":
        return str(v)
    return geld(v)


def geld(v):
    """-5864.2 -> '−$5.864' (punt als duizendtal, zoals in Nederland)."""
    s = format(int(round(abs(v))), ",").replace(",", ".")
    return ("−$" if v < 0 else "$") + s


LABELS = OrderedDict([
    ("trades", "Trades"),
    ("winrate", "Winrate"),
    ("gem_winst_R", "Gem. winst (R)"),
    ("gem_verlies_R", "Gem. verlies (R)"),
    ("expectancy_R", "Expectancy (R)"),
    ("t_stat", "t-stat"),
    ("profit_factor", "Profit factor"),
    ("netto_totaal", "Netto totaal"),
    ("max_dd", "Max drawdown"),
    ("beste_dag_aandeel", "Beste dag ÷ totaal"),
])
