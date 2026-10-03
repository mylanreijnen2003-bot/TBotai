"""Journal: kolommen, automatische berekeningen, lezen/schrijven van journal.csv en journal_days.csv."""
import csv
import datetime as dt
import os
from collections import OrderedDict

from .kalender import is_dst_mismatch

COLUMNS = [
    "trade_id", "datum", "weekdag", "instaptijd", "uitstaptijd", "dst_mismatch",
    "instrument", "account", "setup", "biasreden", "richting",
    "geplande_instap", "werkelijke_instap", "stop", "doel", "contracten", "uitstapprijs",
    "uitstapreden", "risico_$", "bruto_pnl", "kosten", "netto_pnl", "R",
    "MAE_$", "MFE_$", "screenshot_link", "regels_nageleefd", "gebroken_regel",
    "emotie_voor", "emotie_na", "slaap_uren", "energie", "notitie",
]
DAY_COLUMNS = ["datum", "aantal_trades", "reden_geen_trade", "dag_pnl", "dagstop_geraakt", "plafond_geraakt"]
WEEKDAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
ACCOUNTS = ["live-sim", "replay", "combine", "funded"]
UITSTAPREDENEN = ["doel", "stop", "tijd", "handmatig"]


def num(x):
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _fmt(x, digits=2):
    return "" if x is None else ("%.*f" % (digits, x))


def is_ja(x):
    return str(x).strip().lower() in ("ja", "j", "y", "yes", "true", "1")


def compute_fields(row, config, calendar=None):
    """Vult weekdag, dst_mismatch, risico_$, bruto_pnl, kosten, netto_pnl en R in."""
    r = dict(row)
    d = dt.date.fromisoformat(str(r["datum"]).strip())
    r["weekdag"] = WEEKDAGEN[d.weekday()]
    if calendar is not None:
        r["dst_mismatch"] = "ja" if is_dst_mismatch(d, calendar) else "nee"
    inst = config["instrumenten"].get(r.get("instrument") or "MES", config["instrumenten"]["MES"])
    pv = inst["punt_waarde"]
    entry, stop, exitp = num(r.get("werkelijke_instap")), num(r.get("stop")), num(r.get("uitstapprijs"))
    n = num(r.get("contracten")) or 0
    sign = -1 if str(r.get("richting", "long")).strip().lower() == "short" else 1
    risico = abs(entry - stop) * pv * n if entry is not None and stop is not None else None
    bruto = (exitp - entry) * sign * pv * n if entry is not None and exitp is not None else None
    kosten = n * (config["kosten_per_contract_rt"] + 2 * config["slippage_ticks_per_kant"] * inst["tick_waarde"])
    netto = bruto - kosten if bruto is not None else None
    R = netto / risico if netto is not None and risico else None
    r["risico_$"] = _fmt(risico)
    r["bruto_pnl"] = _fmt(bruto)
    r["kosten"] = _fmt(kosten)
    r["netto_pnl"] = _fmt(netto)
    r["R"] = _fmt(R, 3)
    return r


def read_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_rows(path, rows, columns):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def append_trade(path, row):
    rows = read_rows(path)
    rows.append(row)
    write_rows(path, rows, COLUMNS)


def next_trade_id(rows):
    best = 0
    for r in rows:
        s = str(r.get("trade_id", ""))
        digits = "".join(ch for ch in s if ch.isdigit())
        if digits:
            best = max(best, int(digits))
    return "T%04d" % (best + 1)


def to_record(r):
    net = num(r.get("netto_pnl"))
    if net is None or not str(r.get("datum", "")).strip():
        return None
    return {
        "trade_id": r.get("trade_id", ""),
        "datum": dt.date.fromisoformat(r["datum"].strip()),
        "instaptijd": (r.get("instaptijd") or "").strip(),
        "account": (r.get("account") or "").strip().lower(),
        "setup": (r.get("setup") or "").strip(),
        "instrument": (r.get("instrument") or "").strip().upper(),
        "netto_pnl": net,
        "R": num(r.get("R")),
        "mae": num(r.get("MAE_$")),
        "kosten": num(r.get("kosten")),
        "risico": num(r.get("risico_$")),
        "regels_ok": is_ja(r.get("regels_nageleefd", "")),
    }


def records(rows, accounts=None):
    """Rijen -> gesorteerde lijst trades met getallen. accounts=None betekent alle accounts."""
    out = []
    for r in rows:
        rec = to_record(r)
        if rec is None:
            continue
        if accounts is not None and rec["account"] not in accounts:
            continue
        out.append(rec)
    out.sort(key=lambda t: (t["datum"], t["instaptijd"]))
    return out


def group_days(recs):
    """-> [(datum, [{'net_pnl', 'mae', 'kosten'}, ...]), ...] in volgorde, voor de regel-simulator."""
    days = OrderedDict()
    for t in recs:
        days.setdefault(t["datum"], []).append(
            {"net_pnl": t["netto_pnl"], "mae": t["mae"], "kosten": t.get("kosten")})
    return list(days.items())


def rebuild_days(journal_path, days_path, personal, extra_reasons=None):
    """Herberekent journal_days.csv uit de trades (replay telt niet mee). Redenen voor geen trade blijven bewaard."""
    existing = {r["datum"]: r for r in read_rows(days_path)}
    reasons = {d: r.get("reden_geen_trade", "") for d, r in existing.items()}
    reasons.update(extra_reasons or {})
    recs = [t for t in records(read_rows(journal_path)) if t["account"] != "replay"]
    out = {}
    for d, trades in group_days(recs):
        pnl = sum(t["net_pnl"] for t in trades)
        losses = sum(1 for t in trades if t["net_pnl"] < 0)
        out[d.isoformat()] = {
            "datum": d.isoformat(),
            "aantal_trades": len(trades),
            "reden_geen_trade": reasons.get(d.isoformat(), ""),
            "dag_pnl": _fmt(pnl),
            "dagstop_geraakt": "ja" if losses >= personal["dagstop_verliezen"] or pnl <= -personal["dagstop_usd"] else "nee",
            "plafond_geraakt": "ja" if pnl >= personal["winstplafond_usd"] else "nee",
        }
    for d, reden in reasons.items():
        if d not in out and reden:
            out[d] = {"datum": d, "aantal_trades": 0, "reden_geen_trade": reden, "dag_pnl": "0.00",
                      "dagstop_geraakt": "nee", "plafond_geraakt": "nee"}
    write_rows(days_path, [out[k] for k in sorted(out)], DAY_COLUMNS)
