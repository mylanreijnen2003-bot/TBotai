"""Kenmerken per munt (volatiliteit, trendtoestand) op een willekeurige dag t.

Wordt gebruikt door zowel de live-run als de backtest, zodat beide exact
dezelfde berekening doen. Een waarde op dag t hangt alleen af van data t/m t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import donchian_states, keltner_states


def asof(s: pd.Series | None, t) -> float:
    """Laatste waarde van reeks s op of vóór dag t (NaN als er niets is)."""
    if s is None or len(s) == 0:
        return float("nan")
    i = s.index.searchsorted(t, side="right") - 1
    return float(s.iloc[i]) if i >= 0 else float("nan")


class Features:
    def __init__(self, closes: dict[str, pd.Series], cfg: dict,
                 highs: dict[str, pd.Series] | None = None, lows: dict[str, pd.Series] | None = None):
        self.cfg = cfg
        self.closes = {s: c.dropna().sort_index() for s, c in closes.items() if c is not None and len(c.dropna())}
        self.highs = highs or {}
        self.lows = lows or {}
        self._sigma: dict[str, pd.Series] = {}
        self._trend: dict[str, pd.Series] = {}
        self._sma: dict[tuple[str, int], pd.Series] = {}
        self._kelt: dict[str, pd.Series] = {}

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

    def sma(self, sym: str, t: pd.Timestamp, n: int) -> float:
        """Gewoon gemiddelde van de laatste n slotkoersen t/m t (NaN bij te weinig historie)."""
        key = (sym, n)
        if key not in self._sma:
            c = self.closes.get(sym)
            if c is None:
                return float("nan")
            self._sma[key] = c.rolling(n, min_periods=n).mean()
        return asof(self._sma[key], t)

    def keltner_on(self, sym: str, t: pd.Timestamp) -> bool:
        """S9-toestand (Keltner/Donchian met ratchet-stop) op dag t."""
        if sym not in self._kelt:
            c = self.closes.get(sym)
            if c is None:
                return False
            k = self.cfg["s9"]
            hi = self.highs.get(sym, c)
            lo = self.lows.get(sym, c)
            self._kelt[sym] = keltner_states(c, hi, lo, k["entry_n"], k["exit_n"], k["atr_mult"]).astype(float)
        return asof(self._kelt[sym], t) == 1.0


def from_candles(candles: dict[str, pd.DataFrame], cfg: dict) -> "Features":
    """Features uit OHLCV-tabellen (slot, hoog, laag)."""
    return Features(
        {s: d["close"] for s, d in candles.items()},
        cfg,
        {s: d["high"] for s, d in candles.items() if "high" in d},
        {s: d["low"] for s, d in candles.items() if "low" in d},
    )
