import numpy as np
import pandas as pd

from tbot.features import Features
from tbot.indicators import keltner_states
from tbot.strategies import s4_targets, s7_targets, s8_targets, s9_targets, s10_targets


def _series(vals, start="2022-01-01"):
    return pd.Series(vals, index=pd.date_range(start, periods=len(vals)), dtype=float)


def test_s10_counts_smas(cfg):
    # 400 dagen op 100, daarna 50 dagen op 200: slot boven alle drie de gemiddelden
    c = _series([100.0] * 400 + [200.0] * 50)
    f = Features({"BTC/EUR": c}, cfg)
    assert s10_targets(c.index[-1], f, cfg) == {"BTC/EUR": 1.0}
    # te weinig historie voor SMA350 en SMA200: alleen SMA100 telt mee
    c2 = _series([100.0] * 150 + [200.0] * 10)
    f2 = Features({"BTC/EUR": c2}, cfg)
    assert abs(s10_targets(c2.index[-1], f2, cfg)["BTC/EUR"] - 1 / 3) < 1e-12
    # dalend: onder alle gemiddelden
    c3 = _series(list(np.linspace(300, 100, 400)))
    f3 = Features({"BTC/EUR": c3}, cfg)
    assert s10_targets(c3.index[-1], f3, cfg) == {"BTC/EUR": 0.0}


def test_s7_is_s4_times_regime(market, cfg):
    f = Features({s: d["close"] for s, d in market.items()}, cfg)
    u = ["C01/EUR", "C02/EUR", "C03/EUR"]
    for i in (500, 700, 900):
        t = market["BTC/EUR"].index[i]
        on = f.close("BTC/EUR", t) > f.sma("BTC/EUR", t, 200)
        a, b = s7_targets(t, u, f, cfg), s4_targets(t, u, f, cfg)
        for s in u:
            assert a[s] == (b[s] if on else 0.0)


def test_s8_weekly_and_scores(market, cfg):
    f = Features({s: d["close"] for s, d in market.items()}, cfg)
    monday = pd.Timestamp("2023-06-05")
    t = monday - pd.Timedelta(days=1)
    assert s8_targets(t, monday + pd.Timedelta(days=2), f, cfg) is None
    tg = s8_targets(t, monday, f, cfg)
    assert set(tg) == {"BTC/EUR", "ETH/EUR"}
    for w in tg.values():
        assert any(abs(w - k / 6) < 1e-12 for k in range(4))


def test_keltner_entry_ratchet_exit():
    up = list(np.linspace(110, 100, 60)) + list(np.linspace(100, 200, 60))
    down = list(np.linspace(199, 80, 40))
    c = _series(up + down)
    st = keltner_states(c, c, c, 20, 40, 2.0)
    assert st.iloc[:60].sum() == 0          # dalend: niet in
    assert st.iloc[110] == 1                # in de stijging
    assert st.iloc[-1] == 0                 # na de daling eruit


def test_s9_weights_capped(market, cfg):
    f = Features({s: d["close"] for s, d in market.items()}, cfg)
    t = market["BTC/EUR"].index[900]
    u = [f"C{i:02d}/EUR" for i in range(15)]
    tg = s9_targets(t, u, f, cfg)
    assert all(0 <= w <= 1.5 / 15 + 1e-12 for w in tg.values())
    assert sum(tg.values()) <= 1 + 1e-12


def test_mix_is_weighted_average(market, cfg):
    from tbot.strategies import mix_targets, s1_targets, s8_latest_targets

    f = Features({s: d["close"] for s, d in market.items()}, cfg)
    t = market["BTC/EUR"].index[800]
    fill = t + pd.Timedelta(days=1)
    u = [f"C{i:02d}/EUR" for i in range(15)]
    m2 = mix_targets("M2", t, fill, u, f, cfg)
    a, b = s1_targets(t, u, f, cfg), s8_latest_targets(t, fill, f, cfg)
    for s in set(a) | set(b):
        assert abs(m2.get(s, 0) - (0.5 * a.get(s, 0) + 0.5 * b.get(s, 0))) < 1e-12
    assert sum(m2.values()) <= 1 + 1e-9
    m1 = mix_targets("M1", t, fill, u, f, cfg)
    assert sum(m1.values()) <= 1 + 1e-9


def test_s8_latest_uses_last_monday(market, cfg):
    from tbot.strategies import s8_latest_targets

    f = Features({s: d["close"] for s, d in market.items()}, cfg)
    monday = pd.Timestamp("2023-06-05")
    base = s8_targets(monday - pd.Timedelta(days=1), monday, f, cfg)
    for k in range(7):
        day = monday + pd.Timedelta(days=k)
        assert s8_latest_targets(day - pd.Timedelta(days=1), day, f, cfg) == base
