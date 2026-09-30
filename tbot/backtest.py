"""Backtest met exact dezelfde strategie-, portefeuille- en engine-code als live.

Let op (staat ook in de uitvoer): de data komt van de huidige Bitvavo-markten.
Munten die van Bitvavo verdwenen zijn, ontbreken -> survivorship bias
(resultaten zijn te optimistisch). Een point-in-time dataset is een latere stap.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .engine import new_portfolios, step
from .features import Features, asof
from .report import metrics, summary_markdown
from .strategies import STRATEGIES
from .universe import is_universe_day, select_universe

HOLDOUT_START = pd.Timestamp("2025-04-01")  # S1-paper loopt t/m maart 2025


def run_backtest(
    candles: dict[str, pd.DataFrame],
    cfg: dict,
    start: str | pd.Timestamp = "2020-01-01",
    end: str | pd.Timestamp | None = None,
    cost: float | None = None,
) -> dict:
    cost = cfg["cost_per_side"] if cost is None else cost
    candles = {s: df.sort_index() for s, df in candles.items() if df is not None and len(df)}
    opens = {s: df["open"] for s, df in candles.items()}
    feats = Features({s: df["close"] for s, df in candles.items()}, cfg)

    all_dates = sorted(set().union(*[df.index for df in candles.values()]))
    start = pd.Timestamp(start)
    last = all_dates[-1] if end is None else min(pd.Timestamp(end), all_dates[-1])
    days = [d for d in all_dates if start <= d < last]  # t; fill = t + 1 moet bestaan

    pfs = new_portfolios(cfg)
    universe: list[str] = []
    started = False
    eq_rows, ex_rows = {}, {}
    traded = {n: 0.0 for n in STRATEGIES}
    trade_log = []

    for t in days:
        fill = t + pd.Timedelta(days=1)
        uday = is_universe_day(fill)
        if uday or not started:
            universe = select_universe(candles, t, cfg)
            if not universe:
                continue  # nog te weinig historie
        first_day = not started
        started = True

        needed = set(universe) | {cfg["benchmark_btc_symbol"]}
        for pf in pfs.values():
            needed |= set(pf.qty)
        prices = {}
        for s in needed:
            o = opens.get(s)
            p = float(o.get(fill, float("nan"))) if o is not None else float("nan")
            if not p > 0:
                p = feats.close(s, t)  # geen open: laatste slotkoers gebruiken
            if p > 0:
                prices[s] = p

        res = step(t, fill, prices, universe, feats, pfs, cfg, first_day, uday, cost=cost)
        eq_rows[fill] = {n: r.equity for n, r in res.items()}
        ex_rows[fill] = {n: r.exposure for n, r in res.items()}
        for n, r in res.items():
            for tr in r.trades:
                traded[n] += tr.notional
                trade_log.append({"date": fill.date().isoformat(), "strategy": n, **tr.__dict__})

    equity = pd.DataFrame.from_dict(eq_rows, orient="index").sort_index()
    exposure = pd.DataFrame.from_dict(ex_rows, orient="index").sort_index()
    return {"equity": equity, "exposure": exposure, "traded": traded, "trades": trade_log, "cost": cost}


def write_results(res: dict, cfg: dict, out_dir: str | Path, label: str) -> dict:
    """Schrijf rapport (markdown), equity (csv) en kerncijfers (json)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    eq, ex = res["equity"], res["exposure"]
    parts = [
        f"# Backtest {cfg['strategy_version']} — kosten {res['cost'] * 100:.2f}% per kant",
        "",
        "> Waarschuwing: data van de huidige Bitvavo-markten. Verdwenen munten ontbreken (survivorship bias),",
        "> dus de cijfers zijn te optimistisch. Een paper-test van maanden wijst géén winnaar aan.",
        "",
    ]
    ins = eq[eq.index < HOLDOUT_START]
    hold = eq[eq.index >= HOLDOUT_START]
    cap = float(cfg["start_capital_eur"])
    parts.append(summary_markdown(eq, ex, res["traded"], "Hele periode"))
    if len(ins) > 1:
        parts.append(summary_markdown(ins / ins.iloc[0] * cap, ex.loc[ins.index], {}, "In-sample (tot april 2025)"))
    if len(hold) > 1:
        parts.append(
            summary_markdown(
                hold / hold.iloc[0] * cap, ex.loc[hold.index], {}, "Holdout (vanaf april 2025, opnieuw op €10.000 gezet) — hier telt het"
            )
        )
    (out / f"backtest_{label}.md").write_text("\n".join(parts), encoding="utf-8")
    eq.to_csv(out / f"equity_{label}.csv", index_label="date")
    pd.DataFrame(res["trades"]).to_csv(out / f"trades_{label}.csv", index=False)
    key = {n: metrics(eq[n], ex[n], res["traded"][n]) for n in eq.columns} if len(eq) > 1 else {}
    (out / f"summary_{label}.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    return key


def load_all_candles(cache_dir: str | Path) -> dict[str, pd.DataFrame]:
    out = {}
    for p in sorted(Path(cache_dir).glob("*.csv")):
        df = pd.read_csv(p, index_col="date", parse_dates=["date"])
        if len(df):
            out[p.stem.replace("_", "/", 1)] = df
    return out


def download_all(source, cfg: dict, cache_dir: str | Path, since: str = "2019-01-01", log=print) -> int:
    """Download dagcandles voor alle EUR-markten naar de cache (alleen gesloten dagen)."""
    from .data import closed_only, save_cached

    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    n = 0
    for sym in source.list_markets():
        try:
            df = source.fetch_daily(sym, since=pd.Timestamp(since))
        except Exception as e:  # een munt die faalt, stopt de rest niet
            log(f"  {sym}: overgeslagen ({e.__class__.__name__})")
            continue
        df = closed_only(df, today)
        if len(df):
            save_cached(Path(cache_dir), sym, df)
            n += 1
    return n


__all__ = ["run_backtest", "write_results", "load_all_candles", "download_all", "asof"]
