import pandas as pd

from tbot.strategies import STRATEGIES
from tbot.ledger import Ledger
from tbot.live import run_live

from conftest import FakeSource


def _run(tmp_path, cfg, source, day):
    source.today = pd.Timestamp(day)
    return run_live(
        cfg, source, state_dir=tmp_path / "state", today=pd.Timestamp(day),
        kill_file=tmp_path / "KILL", results_dir=tmp_path / "results", observe=False, log=lambda *a: None,
    )


def test_live_run_and_idempotent(tmp_path, cfg, market):
    src = FakeSource(market)
    day = market["BTC/EUR"].index[700]
    assert _run(tmp_path, cfg, src, day) == "ok"
    led = Ledger(tmp_path / "state" / "ledger.db")
    n_trades = led.db.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    assert n_trades > 0
    # dezelfde dag nog eens: niets doen, geen dubbele trades
    assert _run(tmp_path, cfg, src, day) == "skip"
    led = Ledger(tmp_path / "state" / "ledger.db")
    assert led.db.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == n_trades
    assert led.reconcile(cfg["start_capital_eur"]) == []
    assert (tmp_path / "state" / "summary.md").exists()


def test_live_multiple_days_reconcile(tmp_path, cfg, market):
    src = FakeSource(market)
    for i in range(700, 740):
        assert _run(tmp_path, cfg, src, market["BTC/EUR"].index[i]) == "ok"
    led = Ledger(tmp_path / "state" / "ledger.db")
    assert led.reconcile(cfg["start_capital_eur"]) == []
    eq = pd.read_sql_query("SELECT * FROM equity", led.db)
    assert set(eq["strategy"]) == set(STRATEGIES)
    assert len(eq) == 40 * len(STRATEGIES)
    # B1 = 100% BTC na de eerste dag
    b1 = pd.read_sql_query("SELECT * FROM positions WHERE strategy='B1'", led.db)
    assert list(b1["symbol"]) == ["BTC/EUR"]


def test_kill_file_stops_bot(tmp_path, cfg, market):
    (tmp_path / "KILL").write_text("stop")
    assert _run(tmp_path, cfg, FakeSource(market), market["BTC/EUR"].index[700]) == "killed"
    assert not (tmp_path / "state" / "ledger.db").exists()


def test_reconcile_detects_tampering(tmp_path, cfg, market):
    src = FakeSource(market)
    day = market["BTC/EUR"].index[700]
    assert _run(tmp_path, cfg, src, day) == "ok"
    led = Ledger(tmp_path / "state" / "ledger.db")
    led.db.execute("UPDATE cash SET cash = cash + 100 WHERE strategy='S2'")
    led.commit()
    assert _run(tmp_path, cfg, src, market["BTC/EUR"].index[701]) == "halted"


def test_version_mismatch_errors(tmp_path, cfg, market):
    src = FakeSource(market)
    assert _run(tmp_path, cfg, src, market["BTC/EUR"].index[700]) == "ok"
    cfg2 = dict(cfg, strategy_version="v2")
    assert _run(tmp_path, cfg2, src, market["BTC/EUR"].index[701]) == "error"


def test_new_strategy_added_later(tmp_path, cfg, market):
    """Een strategie die later wordt toegevoegd start met het startkapitaal; bestaande lopen ongewijzigd door."""
    import tbot.engine as engine
    import tbot.live as live
    import tbot.strategies as st

    src = FakeSource(market)
    old = ["S1", "S2", "S3", "B1", "B2"]
    orig = st.STRATEGIES[:]
    try:
        engine.STRATEGIES[:] = old
        live.STRATEGIES[:] = old
        assert _run(tmp_path, cfg, src, market["BTC/EUR"].index[700]) == "ok"
    finally:
        engine.STRATEGIES[:] = orig
        live.STRATEGIES[:] = orig
    led = Ledger(tmp_path / "state" / "ledger.db")
    s1_before = led.db.execute("SELECT cash FROM cash WHERE strategy='S1'").fetchone()[0]
    assert _run(tmp_path, cfg, src, market["BTC/EUR"].index[701]) == "ok"
    led = Ledger(tmp_path / "state" / "ledger.db")
    assert led.reconcile(cfg["start_capital_eur"]) == []
    eq = pd.read_sql_query("SELECT * FROM equity", led.db)
    assert set(eq["strategy"]) == set(STRATEGIES)
    assert len(eq[eq.strategy == "S4"]) == 1
    starts = led.get_meta("strategy_start")
    assert starts["S4"] != starts["S1"]
    assert s1_before is not None


def test_missed_days_are_reported(tmp_path, cfg, market):
    src = FakeSource(market)
    idx = market["BTC/EUR"].index
    assert _run(tmp_path, cfg, src, idx[700]) == "ok"
    assert _run(tmp_path, cfg, src, idx[704]) == "ok"           # drie dagen geen run
    led = Ledger(tmp_path / "state" / "ledger.db")
    msg = led.db.execute("SELECT message FROM runs ORDER BY bar_date DESC LIMIT 1").fetchone()[0]
    assert msg.startswith("gemist: ")
    assert len(msg.split(": ")[1].split(", ")) == 3
    assert "3 gemist" in (tmp_path / "state" / "summary.md").read_text()


def test_stale_price_is_reported_and_data_window_logged(tmp_path, cfg, market):
    idx = market["BTC/EUR"].index
    src = FakeSource(market)
    assert _run(tmp_path, cfg, src, idx[700]) == "ok"            # universum van deze maand vastgelegd
    day = idx[701]
    led = Ledger(tmp_path / "state" / "ledger.db")
    month = day.strftime("%Y-%m")
    sym = led.get_universe(month)[5]
    # de beurs levert voor deze munt de laatste dagen geen nieuwe candle
    market = dict(market)
    market[sym] = market[sym][market[sym].index < day - pd.Timedelta(days=3)]
    assert _run(tmp_path, cfg, FakeSource(market), day) == "ok"
    led = Ledger(tmp_path / "state" / "ledger.db")
    msg = led.db.execute("SELECT message FROM runs ORDER BY bar_date DESC LIMIT 1").fetchone()[0]
    assert "oude koers" in msg and sym in msg
    rows = led.db.execute(
        "SELECT symbol, first_bar, last_bar, exec_price FROM data_windows WHERE date=?", (day.date().isoformat(),)
    ).fetchall()
    assert rows and all(r[3] > 0 for r in rows)
    got = {r[0]: r for r in rows}
    assert got["BTC/EUR"][2] == (day - pd.Timedelta(days=1)).date().isoformat()
    assert got[sym][2] < (day - pd.Timedelta(days=1)).date().isoformat()
