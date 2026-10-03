"""Eigen journal: bot_mgc/journal_bot.csv. Zelfde kolommen als journal.csv. Schrijft nooit in andere journals."""
import csv
import datetime as dt
import os
from pathlib import Path

from .instellingen import BOT
from .tijd import ET, NL

JOURNAL = BOT / "journal_bot.csv"
COLUMNS = [
    "trade_id", "datum", "weekdag", "instaptijd", "uitstaptijd", "dst_mismatch",
    "instrument", "account", "setup", "biasreden", "richting",
    "geplande_instap", "werkelijke_instap", "stop", "doel", "contracten", "uitstapprijs",
    "uitstapreden", "risico_$", "bruto_pnl", "kosten", "netto_pnl", "R",
    "MAE_$", "MFE_$", "screenshot_link", "regels_nageleefd", "gebroken_regel",
    "emotie_voor", "emotie_na", "slaap_uren", "energie", "notitie",
]
WEEKDAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
ACCOUNTS = ("mgc-backtest", "mgc-paper", "mgc-sim", "mgc-combine")
LIVE_ACCOUNTS = ("mgc-paper", "mgc-sim", "mgc-combine")


def _nl(datum, hhmm):
    if not hhmm or ":" not in str(hhmm):
        return ""
    h, m = (int(x) for x in str(hhmm)[:5].split(":"))
    return dt.datetime(datum.year, datum.month, datum.day, h, m, tzinfo=ET).astimezone(NL).strftime("%H:%M")


def is_dst_mismatch(datum):
    """Normaal is NL 6 uur later dan New York. In de mismatchweken 5 uur."""
    t = dt.datetime(datum.year, datum.month, datum.day, 12, tzinfo=ET)
    return (t.astimezone(NL).utcoffset() - t.utcoffset()) != dt.timedelta(hours=6)


def lees(pad=JOURNAL):
    if not os.path.exists(pad):
        return []
    with open(pad, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def schrijf(rows, pad=JOURNAL):
    Path(pad).parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def trade_rij(t, account, setup, trade_id):
    d = t["datum"]
    r = t.get("R")
    bias = "ROD %+.3f%%" % (100 * t["rod"]) if t.get("rod") is not None else ""
    if t.get("mediaan") is not None:
        bias += " (mediaan %.3f%%)" % (100 * t["mediaan"])
    if t.get("onfh") is not None:
        bias += "; ochtend %+.3f%%" % (100 * t["onfh"])
    notitie = "ET %s–%s; stop %.1f punten" % (t.get("instap_bar") or "", t.get("uitstap_bar") or "", t["stop_afstand"])
    if t.get("fomc"):
        notitie += "; FOMC-dag"
    if t.get("notitie"):
        notitie += "; " + t["notitie"]
    return {
        "trade_id": trade_id, "datum": d.isoformat(), "weekdag": WEEKDAGEN[d.weekday()],
        "instaptijd": _nl(d, t.get("instap_bar")), "uitstaptijd": _nl(d, t.get("uitstap_bar")),
        "dst_mismatch": "ja" if is_dst_mismatch(d) else "nee", "instrument": "MGC", "account": account,
        "setup": setup, "biasreden": bias, "richting": "long" if t["richting"] > 0 else "short",
        "geplande_instap": "%.1f" % t["signaal"], "werkelijke_instap": "%.1f" % t["instap"], "stop": "%.1f" % t["stop"],
        "doel": "", "contracten": t["contracten"], "uitstapprijs": "%.1f" % t["uitstap"],
        "uitstapreden": t.get("uitstapreden", ""), "risico_$": "%.2f" % t["risico"], "bruto_pnl": "%.2f" % t["bruto"],
        "kosten": "%.2f" % t["kosten"], "netto_pnl": "%.2f" % t["netto"], "R": "" if r is None else "%.3f" % r,
        "MAE_$": "%.2f" % t.get("mae", 0.0), "MFE_$": "%.2f" % t.get("mfe", 0.0), "screenshot_link": "",
        "regels_nageleefd": "ja", "gebroken_regel": "", "emotie_voor": "", "emotie_na": "", "slaap_uren": "",
        "energie": "", "notitie": notitie,
    }


def schrijf_backtest_journal(trades_per_variant, pad=JOURNAL):
    """Vervangt alle mgc-backtest-rijen; paper-, sim- en combine-rijen blijven staan."""
    rows = [r for r in lees(pad) if r.get("account") != "mgc-backtest"]
    nieuw = []
    for var, trades in trades_per_variant.items():
        for i, t in enumerate(sorted(trades, key=lambda x: x["datum"]), 1):
            nieuw.append(trade_rij(t, "mgc-backtest", "G-" + var, "MGB%s%05d" % (var, i)))
    nieuw.sort(key=lambda r: (r["datum"], r["setup"]))
    schrijf(nieuw + rows, pad)
    return len(nieuw)


def voeg_live_trade_toe(t, account, setup="G-A", pad=JOURNAL):
    assert account in LIVE_ACCOUNTS
    rows = lees(pad)
    n = sum(1 for r in rows if r.get("account") == account) + 1
    rows.append(trade_rij(t, account, setup, "MG%s%05d" % (account[4].upper(), n)))
    schrijf(rows, pad)


def live_trades(account, pad=JOURNAL, setup="G-A"):
    """-> [(datum, netto, mae, R)] voor het virtuele account en de bewaking."""
    out = []
    for r in lees(pad):
        if r.get("account") != account or r.get("setup") != setup:
            continue
        try:
            out.append((dt.date.fromisoformat(r["datum"]), float(r["netto_pnl"]), float(r["MAE_$"] or 0),
                        float(r["R"]) if r.get("R") else None))
        except (ValueError, KeyError):
            continue
    return out
