"""Indicatoren. Alles rekent alleen met data t/m dag t (geen blik in de toekomst)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sigma(closes: pd.Series, lookback: int = 90) -> float:
    """Jaarlijkse volatiliteit: stdev van dagelijkse log-rendementen over `lookback` dagen × √365."""
    r = np.log(closes).diff().dropna().tail(lookback)
    if len(r) < lookback:
        return float("nan")
    return float(r.std(ddof=1) * np.sqrt(365))


def donchian_states(closes: pd.Series, lookbacks: list[int]) -> pd.DataFrame:
    """Aan/uit-toestand per terugkijkperiode L voor één munt (S1).

    Per L en per dag t:
      - uitstap:   in positie en close_t < stop_{t-1}      -> uit
      - stop:      in positie: stop_t = max(stop_{t-1}, midden_t)
      - instap:    uit positie en close_t >= max(close_{t-L} .. close_{t-1})
                   -> aan, stop = midden_t
      midden_t = (max + min van close over de laatste L dagen t/m t) / 2
    De stop gaat alleen omhoog. Op de dag van een uitstap volgt geen nieuwe instap.
    """
    c = closes.to_numpy(dtype=float)
    n = len(c)
    out = {}
    for L in lookbacks:
        s = np.zeros(n, dtype=np.int8)
        state, stop = 0, np.nan
        for t in range(n):
            if t < L:  # te weinig historie voor dit kanaal
                s[t] = 0
                continue
            window = c[t - L + 1 : t + 1]
            mid = (window.max() + window.min()) / 2.0
            if state == 1:
                if c[t] < stop:
                    state, stop = 0, np.nan
                else:
                    stop = max(stop, mid)
            elif c[t] >= c[t - L : t].max():
                state, stop = 1, mid
            s[t] = state
        out[L] = s
    return pd.DataFrame(out, index=closes.index)


def trend_fraction(closes: pd.Series, lookbacks: list[int]) -> float:
    """Aandeel actieve trendsignalen op de laatste dag (0..1)."""
    if len(closes) == 0:
        return 0.0
    st = donchian_states(closes, lookbacks)
    return float(st.iloc[-1].sum() / len(lookbacks))


def keltner_states(close: pd.Series, high: pd.Series, low: pd.Series, entry_n: int = 20, exit_n: int = 40,
                   mult: float = 2.0) -> pd.Series:
    """Aan/uit-toestand voor S9 (Keltner/Donchian met ratchet-stop), per dag.

    Upper_t = min(hoogste slot over entry_n dagen t/m t, EMA_entry_n + mult × ATR_entry_n)
    Lower_t = max(laagste slot over exit_n dagen t/m t, EMA_exit_n − mult × ATR_exit_n)
    Instap:  uit en close_t ≥ Upper_{t−1}  → aan, stop = Lower_t
    In positie: close_t < stop_{t−1} → uit; anders stop = max(stop, Lower_t)  (stop gaat nooit omlaag)
    ATR = gewoon gemiddelde van de True Range; EMA = exponentieel gemiddelde (span n, adjust=False).
    """
    c = close.astype(float)
    h = high.reindex(c.index).astype(float).fillna(c)
    lo = low.reindex(c.index).astype(float).fillna(c)
    prev = c.shift(1)
    tr = pd.concat([h - lo, (h - prev).abs(), (lo - prev).abs()], axis=1).max(axis=1)
    atr_e = tr.rolling(entry_n, min_periods=entry_n).mean()
    atr_x = tr.rolling(exit_n, min_periods=exit_n).mean()
    ema_e = c.ewm(span=entry_n, adjust=False).mean()
    ema_x = c.ewm(span=exit_n, adjust=False).mean()
    upper = np.minimum(c.rolling(entry_n, min_periods=entry_n).max(), ema_e + mult * atr_e).to_numpy()
    lower = np.maximum(c.rolling(exit_n, min_periods=exit_n).min(), ema_x - mult * atr_x).to_numpy()
    cv = c.to_numpy()
    out = np.zeros(len(cv), dtype=np.int8)
    state, stop = 0, np.nan
    for t in range(1, len(cv)):
        if state == 1:
            if cv[t] < stop:
                state, stop = 0, np.nan
            elif not np.isnan(lower[t]):
                stop = max(stop, lower[t])
        elif not np.isnan(upper[t - 1]) and not np.isnan(lower[t]) and cv[t] >= upper[t - 1]:
            state, stop = 1, lower[t]
        out[t] = state
    return pd.Series(out, index=c.index)
