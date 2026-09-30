import pandas as pd

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
    assert set(eq["strategy"]) == {"S1", "S2", "S3", "B1", "B2"}
    assert len(eq) == 40 * 5
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
