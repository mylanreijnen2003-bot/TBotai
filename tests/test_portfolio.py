import pytest

from tbot.portfolio import Portfolio

KW = dict(cost=0.003, band=0.20, min_order=5.0, use_band=True, follow_universe=True)


def test_buy_costs_and_no_leverage():
    pf = Portfolio("X", 10_000)
    tr = pf.rebalance({"A": 0.5, "B": 0.6}, {"A": 10.0, "B": 20.0}, ["A", "B"], **KW)
    assert pf.cash >= 0
    assert sum(t.notional + t.cost for t in tr) <= 10_000 + 1e-6   # nooit meer dan het cash
    assert all(t.side == "buy" for t in tr)
    assert all(abs(t.cost - t.notional * 0.003) < 1e-9 for t in tr)


def test_sell_then_buy_and_value_conserved_minus_costs():
    pf = Portfolio("X", 10_000)
    pf.rebalance({"A": 0.5}, {"A": 10.0}, ["A", "B"], **KW)
    v0 = pf.value({"A": 10.0, "B": 5.0})
    tr = pf.rebalance({"A": 0.0, "B": 0.5}, {"A": 10.0, "B": 5.0}, ["A", "B"], **KW)
    v1 = pf.value({"A": 10.0, "B": 5.0})
    assert [t.side for t in tr] == ["sell", "buy"]
    assert abs((v0 - v1) - sum(t.cost for t in tr)) < 1e-6   # alleen kosten gaan verloren


def test_band_rule():
    pf = Portfolio("X", 10_000)
    pf.rebalance({"A": 0.10}, {"A": 10.0}, ["A"], **KW)
    # 15% afwijking van het doel: binnen de band -> niets doen
    assert pf.rebalance({"A": 0.10 * 1.15}, {"A": 10.0}, ["A"], **KW) == []
    # 30% afwijking: wel bijsturen
    assert len(pf.rebalance({"A": 0.10 * 1.30}, {"A": 10.0}, ["A"], **KW)) == 1


def test_band_off_for_benchmarks():
    pf = Portfolio("X", 10_000)
    kw = dict(KW, use_band=False)
    pf.rebalance({"A": 0.10}, {"A": 10.0}, ["A"], **kw)
    assert len(pf.rebalance({"A": 0.11}, {"A": 10.0}, ["A"], **kw)) == 1


def test_full_exit_and_universe_removal():
    pf = Portfolio("X", 10_000)
    pf.rebalance({"A": 0.3, "B": 0.3}, {"A": 10.0, "B": 10.0}, ["A", "B"], **KW)
    tr = pf.rebalance(None, {"A": 10.0, "B": 10.0}, ["A"], **KW)   # B viel uit het universum
    assert [(t.symbol, t.side) for t in tr] == [("B", "sell")]
    assert "B" not in pf.qty


def test_none_targets_means_hold():
    pf = Portfolio("X", 10_000)
    pf.rebalance({"A": 0.5}, {"A": 10.0}, ["A"], **KW)
    assert pf.rebalance(None, {"A": 20.0}, ["A"], **KW) == []


def test_min_order_skipped():
    pf = Portfolio("X", 100)
    assert pf.rebalance({"A": 0.01}, {"A": 10.0}, ["A"], **KW) == []   # €1 < €5


def test_missing_price_no_trade():
    pf = Portfolio("X", 10_000)
    assert pf.rebalance({"A": 0.5}, {}, ["A"], **KW) == []


@pytest.mark.parametrize("seed", range(5))
def test_random_rebalances_keep_cash_nonnegative(seed):
    import numpy as np

    rng = np.random.default_rng(seed)
    pf = Portfolio("X", 10_000)
    syms = list("ABCDE")
    for _ in range(200):
        prices = {s: float(rng.uniform(1, 100)) for s in syms}
        w = rng.dirichlet(np.ones(6))[:5]
        pf.rebalance(dict(zip(syms, w)), prices, syms, **KW)
        assert pf.cash >= -1e-6
        assert sum(pf.weights(prices).values()) <= 1 + 1e-9
