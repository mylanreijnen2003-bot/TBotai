"""Kenmerken per munt (volatiliteit, trendtoestand) op een willekeurige dag t.

Wordt gebruikt door zowel de live-run als de backtest, zodat beide exact
dezelfde berekening doen. Een waarde op dag t hangt alleen af van data t/m t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import donchian_states


def asof(s: pd.Series | None, t) -> float:
    """Laatste waarde van reeks s op of vóór dag t (NaN als er niets is)."""
    if s is None or len(s) == 0:
        return float("nan")
    i = s.index.searchsorted(t, side="right") - 1
    return float(s.iloc[i]) if i >= 0 else float("nan")


class Features:
    def __init__(self, closes: dict[str, pd.Series], cfg: dict):
        self.cfg = cfg
        self.closes = {s: c.dropna().sort_index() for s, c in closes.items() if c is not None and len(c.dropna())}
        self._sigma: dict[str, pd.Series] = {}
        self._trend: dict[str, pd.Series] = {}

    def has(self, sym: str) -> bool:
        return sym in self.closes

    def close(self, sym: str, t: pd.Timestamp) -> float:
        return asof(self.closes.get(sym), t)

    def ret(self, sym: str, t: pd.Timestamp, days: int) -> float:
        """close_t / close_{t-days} - 1 (op kalenderdatum)."""
        now = self.close(sym, t)
        then = self.close(sym, t - pd.Timedelta(days=days))
        if np.isnan(now) or np.isnan(then) or then <= 0:
            return float("nan")
        return now / then - 1.0

    def sigma(self, sym: str, t: pd.Timestamp) -> float:
        if sym not in self._sigma:
            c = self.closes.get(sym)
            if c is None:
                return float("nan")
            lb = self.cfg["vol_lookback"]
            self._sigma[sym] = np.log(c).diff().rolling(lb, min_periods=lb).std(ddof=1) * np.sqrt(365)
        return asof(self._sigma[sym], t)

    def trend_fraction(self, sym: str, t: pd.Timestamp) -> float:
        if sym not in self._trend:
            c = self.closes.get(sym)
            if c is None:
                return 0.0
            lbs = self.cfg["s1_lookbacks"]
            self._trend[sym] = donchian_states(c, lbs).sum(axis=1) / len(lbs)
        v = asof(self._trend[sym], t)
        return 0.0 if np.isnan(v) else v
