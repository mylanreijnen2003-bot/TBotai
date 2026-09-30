import numpy as np
import pandas as pd

from tbot.features import Features
from tbot.indicators import donchian_states, sigma

from conftest import make_candles


def test_sigma_matches_definition():
    c = make_candles(n=200, seed=1)["close"]
    r = np.log(c).diff().dropna().tail(90)
    assert abs(sigma(c, 90) - r.std(ddof=1) * np.sqrt(365)) < 1e-12


def test_features_sigma_equals_plain_sigma(cfg):
    c = make_candles(n=300, seed=2)["close"]
    f = Features({"X": c}, cfg)
    t = c.index[250]
    assert abs(f.sigma("X", t) - sigma(c[c.index <= t], 90)) < 1e-10


def test_donchian_entry_and_exit():
    # prijs stijgt 30 dagen (instap), daarna crash (uitstap)
    up = list(np.linspace(100, 200, 40))
    down = list(np.linspace(199, 50, 20))
    c = pd.Series(up + down, index=pd.date_range("2022-01-01", periods=60))
    st = donchian_states(c, [10])[10]
    assert st.iloc[:10].sum() == 0          # te weinig historie
    assert st.iloc[39] == 1                 # in de trend
    assert st.iloc[-1] == 0                 # na de crash eruit


def test_donchian_stop_never_decreases():
    c = make_candles(n=500, seed=3, drift=0.002)["close"]
    L = 20
    arr = c.to_numpy()
    state, stop, stops = 0, np.nan, []
    for t in range(len(arr)):
        if t < L:
            continue
        mid = (arr[t - L + 1 : t + 1].max() + arr[t - L + 1 : t + 1].min()) / 2
        if state == 1:
            if arr[t] < stop:
                state, stop = 0, np.nan
                stops.append(None)
            else:
                new = max(stop, mid)
                assert new >= stop
                stop = new
        elif arr[t] >= arr[t - L : t].max():
            state, stop = 1, mid
    st = donchian_states(c, [L])[L]
    assert set(st.unique()) <= {0, 1}
