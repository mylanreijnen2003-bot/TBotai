import pandas as pd

from tbot.h4 import H4Signals, h4_targets, round_trips, run_backtest_h4, run_live_h4, write_results_h4
from tbot.ledger import Ledger

from conftest import FakeSource


def _live(tmp_path, cfg, src, now):
    src.today = pd.Timestamp(now)
    return run_live_h4(cfg, src, state_dir=tmp_path / "s4h", now=pd.Timestamp(now), kill_file=tmp_path / "KILL",
                       log=lambda *a: None)


def test_s6_targets_hold_and_exit(market4h, cfg):
    sig = H4Signals({s: d["close"] for s, d in market4h.items()}, 20)
    syms = cfg["h4"]["symbols"]
    t = market4h["BTC/EUR"].index[500]
    tg = h4_targets("S6", t, sig, {}, syms, False)
    for s in syms:
        assert tg[s] == (1 / 3 if sig.on(s, t) else 0.0)
    held = {s: 0.4 for s in syms}
    tg2 = h4_targets("S6", t, sig, held, syms, False)
    for s in syms:
        assert tg2[s] == (0.4 if sig.on(s, t) else 0.0)   # in positie: niet bijsturen


def test_s6_no_lookahead(market4h, cfg):
    t = market4h["BTC/EUR"].index[1000]
    a = H4Signals({s: d["close"] for s, d in market4h.items()}, 20)
    changed = {s: d["close"].where(d.index <= t, d["close"] * 5) for s, d in market4h.items()}
    b = H4Signals(changed, 20)
    for s in market4h:
        assert a.on(s, t) == b.on(s, t)


def test_backtest_h4(tmp_path, cfg, market4h):
    res = run_backtest_h4(market4h, cfg, start="2023-01-01")
    eq = res["equity"]
    assert list(eq.columns) == ["S6", "HB1", "HB3"]
    assert (res["exposure"] <= 1 + 1e-9).all().all()
    rt = round_trips(res["trades"])
    assert len(rt) > 10
    write_results_h4(res, cfg, tmp_path, "30bp")
    assert (tmp_path / "backtest_4h_30bp.md").exists()
    hi = run_backtest_h4(market4h, cfg, start="2023-01-01", cost=0.006)["equity"].iloc[-1]
    assert hi["S6"] < eq["S6"].iloc[-1]


def test_live_h4_catchup_and_idempotent(tmp_path, cfg, market4h):
    src = FakeSource(market4h)
    idx = market4h["BTC/EUR"].index
    assert _live(tmp_path, cfg, src, idx[600] + pd.Timedelta(minutes=10)) == "ok"
    assert _live(tmp_path, cfg, src, idx[600] + pd.Timedelta(minutes=50)) == "skip"   # zelfde candle
    # 5 candles overgeslagen -> inhalen
    assert _live(tmp_path, cfg, src, idx[605] + pd.Timedelta(minutes=10)) == "ok"
    led = Ledger(tmp_path / "s4h" / "ledger.db")
    assert led.reconcile(cfg["start_capital_eur"]) == []
    eq = pd.read_sql_query("SELECT * FROM equity", led.db)
    assert len(eq[eq.strategy == "S6"]) == 6
    assert (tmp_path / "s4h" / "summary.md").exists()


def test_live_h4_matches_backtest(tmp_path, cfg, market4h):
    """Live, candle voor candle, geeft dezelfde equity als de backtest over dezelfde candles."""
    src = FakeSource(market4h)
    idx = market4h["BTC/EUR"].index
    for i in range(400, 460):
        assert _live(tmp_path, cfg, src, idx[i + 1] + pd.Timedelta(minutes=5)) == "ok"
    led = Ledger(tmp_path / "s4h" / "ledger.db")
    live = pd.read_sql_query("SELECT * FROM equity WHERE strategy='S6'", led.db)
    sub = {s: d[d.index <= idx[460]] for s, d in market4h.items()}
    bt = run_backtest_h4(sub, cfg, start=idx[400])["equity"]["S6"]
    assert abs(live["equity"].iloc[-1] - bt.iloc[-1]) < 1e-6
