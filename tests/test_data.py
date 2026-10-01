import pandas as pd

from tbot.data import CcxtSource

DAY = 86_400_000


class FakeExchange:
    """Beurs met data pas vanaf `listed`; geeft een lege lijst voor eerdere vensters."""

    def __init__(self, listed_ms, now_ms, step):
        self.listed, self.now, self.step = listed_ms, now_ms, step

    def parse_timeframe(self, tf):
        return self.step // 1000

    def milliseconds(self):
        return self.now

    def fetch_ohlcv(self, symbol, tf, since=None, limit=1000):
        end = min(since + limit * self.step, self.now)
        start = max(since, self.listed)
        start = ((start + self.step - 1) // self.step) * self.step
        return [[t, 1, 1, 1, 1, 1] for t in range(start, end, self.step)]


def test_fetch_skips_empty_period_before_listing():
    src = CcxtSource.__new__(CcxtSource)
    now = int(pd.Timestamp("2026-10-01", tz="UTC").timestamp() * 1000)
    listed = int(pd.Timestamp("2024-03-15", tz="UTC").timestamp() * 1000)
    src.ex = FakeExchange(listed, now, DAY)
    df = src.fetch("X/EUR", "1d", since=pd.Timestamp("2019-01-01"))
    assert df.index[0] == pd.Timestamp("2024-03-15")
    assert df.index[-1] >= pd.Timestamp("2026-09-29")
    src.ex = FakeExchange(listed, now, 4 * 3600 * 1000)
    df4 = src.fetch("X/EUR", "4h", since=pd.Timestamp("2020-01-01"))
    assert df4.index[0] == pd.Timestamp("2024-03-15") and len(df4) > 5000
