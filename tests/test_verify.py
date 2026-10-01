import pandas as pd

from tbot.ledger import Ledger
from tbot.live import run_live
from tbot.verify import replay, report_markdown, symbols_needed

from conftest import FakeSource


def _live_days(tmp_path, cfg, market, days):
    src = FakeSource(market)
    for day in days:
        src.today = day
        status = run_live(
            cfg, src, state_dir=tmp_path / "state", today=day, kill_file=tmp_path / "KILL",
            results_dir=tmp_path / "results", observe=False, log=lambda *a: None,
        )
        assert status == "ok"
    return Ledger(tmp_path / "state" / "ledger.db")


def test_replay_matches_live_exactly(tmp_path, cfg, market):
    idx = market["BTC/EUR"].index
    days = list(idx[700:745])                       # loopt over een maandwissel heen
    led = _live_days(tmp_path, cfg, market, days)
    res = replay(led, market, cfg)
    assert res["days"] == len(days)
    assert res["trades"] > 0
    assert res["diffs"] == [], res["diffs"][:5]
    assert "geen verschillen" in report_markdown(res, "test")


def test_replay_skips_missed_days(tmp_path, cfg, market):
    idx = market["BTC/EUR"].index
    days = [idx[700], idx[701], idx[705], idx[706]]  # dagen 702-704 geen run
    led = _live_days(tmp_path, cfg, market, days)
    res = replay(led, market, cfg)
    assert res["days"] == 4 and res["diffs"] == []


def test_replay_detects_changed_price(tmp_path, cfg, market):
    idx = market["BTC/EUR"].index
    led = _live_days(tmp_path, cfg, market, list(idx[700:710]))
    changed = dict(market)
    btc = changed["BTC/EUR"].copy()
    btc.loc[idx[705], "open"] *= 1.05                 # de beurs 'past' achteraf een koers aan
    changed["BTC/EUR"] = btc
    res = replay(led, changed, cfg)
    assert any("uitvoeringsprijs" in d and "BTC/EUR" in d for d in res["diffs"])
    assert "verschil" in report_markdown(res, "test")


def test_replay_detects_tampered_trade(tmp_path, cfg, market):
    idx = market["BTC/EUR"].index
    led = _live_days(tmp_path, cfg, market, list(idx[700:705]))
    led.db.execute("UPDATE trades SET notional = notional * 1.1 WHERE rowid = (SELECT MIN(rowid) FROM trades)")
    led.commit()
    assert replay(led, market, cfg)["diffs"]


def test_symbols_needed_includes_universe_and_btc(tmp_path, cfg, market):
    idx = market["BTC/EUR"].index
    led = _live_days(tmp_path, cfg, market, [idx[700]])
    syms = symbols_needed(led, cfg)
    assert "BTC/EUR" in syms and len(syms) >= 15


def test_replay_skips_days_without_data_and_readonly_keeps_file(tmp_path, cfg, market):
    import hashlib

    idx = market["BTC/EUR"].index
    _live_days(tmp_path, cfg, market, list(idx[700:703]))
    path = tmp_path / "state" / "ledger.db"
    before = hashlib.sha1(path.read_bytes()).hexdigest()
    led = Ledger(path, readonly=True)
    res = replay(led, {}, cfg)                       # geen koersdata
    assert res["days"] == 0 and len(res["skipped"]) == 3 and res["diffs"] == []
    assert "niets gecontroleerd" in report_markdown(res, "test")
    assert hashlib.sha1(path.read_bytes()).hexdigest() == before
