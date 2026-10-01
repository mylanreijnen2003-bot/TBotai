import numpy as np
import pandas as pd

from tbot.backtest import run_backtest, write_results
from tbot.engine import new_portfolios, step
from tbot.features import Features
from tbot.report import metrics, paired_test


def test_backtest_runs_end_to_end(tmp_path, cfg, market):
    res = run_backtest(market, cfg, start="2021-01-01")
    eq = res["equity"]
    assert list(eq.columns) == ["S1", "S2", "S3", "S4", "B1", "B2"]
    assert len(eq) > 300
    assert (eq > 0).all().all()
    assert (res["exposure"] <= 1 + 1e-9).all().all()      # nooit hefboom
    key = write_results(res, cfg, tmp_path, "base")
    assert (tmp_path / "backtest_base.md").exists()
    assert "max_drawdown" in key["S1"]


def test_higher_costs_never_help(cfg, market):
    base = run_backtest(market, cfg, start="2021-01-01", cost=0.003)["equity"].iloc[-1]
    stress = run_backtest(market, cfg, start="2021-01-01", cost=0.006)["equity"].iloc[-1]
    for s in ["S1", "S2", "S3", "S4", "B2"]:
        assert stress[s] <= base[s] + 1e-6


def test_backtest_matches_live_step(cfg, market):
    """De backtest gebruikt dezelfde engine: een losse stap geeft hetzelfde resultaat."""
    f = Features({s: df["close"] for s, df in market.items()}, cfg)
    t = market["BTC/EUR"].index[600]
    fill = t + pd.Timedelta(days=1)
    prices = {s: float(df.loc[fill, "open"]) for s, df in market.items()}
    u = ["C01/EUR", "C02/EUR", "BTC/EUR"]
    a = step(t, fill, prices, u, f, new_portfolios(cfg), cfg, True, True)
    b = step(t, fill, prices, u, f, new_portfolios(cfg), cfg, True, True)
    assert {k: v.equity for k, v in a.items()} == {k: v.equity for k, v in b.items()}


def test_metrics_known_values():
    idx = pd.date_range("2020-01-01", periods=366)
    e = pd.Series(np.linspace(100, 200, 366), index=idx)
    m = metrics(e)
    assert abs(m["rendement_totaal"] - 1.0) < 1e-12
    assert abs(m["cagr"] - 1.0) < 1e-9
    assert m["max_drawdown"] == 0


def test_paired_test_detects_clear_difference():
    rng = np.random.default_rng(0)
    idx = pd.date_range("2020-01-01", periods=1000)
    rb = rng.normal(0, 0.01, 1000)
    ra = rb + 0.002
    a = pd.Series(np.cumprod(1 + ra), index=idx)
    b = pd.Series(np.cumprod(1 + rb), index=idx)
    p = paired_test(a, b, n_boot=500)
    assert p["p_mean"] < 0.01
    same = paired_test(b, b, n_boot=200)
    assert same["p_mean"] >= 0.4
