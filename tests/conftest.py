"""Gedeelde testhulp: synthetische koersen en een nep-databron (geen netwerk)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tbot.config import load_config  # noqa: E402


def make_candles(n=900, start="2021-01-01", drift=0.0005, vol=0.03, seed=0, price=100.0, volume=1_000.0):
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, vol, n)
    close = price * np.exp(np.cumsum(r))
    open_ = np.concatenate([[price], close[:-1]])
    idx = pd.date_range(start, periods=n, freq="D", name="date")
    return pd.DataFrame(
        {"open": open_, "high": np.maximum(open_, close) * 1.01, "low": np.minimum(open_, close) * 0.99,
         "close": close, "volume": np.full(n, volume)},
        index=idx,
    )


class FakeSource:
    """Gedraagt zich als CcxtSource, maar met vaste data en een instelbaar 'nu'."""

    def __init__(self, candles: dict[str, pd.DataFrame]):
        self.candles = candles
        self.today = None

    def list_markets(self):
        return sorted(self.candles)

    def fetch_daily(self, symbol, days=None, since=None):
        df = self.candles[symbol]
        df = df[df.index <= self.today]  # inclusief de lopende candle van vandaag
        if days is not None:
            df = df.tail(days + 1)
        return df.copy()


@pytest.fixture
def cfg():
    c = load_config()
    c["live"]["fear_greed"] = False
    c["live"]["funding"] = False
    return c


@pytest.fixture
def market():
    """20 munten + een stablecoin, ~3 jaar dagdata."""
    coins = {}
    for i in range(20):
        coins[f"C{i:02d}/EUR"] = make_candles(n=1100, seed=i, drift=0.0003 * (i % 5 - 1), volume=1000 + 100 * i)
    coins["BTC/EUR"] = make_candles(n=1100, seed=99, drift=0.0008, volume=50_000, price=30_000)
    stable = make_candles(n=1100, seed=5, vol=0.0005, drift=0.0, volume=1e9, price=1.0)
    coins["USDC/EUR"] = stable
    return coins
