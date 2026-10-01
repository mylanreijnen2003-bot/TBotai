"""4-uurs spoor: S6 (korte trendsprongen op BTC, ETH, SOL) met eigen logboek in state_4h/.

Regels (HYPOTHESIS.md, aanvulling 1 okt 2026):
- Per munt een Donchian-toestand over 20 candles van 4 uur (zelfde logica als S1):
  instap als de slotkoers het hoogste slot van de vorige 20 candles evenaart of breekt;
  vangnet = midden van het 20-candle-kanaal, schuift alleen omhoog; uitstap onder het vangnet.
- In positie: 1/3 van het vermogen per munt (bij instap), daarna geen bijsturing.
- Signaal op het slot van candle t, uitvoering tegen de open van candle t+1.
Benchmarks in dit spoor: HB1 = 100% BTC vasthouden, HB3 = 1/3 BTC, ETH, SOL vasthouden.
Backtest en live gebruiken exact dezelfde functies hieronder.
"""
from __future__ import annotations

import json
import traceback
from pathlib import Path

import pandas as pd

from . import notify
from .config import ROOT
from .engine import DayResult
from .features import asof
from .indicators import donchian_states
from .ledger import Ledger
from .portfolio import Portfolio
from .report import fmt_num, fmt_pct, metrics

H4_STRATEGIES = ["S6", "HB1", "HB3"]
BAR = pd.Timedelta(hours=4)


class H4Signals:
    """Donchian-toestand per munt; waarde op candle t hangt alleen af van data t/m t."""

    def __init__(self, closes: dict[str, pd.Series], lookback: int):
        self.state = {
            s: donchian_states(c.dropna().sort_index(), [lookback])[lookback].astype(float)
            for s, c in closes.items()
            if c is not None and len(c.dropna())
        }

    def on(self, sym: str, t) -> bool:
        v = asof(self.state.get(sym), t)
        return bool(v == 1.0)


def h4_targets(name: str, t, signals: H4Signals, weights: dict[str, float], syms: list[str], first_bar: bool):
    n = len(syms)
    if name == "S6":
        tg = {}
        for s in syms:
            if signals.on(s, t):
                w = weights.get(s, 0.0)
                tg[s] = w if w > 0 else 1.0 / n  # al in positie: laten staan
            else:
                tg[s] = 0.0
        return tg
    if name == "HB1":
        return {syms[0]: 1.0} if first_bar else None
    if name == "HB3":
        return {s: 1.0 / n for s in syms} if first_bar else None
    raise ValueError(name)


def h4_step(t, prices, signals, pfs: dict[str, Portfolio], cfg: dict, first_bar, cost: float | None = None):
    h = cfg["h4"]
    cost = h["cost_per_side"] if cost is None else cost
    syms = h["symbols"]
    out = {}
    for name, pf in pfs.items():
        fb = first_bar.get(name, False) if isinstance(first_bar, dict) else first_bar
        before = pf.weights(prices)
        tg = h4_targets(name, t, signals, before, syms, fb)
        trades = pf.rebalance(
            tg, prices, syms, cost=cost, band=cfg["band"], min_order=cfg["min_order_eur"],
            use_band=(name == "S6"), follow_universe=False,
        )
        eq = pf.value(prices)
        out[name] = DayResult(name, tg, before, trades, eq, pf.cash, (eq - pf.cash) / eq if eq > 0 else 0.0,
                              sum(1 for q in pf.qty.values() if q > 0))
    return out


# ---------------------------------------------------------------- backtest

def run_backtest_h4(candles: dict[str, pd.DataFrame], cfg: dict, start="2021-01-01", end=None, cost=None) -> dict:
    h = cfg["h4"]
    cost = h["cost_per_side"] if cost is None else cost
    syms = h["symbols"]
    candles = {s: candles[s].sort_index() for s in syms}
    signals = H4Signals({s: df["close"] for s, df in candles.items()}, h["lookback"])
    bars = sorted(set.intersection(*[set(df.index) for df in candles.values()]))
    bars = [b for b in bars if b >= pd.Timestamp(start) and (end is None or b <= pd.Timestamp(end))]
    pfs = {n: Portfolio(n, float(cfg["start_capital_eur"])) for n in H4_STRATEGIES}
    eq_rows, ex_rows, traded, trades = {}, {}, {n: 0.0 for n in H4_STRATEGIES}, []
    for i, t in enumerate(bars[:-1]):
        fill = bars[i + 1]
        prices = {s: float(candles[s].at[fill, "open"]) for s in syms}
        res = h4_step(t, prices, signals, pfs, cfg, i == 0, cost=cost)
        eq_rows[fill] = {n: r.equity for n, r in res.items()}
        ex_rows[fill] = {n: r.exposure for n, r in res.items()}
        for n, r in res.items():
            for tr in r.trades:
                traded[n] += tr.notional
                trades.append({"time": fill.isoformat(), "strategy": n, **tr.__dict__})
    return {
        "equity": pd.DataFrame.from_dict(eq_rows, orient="index").sort_index(),
        "exposure": pd.DataFrame.from_dict(ex_rows, orient="index").sort_index(),
        "traded": traded, "trades": trades, "cost": cost,
    }


def round_trips(trades: list[dict] | pd.DataFrame, strategy: str = "S6") -> pd.DataFrame:
    """Koppel elke instap aan de volgende volledige uitstap per munt; rendement na kosten."""
    df = pd.DataFrame(trades)
    if df.empty:
        return pd.DataFrame(columns=["symbol", "in", "out", "ret"])
    tcol = "time" if "time" in df else "date"
    df = df[df["strategy"] == strategy].sort_values(tcol)
    rows, open_ = [], {}
    for _, r in df.iterrows():
        if r["side"] == "buy" and r["symbol"] not in open_:
            open_[r["symbol"]] = (r[tcol], r["notional"] + r["cost"])
        elif r["side"] == "sell" and r["symbol"] in open_:
            t_in, paid = open_.pop(r["symbol"])
            rows.append({"symbol": r["symbol"], "in": t_in, "out": r[tcol], "ret": (r["notional"] - r["cost"]) / paid - 1})
    return pd.DataFrame(rows)


def _daily(eq: pd.DataFrame) -> pd.DataFrame:
    return eq.resample("1D").last().dropna(how="all")


def h4_table(eq: pd.DataFrame, ex: pd.DataFrame, cap: float, extra: dict | None = None) -> list[str]:
    d = _daily(eq)
    exd = ex.resample("1D").mean() if ex is not None and not ex.empty else None
    lines = ["| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Gem. belegd |", "|---|---|---|---|---|---|"]
    cols = list(d.columns) + list((extra or {}).keys())
    for c in cols:
        s = d[c] if c in d else extra[c]
        s = s.dropna()
        if len(s) < 2:
            continue
        s = s / s.iloc[0] * cap
        m = metrics(s, exd[c] if exd is not None and c in exd else None)
        lines.append(
            f"| {c} | €{m['eindwaarde']:,.0f} | {fmt_pct(m['cagr'])} | {fmt_num(m['sharpe'])} | "
            f"{fmt_pct(m['max_drawdown'])} | {fmt_pct(m.get('gem_blootstelling'))} |"
        )
    return lines


def write_results_h4(res: dict, cfg: dict, out_dir: str | Path, label: str, s5: pd.Series | None = None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    eq, ex = res["equity"], res["exposure"]
    cap = float(cfg["start_capital_eur"])
    rt = round_trips(res["trades"])
    hold_start = pd.Timestamp("2025-04-01")
    parts = [
        f"# Backtest 4-uurs spoor (S6) — kosten {res['cost'] * 100:.2f}% per kant",
        "",
        "> Ter vergelijking staat S5 (dagversie op BTC, 0,30% kosten) erbij, over dezelfde dagen.",
        "",
    ]
    for title, sl in [("Hele periode", slice(None, None)), ("Holdout (vanaf april 2025) — hier telt het", slice(hold_start, None))]:
        e, x = eq.loc[sl], ex.loc[sl]
        extra = None
        if s5 is not None and len(e):
            s5d = s5[(s5.index >= _daily(e).index[0]) & (s5.index <= _daily(e).index[-1])]
            extra = {"S5 (dag)": s5d} if len(s5d) > 1 else None
        parts += [f"## {title}", "", f"Periode: {e.index[0].date()} t/m {e.index[-1].date()}", ""] if len(e) else [f"## {title}", ""]
        if len(e) > 1:
            parts += h4_table(e, x, cap, extra) + [""]
            r = rt[pd.to_datetime(rt["out"]) >= (e.index[0])] if len(rt) else rt
            if len(r):
                parts += [
                    f"S6-trades: {len(r)} afgerond, {r['ret'].gt(0).mean() * 100:.0f}% winstgevend, "
                    f"gemiddeld {r['ret'].mean() * 100:+.2f}% per trade na kosten "
                    f"(winst gem. {r.loc[r.ret > 0, 'ret'].mean() * 100:+.2f}%, verlies gem. {r.loc[r.ret <= 0, 'ret'].mean() * 100:+.2f}%).",
                    "",
                ]
    (out / f"backtest_4h_{label}.md").write_text("\n".join(parts), encoding="utf-8")
    eq.to_csv(out / f"equity_4h_{label}.csv", index_label="time")
    rt.to_csv(out / f"roundtrips_4h_{label}.csv", index=False)
    d = _daily(eq)
    key = {c: metrics(d[c]) for c in d.columns}
    (out / f"summary_4h_{label}.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    return key


# ---------------------------------------------------------------- live

def run_live_h4(
    cfg: dict,
    source,
    state_dir: str | Path = ROOT / "state_4h",
    now: pd.Timestamp | None = None,
    kill_file: str | Path = ROOT / "KILL",
    log=print,
) -> str:
    h = cfg["h4"]
    syms = h["symbols"]
    state_dir = Path(state_dir)
    now = pd.Timestamp.now(tz="UTC").tz_localize(None) if now is None else pd.Timestamp(now)
    cur = now.floor("4h")  # lopende candle
    now_iso = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")

    if Path(kill_file).exists():
        log("KILL-bestand gevonden: 4-uurs spoor staat stil.")
        return "killed"

    ledger = Ledger(state_dir / "ledger.db")
    cap = float(cfg["start_capital_eur"])
    problems = ledger.reconcile(cap)
    if problems:
        msg = "Reconciliatie 4-uurs spoor mislukt, bot stopt:\n" + "\n".join(problems[:10])
        log(msg)
        notify.telegram(f"TBotai 4u ⚠️ {msg}")
        return "halted"

    try:
        data = {s: source.fetch(s, h["timeframe"], bars=h["history_bars"]) for s in syms}
        closed = {s: df[df.index < cur] for s, df in data.items()}
        common = sorted(set.intersection(*[set(df.index) for df in closed.values()]))
        if not common:
            raise RuntimeError("geen gesloten 4-uurs candles ontvangen")
        last = ledger.get_meta("last_bar")
        pending = [b for b in common if last is None or b > pd.Timestamp(last)]
        if last is None:
            pending = pending[-1:]
        pending = pending[-h["max_catchup_bars"]:]
        if not pending:
            log("Geen nieuwe 4-uurs candle; niets te doen.")
            return "skip"

        signals = H4Signals({s: df["close"] for s, df in closed.items()}, h["lookback"])
        pfs = ledger.load_portfolios()
        if not pfs:
            ledger.set_meta("start_time", (pending[0] + BAR).isoformat())
            ledger.set_meta("strategy_version", cfg["strategy_version"])
        first = {n: n not in pfs for n in H4_STRATEGIES}
        for n in H4_STRATEGIES:
            pfs.setdefault(n, Portfolio(n, cap))

        msgs = []
        for t in pending:
            fill = t + BAR
            prices = {}
            for s in syms:
                df = data[s]
                if fill in df.index and df.at[fill, "open"] > 0:
                    prices[s] = float(df.at[fill, "open"])
                else:
                    prices[s] = float(closed[s].loc[:t, "close"].iloc[-1])
            res = h4_step(t, prices, signals, pfs, cfg, first)
            first = {n: False for n in H4_STRATEGIES}
            stamp = fill.isoformat()
            for n, r in res.items():
                ledger.add_trades(n, stamp, r.trades, cfg["strategy_version"])
                ledger.save_portfolio(pfs[n])
                ledger.add_equity(n, stamp, r.equity, r.cash, r.exposure, r.n_positions)
                for tr in r.trades:
                    if n == "S6":
                        msgs.append(f"{tr.side} {tr.symbol} @ {tr.price:,.2f} ({tr.reason})")
            ledger.record_run(t.isoformat(), now_iso, "ok", "")
            ledger.set_meta("last_bar", t.isoformat())
        ledger.commit()
        post = ledger.reconcile(cap)
        if post:
            raise RuntimeError("Reconciliatie na run mislukt: " + "; ".join(post[:5]))
        ledger.export_csv(state_dir)
        write_summary_h4(ledger, state_dir, cap)
        log(f"4-uurs spoor: {len(pending)} candle(s) verwerkt, {len(msgs)} S6-trade(s).")
        if msgs:
            notify.telegram("TBotai 4u S6:\n" + "\n".join(msgs))
        return "ok"
    except Exception as e:
        ledger.rollback()
        log(traceback.format_exc())
        notify.telegram(f"TBotai 4u ⚠️ run mislukt: {e.__class__.__name__}: {e}")
        return "error"


def write_summary_h4(ledger: Ledger, state_dir: Path, cap: float) -> None:
    df = pd.read_sql_query("SELECT * FROM equity", ledger.db)
    lines = ["# Live 4-uurs spoor (S6) — stand van zaken", "", f"Start: {ledger.get_meta('start_time')}", ""]
    if df.empty:
        lines.append("Nog geen data.")
    else:
        df["date"] = pd.to_datetime(df["date"])
        eq = df.pivot(index="date", columns="strategy", values="equity").sort_index()
        ex = df.pivot(index="date", columns="strategy", values="exposure").sort_index()
        lines += ["| Portefeuille | Waarde | Rendement | Max drawdown | Belegd nu |", "|---|---|---|---|---|"]
        for c in [x for x in H4_STRATEGIES if x in eq]:
            s = eq[c].dropna()
            lines.append(
                f"| {c} | €{s.iloc[-1]:,.0f} | {fmt_pct(s.iloc[-1] / cap - 1)} | "
                f"{fmt_pct(float((s / s.cummax() - 1).min()))} | {fmt_pct(ex[c].dropna().iloc[-1])} |"
            )
        tr = pd.read_sql_query("SELECT * FROM trades", ledger.db)
        rt = round_trips(tr)
        lines += ["", f"S6: {len(rt)} afgeronde trades"
                  + (f", {rt['ret'].gt(0).mean() * 100:.0f}% winstgevend, gem. {rt['ret'].mean() * 100:+.2f}% na kosten." if len(rt) else ".")]
        lines += ["", "Rendement inclusief kosten, vanaf €10.000. Na een paar weken zegt dit nog niets."]
    (state_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = ["H4_STRATEGIES", "h4_targets", "h4_step", "run_backtest_h4", "write_results_h4", "run_live_h4", "round_trips"]
