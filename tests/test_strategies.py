import pandas as pd

from tbot.features import Features
from tbot.strategies import b1_targets, b2_targets, s1_targets, s2_targets, s3_targets
from tbot.universe import select_universe

from conftest import make_candles


def _feats(market, cfg):
    return Features({s: df["close"] for s, df in market.items()}, cfg)


def test_universe_filters(market, cfg):
    t = market["BTC/EUR"].index[500]
    u = select_universe(market, t, cfg)
    assert len(u) == 15
    assert "USDC/EUR" not in u                 # stablecoin uitgesloten
    assert u[0] == "BTC/EUR"                   # hoogste EUR-volume eerst


def test_universe_needs_history(market, cfg):
    t = market["BTC/EUR"].index[100]           # < 365 dagen historie
    assert select_universe(market, t, cfg) == []


def test_universe_excludes_listed_bases(market, cfg):
    market = dict(market)
    market["WBTC/EUR"] = make_candles(n=1100, seed=77, volume=1e9)
    t = market["BTC/EUR"].index[500]
    assert "WBTC/EUR" not in select_universe(market, t, cfg)


def test_weights_never_exceed_one_over_n(market, cfg):
    f = _feats(market, cfg)
    t = market["BTC/EUR"].index[800]
    u = select_universe(market, t, cfg)
    for tg in (s1_targets(t, u, f, cfg), s2_targets(t, u, f, cfg)):
        assert all(0 <= w <= 1 / len(u) + 1e-12 for w in tg.values())
        assert sum(tg.values()) <= 1 + 1e-12


def test_s2_formula(market, cfg):
    f = _feats(market, cfg)
    t = market["BTC/EUR"].index[800]
    u = ["C01/EUR", "C02/EUR"]
    tg = s2_targets(t, u, f, cfg)
    for s in u:
        assert abs(tg[s] - 0.5 * min(1, 0.25 / f.sigma(s, t))) < 1e-12


def test_s1_is_s2_times_trend(market, cfg):
    f = _feats(market, cfg)
    t = market["BTC/EUR"].index[800]
    u = ["C01/EUR", "C03/EUR"]
    a, b = s1_targets(t, u, f, cfg), s2_targets(t, u, f, cfg)
    for s in u:
        assert abs(a[s] - b[s] * f.trend_fraction(s, t)) < 1e-12


def test_s3_only_on_monday(market, cfg):
    f = _feats(market, cfg)
    u = ["C01/EUR", "C02/EUR"]
    monday = pd.Timestamp("2023-06-05")
    assert monday.weekday() == 0
    t = monday - pd.Timedelta(days=1)
    assert s3_targets(t, monday + pd.Timedelta(days=1), u, f, cfg) is None
    tg = s3_targets(t, monday, u, f, cfg)
    assert tg is not None and set(tg) == set(u)
    assert all(w in (0.0, 0.5) for w in tg.values())


def test_benchmarks(cfg):
    assert b1_targets(True, cfg) == {"BTC/EUR": 1.0}
    assert b1_targets(False, cfg) is None
    assert b2_targets(False, False, ["A", "B"]) is None
    assert b2_targets(False, True, ["A", "B"]) == {"A": 0.5, "B": 0.5}


def test_no_lookahead(market, cfg):
    """Toekomstige koersen veranderen mogen de doelgewichten van vandaag niet veranderen."""
    t = market["BTC/EUR"].index[700]
    u = ["C01/EUR", "C02/EUR", "C03/EUR"]
    f1 = _feats(market, cfg)
    changed = {}
    for s, df in market.items():
        d = df.copy()
        d.loc[d.index > t, "close"] *= 3.0
        changed[s] = d
    f2 = _feats(changed, cfg)
    for fn in (s1_targets, s2_targets):
        assert fn(t, u, f1, cfg) == fn(t, u, f2, cfg)
    monday = t - pd.Timedelta(days=t.weekday())   # maandag op of vóór t
    tm = monday - pd.Timedelta(days=1)
    assert s3_targets(tm, monday, u, f1, cfg) == s3_targets(tm, monday, u, f2, cfg)


def test_s4_is_trend_without_vol(market, cfg):
    from tbot.strategies import s4_targets

    f = _feats(market, cfg)
    t = market["BTC/EUR"].index[800]
    u = ["C01/EUR", "C03/EUR", "C04/EUR"]
    tg = s4_targets(t, u, f, cfg)
    for s in u:
        assert abs(tg[s] - f.trend_fraction(s, t) / 3) < 1e-12
    assert sum(tg.values()) <= 1 + 1e-12

