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
