"""Statistieken over trades (records uit journal.records)."""
import datetime as dt
from collections import OrderedDict

from .journal import WEEKDAGEN


def metrics(trades):
    n = len(trades)
    if n == 0:
        return {"trades": 0}
    wins = [t for t in trades if t["netto_pnl"] > 0]
    losses = [t for t in trades if t["netto_pnl"] < 0]
    rs = [t["R"] for t in trades if t["R"] is not None]
    win_rs = [t["R"] for t in wins if t["R"] is not None]
    loss_rs = [t["R"] for t in losses if t["R"] is not None]
    gross_win = sum(t["netto_pnl"] for t in wins)
    gross_loss = -sum(t["netto_pnl"] for t in losses)

    equity = peak = 0.0
    dd_close = dd_mae = 0.0
    for t in trades:
        low = equity + min(t["netto_pnl"], t["mae"] if t["mae"] is not None else 0.0, 0.0)
        dd_mae = max(dd_mae, peak - low)
        equity += t["netto_pnl"]
        dd_close = max(dd_close, peak - equity)
        peak = max(peak, equity)

    days = OrderedDict()
    for t in trades:
        days[t["datum"]] = days.get(t["datum"], 0.0) + t["netto_pnl"]
    total = sum(t["netto_pnl"] for t in trades)
    best = max(days.values())
    return {
        "trades": n,
        "winrate": len(wins) / n,
        "gem_winst_R": sum(win_rs) / len(win_rs) if win_rs else None,
        "gem_verlies_R": sum(loss_rs) / len(loss_rs) if loss_rs else None,
        "expectancy_R": sum(rs) / len(rs) if rs else None,
        "profit_factor": gross_win / gross_loss if gross_loss > 0 else None,
        "netto_totaal": total,
        "max_dd_slot": dd_close,
        "max_dd_mae": dd_mae,
        "beste_dag": best,
        "beste_dag_pct": best / total if total > 0 else None,
        "regelnaleving": sum(1 for t in trades if t["regels_ok"]) / n,
    }


def week_key(d):
    y, w, _ = d.isocalendar()
    return "%d-W%02d" % (y, w)


def month_key(d):
    return "%d-%02d" % (d.year, d.month)


def timeslot(t):
    try:
        h, m = (int(x) for x in t["instaptijd"][:5].split(":"))
    except ValueError:
        return "onbekend"
    s = h * 60 + (m // 15) * 15
    e = s + 15
    return "%02d:%02d–%02d:%02d" % (s // 60, s % 60, e // 60, e % 60)


def by_group(trades, keyfn):
    groups = OrderedDict()
    for t in trades:
        groups.setdefault(keyfn(t), []).append(t)
    return [(k, metrics(v)) for k, v in groups.items()]


def by_week(trades):
    return by_group(trades, lambda t: week_key(t["datum"]))


def by_month(trades):
    return by_group(trades, lambda t: month_key(t["datum"]))


def by_weekday(trades):
    res = dict(by_group(trades, lambda t: WEEKDAGEN[t["datum"].weekday()]))
    return [(d, res[d]) for d in WEEKDAGEN if d in res]


def by_timeslot(trades):
    return sorted(by_group(trades, timeslot))


def last_weeks(trades, weeks=4):
    if not trades:
        return []
    last = max(t["datum"] for t in trades)
    cutoff = last - dt.timedelta(days=7 * weeks)
    return [t for t in trades if t["datum"] > cutoff]


def weeks_spanned(trades):
    if not trades:
        return 0
    first = min(t["datum"] for t in trades)
    last = max(t["datum"] for t in trades)
    m1 = first - dt.timedelta(days=first.weekday())
    m2 = last - dt.timedelta(days=last.weekday())
    return (m2 - m1).days // 7 + 1


def equity_curve(trades):
    eq, out = 0.0, []
    for i, t in enumerate(trades, 1):
        eq += t["netto_pnl"]
        out.append((i, t["datum"], eq))
    return out


def fmt_metric(key, v):
    if v is None:
        return "–"
    if key in ("winrate", "beste_dag_pct", "regelnaleving"):
        return "%.0f%%" % (100 * v)
    if key.endswith("_R") or key == "profit_factor":
        return "%+.2f" % v if key.endswith("_R") else "%.2f" % v
    if key == "trades":
        return str(v)
    return "$%.2f" % v


LABELS = OrderedDict([
    ("trades", "Trades"),
    ("winrate", "Winrate"),
    ("gem_winst_R", "Gem. winst (R)"),
    ("gem_verlies_R", "Gem. verlies (R)"),
    ("expectancy_R", "Expectancy (R)"),
    ("profit_factor", "Profit factor"),
    ("netto_totaal", "Netto totaal"),
    ("max_dd_slot", "Max DD (slot)"),
    ("max_dd_mae", "Max DD (incl. MAE)"),
    ("beste_dag_pct", "Beste dag ÷ winst"),
    ("regelnaleving", "Regelnaleving"),
])
