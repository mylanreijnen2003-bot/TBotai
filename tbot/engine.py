"""Eén handelsdag voor alle portefeuilles. Gedeeld door live-run en backtest."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .features import Features
from .portfolio import Portfolio, Trade
from .strategies import FOLLOWS_UNIVERSE, STRATEGIES, USES_BAND, targets_for


@dataclass
class DayResult:
    name: str
    targets: dict[str, float] | None
    weights_before: dict[str, float]
    trades: list[Trade]
    equity: float
    cash: float
    exposure: float
    n_positions: int


def new_portfolios(cfg: dict) -> dict[str, Portfolio]:
    return {n: Portfolio(n, float(cfg["start_capital_eur"])) for n in STRATEGIES}


def step(
    t: pd.Timestamp,
    fill_date: pd.Timestamp,
    prices: dict[str, float],
    universe: list[str],
    feats: Features,
    portfolios: dict[str, Portfolio],
    cfg: dict,
    first_day: bool,
    universe_day: bool,
    cost: float | None = None,
) -> dict[str, DayResult]:
    """Signaal op het slot van dag t, uitvoering tegen `prices` (open van fill_date)."""
    cost = cfg["cost_per_side"] if cost is None else cost
    out = {}
    for name, pf in portfolios.items():
        tg = targets_for(name, t, fill_date, universe, feats, cfg, first_day, universe_day)
        before = pf.weights(prices)
        trades = pf.rebalance(
            tg,
            prices,
            universe,
            cost=cost,
            band=cfg["band"],
            min_order=cfg["min_order_eur"],
            use_band=USES_BAND[name],
            follow_universe=FOLLOWS_UNIVERSE[name],
        )
        eq = pf.value(prices)
        pos_val = eq - pf.cash
        out[name] = DayResult(
            name=name,
            targets=tg,
            weights_before=before,
            trades=trades,
            equity=eq,
            cash=pf.cash,
            exposure=pos_val / eq if eq > 0 else 0.0,
            n_positions=sum(1 for q in pf.qty.values() if q > 0),
        )
    return out
