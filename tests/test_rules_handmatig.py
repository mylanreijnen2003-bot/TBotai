"""Tests met een vooraf, met de hand uitgerekende uitkomst.

Elke test beschrijft een kleine, verzonnen koersreeks en de exacte uitkomst die
volgens HYPOTHESIS.md moet volgen. Faalt er één, dan wijkt de code af van de
vastgelegde regels: pas dan de code aan, nooit de verwachte uitkomst.
"""
import math

import numpy as np
import pandas as pd

from tbot.features import Features
from tbot.indicators import donchian_states
from tbot.portfolio import Portfolio
from tbot.strategies import s1_targets, s3_targets

KW = dict(cost=0.003, band=0.20, min_order=5.0, use_band=True, follow_universe=True)


def _series(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


# ---- Donchian (S1/S4) -----------------------------------------------------

def test_donchian_exact_states_L3():
    # dag:     0   1   2   3   4   5     6   7   8   9
    closes = [10, 11, 12, 13, 12, 11.4, 11, 14, 15, 9]
    # dag 3: 13 >= max(10,11,12)            -> aan, stop = (13+11)/2 = 12
    # dag 4: 12 niet < 12; midden 12,5      -> aan, stop 12,5
    # dag 5: 11,4 < 12,5                    -> uit
    # dag 6: 11 < max(13,12,11,4)           -> uit
    # dag 7: 14 >= max(12,11,4,11)          -> aan, stop = (14+11)/2 = 12,5
    # dag 8: 15 >= 12,5; midden 13          -> aan, stop 13
    # dag 9: 9 < 13                         -> uit
    st = donchian_states(_series(closes), [3])[3].tolist()
    assert st == [0, 0, 0, 1, 1, 0, 0, 1, 1, 0]


def test_donchian_stop_does_not_follow_middle_down():
    # dag 3: 20 >= max(10,10,10) -> aan, stop = (20+10)/2 = 15
    # dag 4: 16 >= 15; midden (20+10)/2 = 15        -> stop 15
    # dag 5: 16 >= 15; midden (20+16)/2 = 18        -> stop 18
    # dag 6: 16 < 18 -> UIT. Het midden is nu (16+16)/2 = 16; als de stop
    #        dat midden omlaag zou volgen, bleef de toestand ten onrechte aan.
    closes = [10, 10, 10, 20, 16, 16, 16]
    st = donchian_states(_series(closes), [3])[3].tolist()
    assert st == [0, 0, 0, 1, 1, 1, 0]


def test_donchian_needs_full_channel_history():
    # Met L = 5 kan er pas vanaf dag 5 een toestand 'aan' zijn, ook al stijgt de koers.
    st = donchian_states(_series([1, 2, 3, 4, 5, 6, 7]), [5])[5].tolist()
    assert st == [0, 0, 0, 0, 0, 1, 1]


# ---- S1-doelgewicht ---------------------------------------------------------

def _zigzag_up(n=500, up=0.03, down=-0.01):
    """Log-rendementen afwisselend +3% en -1%: een gestage stijging met bekende volatiliteit."""
    r = np.array([up if i % 2 == 0 else down for i in range(n - 1)])
    return _series(100 * np.exp(np.concatenate([[0.0], np.cumsum(r)])))


def test_s1_weight_by_hand(cfg):
    c = _zigzag_up()
    assert np.log(c).diff().iloc[-1] > 0              # laatste dag is een stijgdag
    f = Features({"A/EUR": c, "B/EUR": c}, cfg)
    t = c.index[-1]
    assert f.trend_fraction("A/EUR", t) == 1.0        # alle 9 trendsignalen aan
    # σ90: 90 rendementen, 45× +3% en 45× -1%, gemiddelde 1%, afwijking ±2%
    sigma = 0.02 * math.sqrt(90 / 89) * math.sqrt(365)
    assert abs(f.sigma("A/EUR", t) - sigma) < 1e-9
    w = s1_targets(t, ["A/EUR", "B/EUR"], f, cfg)
    expected = 0.5 * 1.0 * min(1.0, 0.25 / sigma)     # (1/N) × (9/9) × min(1; 0,25/σ90)
    assert abs(w["A/EUR"] - expected) < 1e-9
    assert abs(expected - 0.3253) < 1e-3              # ≈ 32,5% per munt


# ---- S3-marktschakelaar -----------------------------------------------------

def test_s3_falling_market_goes_to_cash(cfg):
    down = _series(np.linspace(200, 100, 60))
    f = Features({"A/EUR": down, "B/EUR": down * 2}, cfg)
    t = down.index[-1]
    monday = t + pd.Timedelta(days=(7 - t.weekday()) % 7 or 7)
    tg = s3_targets(monday - pd.Timedelta(days=1), monday, ["A/EUR", "B/EUR"], f, cfg)
    assert tg == {"A/EUR": 0.0, "B/EUR": 0.0}


def test_s3_rising_market_is_one_over_n(cfg):
    up = _series(np.linspace(100, 200, 60))
    f = Features({"A/EUR": up, "B/EUR": up}, cfg)
    t = up.index[-1]
    monday = t + pd.Timedelta(days=(7 - t.weekday()) % 7 or 7)
    tg = s3_targets(monday - pd.Timedelta(days=1), monday, ["A/EUR", "B/EUR"], f, cfg)
    assert tg == {"A/EUR": 0.5, "B/EUR": 0.5}


# ---- Band, minimale order, kosten ------------------------------------------

def test_band_is_strictly_more_than_20_percent():
    pf = Portfolio("X", 10_000)
    pf.rebalance({"A": 0.10}, {"A": 10.0}, ["A"], **KW)
    w = pf.weights({"A": 10.0})["A"]
    just_inside = w / 1.2 * (1 + 1e-9)    # afwijking net onder 20% -> niets doen
    just_outside = w / 1.2 * (1 - 1e-6)   # afwijking net boven 20% -> bijsturen
    assert pf.rebalance({"A": just_inside}, {"A": 10.0}, ["A"], **KW) == []
    tr = pf.rebalance({"A": just_outside}, {"A": 10.0}, ["A"], **KW)
    assert [(t.side, t.reason) for t in tr] == [("sell", "bijsturen")]


def test_full_exit_also_below_minimum_order():
    pf = Portfolio("X", 1_000, qty={"A": 0.3})         # positie van €3, onder de €5
    tr = pf.rebalance({"A": 0.0}, {"A": 10.0}, ["A"], **KW)
    assert [(t.side, t.reason) for t in tr] == [("sell", "uitstap")]
    assert abs(tr[0].notional - 3.0) < 1e-12
    assert "A" not in pf.qty


def test_partial_order_below_minimum_is_skipped():
    pf = Portfolio("X", 900, qty={"A": 10.0})          # €100 positie, vermogen €1.000
    kw = dict(KW, use_band=False)
    assert pf.rebalance({"A": 0.097}, {"A": 10.0}, ["A"], **kw) == []   # €3 verkopen < €5


def test_costs_exactly_030_percent_both_sides():
    pf = Portfolio("X", 10_000)
    buy = pf.rebalance({"A": 0.5}, {"A": 10.0}, ["A"], **KW)
    assert abs(buy[0].notional - 5_000) < 1e-9 and abs(buy[0].cost - 15.0) < 1e-9
    sell = pf.rebalance({"A": 0.0}, {"A": 12.0}, ["A"], **KW)
    assert abs(sell[0].notional - 6_000) < 1e-9 and abs(sell[0].cost - 18.0) < 1e-9
    # 10.000 − 5.000 − 15 + 6.000 − 18 = 10.967
    assert abs(pf.cash - 10_967) < 1e-9
