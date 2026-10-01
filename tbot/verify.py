"""Controle: doet de live-run precies wat dezelfde code met dezelfde koersen zou doen?

Elke verwerkte live-dag wordt opnieuw uitgerekend met de engine van de backtest
(`engine.step`), het opgeslagen universum van die maand en opnieuw opgehaalde
koersen. Per dag start de herberekening vanaf de echte live-stand (uit het
tradelogboek), zodat elke dag los gecontroleerd wordt en één verschil niet alle
volgende dagen meesleept.

Vergeleken worden: welke trades er zijn (munt + kant), hun bedrag, de
uitvoeringsprijs en de equity aan het eind van de dag.

Een verschil betekent: code- of datafout. Niet de regels aanpassen, maar
uitzoeken waar het vandaan komt.
"""
from __future__ import annotations

import copy
import json
import math

import pandas as pd

from .engine import step
from .features import Features
from .ledger import Ledger
from .portfolio import Portfolio
from .strategies import STRATEGIES, extra_symbols

REL_TOL = 1e-6


def _close(a: float, b: float, tol: float = REL_TOL) -> bool:
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        return False
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def symbols_needed(ledger: Ledger, cfg: dict) -> list[str]:
    """Alle munten die de live-run ooit nodig had."""
    syms = set(extra_symbols(cfg))
    for (symbols,) in ledger.db.execute("SELECT symbols FROM universe"):
        syms |= set(json.loads(symbols))
    syms |= {r[0] for r in ledger.db.execute("SELECT DISTINCT symbol FROM trades")}
    if ledger.has_table("data_windows"):
        syms |= {r[0] for r in ledger.db.execute("SELECT DISTINCT symbol FROM data_windows")}
    return sorted(syms)


def replay(ledger: Ledger, candles: dict[str, pd.DataFrame], cfg: dict) -> dict:
    """Herbereken alle geslaagde live-dagen en vergelijk ze met het logboek."""
    start_cap = float(cfg["start_capital_eur"])
    hist = int(cfg["live"]["history_days"])
    bars = ledger.ok_bars()

    trades = pd.read_sql_query(
        "SELECT strategy, date, symbol, side, qty, price, notional, cost FROM trades ORDER BY date, rowid", ledger.db
    )
    equity = pd.read_sql_query("SELECT strategy, date, equity FROM equity", ledger.db)
    eq_live = {(r.strategy, r.date): r.equity for r in equity.itertuples()}
    starts = equity.groupby("strategy")["date"].min().to_dict()
    unis = {m: (json.loads(s), a) for m, s, a in ledger.db.execute("SELECT month, symbols, asof FROM universe")}
    if ledger.has_table("data_windows"):
        win = pd.read_sql_query("SELECT * FROM data_windows", ledger.db)
    else:  # logboek van vóór de datalogging
        win = pd.DataFrame(columns=["date", "symbol", "first_bar", "last_bar", "exec_price"])

    live_state: dict[str, Portfolio] = {}
    diffs: list[str] = []
    notes: list[str] = []
    n_days = n_trades = 0
    skipped: list[str] = []

    for bar in bars:
        t = pd.Timestamp(bar)
        fill = t + pd.Timedelta(days=1)
        date = fill.date().isoformat()
        month = fill.strftime("%Y-%m")
        day_trades = trades[trades["date"] == date]

        if month not in unis:
            diffs.append(f"{date}: geen opgeslagen universum voor {month}")
            continue
        universe, asof = unis[month]
        uday = asof == bar

        # portefeuilles die op deze dag (live) bestonden
        first_day = {}
        for n in STRATEGIES:
            st = starts.get(n)
            if st is None or st > date:
                continue
            first_day[n] = n not in live_state
            if first_day[n]:
                live_state[n] = Portfolio(n, start_cap)
        sim = {n: copy.deepcopy(live_state[n]) for n in first_day}

        needed = set(universe) | extra_symbols(cfg)
        for pf in sim.values():
            needed |= set(pf.qty)

        w = win[win["date"] == date].set_index("symbol")
        logged = len(w) > 0
        tag = "" if logged else " (dag vóór de datalogging: begin koershistorie geschat)"
        if logged and set(w.index) != needed:
            diffs.append(
                f"{date}: andere munten opgehaald dan nodig "
                f"(alleen live: {sorted(set(w.index) - needed)}, alleen herberekening: {sorted(needed - set(w.index))})"
            )

        closes, highs, lows, prices, missing = {}, {}, {}, {}, []
        for s in sorted(needed):
            df = candles.get(s)
            if df is None or df.empty:
                missing.append(s)
                continue
            if logged and s in w.index and w.loc[s, "first_bar"]:
                lo, hi = pd.Timestamp(w.loc[s, "first_bar"]), pd.Timestamp(w.loc[s, "last_bar"])
            else:
                lo, hi = fill - pd.Timedelta(days=hist + 1), t
            done = df[(df.index >= lo) & (df.index <= min(hi, t))]
            closes[s] = done["close"]
            highs[s], lows[s] = done["high"], done["low"]
            if fill in df.index and df.loc[fill, "open"] > 0:
                prices[s] = float(df.loc[fill, "open"])
            elif len(done):
                prices[s] = float(done["close"].iloc[-1])
            if logged and s in w.index and s in prices and not _close(prices[s], float(w.loc[s, "exec_price"]), 1e-9):
                diffs.append(f"{date} {s}: uitvoeringsprijs live {w.loc[s, 'exec_price']} ≠ nu opgehaald {prices[s]}")
        if missing:
            notes.append(f"{date}: geen koersdata voor {', '.join(missing)}; deze dag is niet gecontroleerd")
            skipped.append(date)
            res = {}
        else:
            res = step(t, fill, prices, universe, Features(closes, cfg, highs, lows), sim, cfg, first_day, uday)

        for n, r in res.items():
            mine = {(tr.symbol, tr.side): tr for tr in r.trades}
            lv = day_trades[day_trades["strategy"] == n]
            theirs = {(x.symbol, x.side): x for x in lv.itertuples()}
            for key in sorted(set(mine) | set(theirs)):
                a, b = theirs.get(key), mine.get(key)
                if a is None:
                    diffs.append(f"{date} {n} {key[0]} {key[1]}: alleen in herberekening (€{b.notional:,.2f}){tag}")
                elif b is None:
                    diffs.append(f"{date} {n} {key[0]} {key[1]}: alleen live (€{a.notional:,.2f}){tag}")
                elif not _close(a.notional, b.notional) or not _close(a.price, b.price):
                    diffs.append(
                        f"{date} {n} {key[0]} {key[1]}: live €{a.notional:,.2f} @ {a.price} "
                        f"≠ herberekend €{b.notional:,.2f} @ {b.price}{tag}"
                    )
            n_trades += len(theirs)
            le = eq_live.get((n, date))
            if le is not None and not _close(le, r.equity):
                diffs.append(f"{date} {n}: equity live €{le:,.2f} ≠ herberekend €{r.equity:,.2f}{tag}")

        # live-stand bijwerken met de ECHTE trades van die dag (net als de reconciliatie)
        for x in day_trades.itertuples():
            pf = live_state.setdefault(x.strategy, Portfolio(x.strategy, start_cap))
            if x.side == "buy":
                pf.cash -= x.notional + x.cost
                pf.qty[x.symbol] = pf.qty.get(x.symbol, 0.0) + x.qty
            else:
                pf.cash += x.notional - x.cost
                pf.qty[x.symbol] = pf.qty.get(x.symbol, 0.0) - x.qty
                if pf.qty[x.symbol] <= 1e-12:
                    pf.qty.pop(x.symbol, None)
        for pf in live_state.values():
            if -1e-6 < pf.cash < 0:
                pf.cash = 0.0  # zelfde afronding als de live-portefeuille (nooit echt negatief)
        if not missing:
            n_days += 1

    return {
        "skipped": skipped,
        "days": n_days,
        "trades": n_trades,
        "first": bars[0] if bars else None,
        "last": bars[-1] if bars else None,
        "diffs": diffs,
        "notes": notes,
    }


def report_markdown(res: dict, checked_at: str) -> str:
    lines = [
        "# Controle: live-run tegen dezelfde code opnieuw uitgerekend",
        "",
        f"Gecontroleerd op {checked_at}. Signaaldagen {res['first']} t/m {res['last']}: "
        f"{res['days']} dagen, {res['trades']} live trades.",
        "",
    ]
    if res.get("skipped"):
        lines += [f"Niet gecontroleerd (koersdata ontbrak): {len(res['skipped'])} dag(en).", ""]
    if not res["diffs"] and res["days"] == 0:
        lines += ["**Resultaat: niets gecontroleerd.** Er was geen bruikbare koersdata.", ""]
    elif not res["diffs"]:
        lines += ["**Resultaat: geen verschillen.** Elke live trade en de equity per dag komen exact overeen.", ""]
    else:
        lines += [
            f"**Resultaat: {len(res['diffs'])} verschil(len).** Niet de regels aanpassen; eerst uitzoeken waar het vandaan komt.",
            "",
            "Mogelijke oorzaken: de beurs heeft koersen achteraf aangepast, de live-run kreeg andere data binnen,",
            "of de code wijkt af van wat er in het logboek staat.",
            "",
        ]
        lines += [f"- {d}" for d in res["diffs"][:50]]
        if len(res["diffs"]) > 50:
            lines.append(f"- … en nog {len(res['diffs']) - 50}")
        lines.append("")
    if res["notes"]:
        lines += ["Opmerkingen:", ""] + [f"- {n}" for n in res["notes"][:20]] + [""]
    return "\n".join(lines)
