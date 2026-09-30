"""Koersdata ophalen via ccxt (standaard Bitvavo, EUR-paren, dagcandles).

Alleen publieke marktdata: er zijn GEEN API-sleutels nodig en de bot kan
nooit echte orders plaatsen.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

DAY_MS = 86_400_000
COLS = ["open", "high", "low", "close", "volume"]


def to_frame(rows: list[list]) -> pd.DataFrame:
    """ccxt-OHLCV-rijen -> DataFrame met een datum-index (UTC, 00:00)."""
    if not rows:
        return pd.DataFrame(columns=COLS, index=pd.DatetimeIndex([], name="date"))
    df = pd.DataFrame(rows, columns=["ts"] + COLS)
    df["date"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    df = df.drop(columns="ts").drop_duplicates("date", keep="last").set_index("date").sort_index()
    return df.astype(float)


class CcxtSource:
    """Dunne laag rond ccxt, zodat tests een nep-bron kunnen gebruiken."""

    def __init__(self, exchange_id: str = "bitvavo", quote: str = "EUR"):
        import ccxt  # pas hier importeren: tests hebben geen netwerk nodig

        self.ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
        self.quote = quote
        self._markets = None

    def list_markets(self) -> list[str]:
        if self._markets is None:
            self._markets = self.ex.load_markets()
        out = []
        for sym, m in self._markets.items():
            if m.get("spot") and m.get("quote") == self.quote and m.get("active", True) is not False:
                out.append(sym)
        return sorted(out)

    def fetch_daily(self, symbol: str, days: int | None = None, since: pd.Timestamp | None = None) -> pd.DataFrame:
        """Dagcandles ophalen. Let op: de laatste rij kan de nog lopende candle van vandaag zijn."""
        now_ms = self.ex.milliseconds()
        if since is not None:
            start = int(pd.Timestamp(since).tz_localize("UTC").timestamp() * 1000)
        elif days is not None:
            start = now_ms - (days + 2) * DAY_MS
        else:
            start = int(pd.Timestamp("2018-01-01", tz="UTC").timestamp() * 1000)
        rows: list[list] = []
        cursor = start
        for _ in range(100):  # harde limiet tegen oneindige lussen
            batch = self._retry(lambda: self.ex.fetch_ohlcv(symbol, "1d", since=cursor, limit=1000))
            if not batch:
                break
            rows.extend(batch)
            last = batch[-1][0]
            if last <= cursor or last >= now_ms - DAY_MS:
                break
            cursor = last + DAY_MS
        return to_frame(rows)

    @staticmethod
    def _retry(fn, tries: int = 4):
        for i in range(tries):
            try:
                return fn()
            except Exception:  # netwerk- of rate-limitfout
                if i == tries - 1:
                    raise
                time.sleep(2 ** i)


def closed_only(df: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    """Alleen gesloten candles (datum vóór vandaag UTC)."""
    return df[df.index < today]


# ---- cache voor de backtest (niet in git) ---------------------------------

def cache_path(cache_dir: Path, symbol: str) -> Path:
    return cache_dir / (symbol.replace("/", "_") + ".csv")


def load_cached(cache_dir: Path, symbol: str) -> pd.DataFrame | None:
    p = cache_path(cache_dir, symbol)
    if not p.exists():
        return None
    return pd.read_csv(p, index_col="date", parse_dates=["date"])


def save_cached(cache_dir: Path, symbol: str, df: pd.DataFrame) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path(cache_dir, symbol), index_label="date")
