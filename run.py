"""Opdrachtregel voor TBotai.

  python run.py live                 # dagelijkse paper-run (GitHub Actions doet dit elke dag)
  python run.py download             # dagcandles van alle EUR-markten naar data/candles/
  python run.py backtest             # backtest met basiskosten (0,30%) en stresskosten (0,60%)
  python run.py summary              # samenvatting van de live-test opnieuw schrijven
  python run.py live4h               # 4-uurs spoor (S6), elke 4 uur
  python run.py download4h           # 4-uurs candles BTC/ETH/SOL naar data/candles_4h/
  python run.py backtest4h           # backtest 4-uurs spoor (0,15% / 0,30% / 0,60% kosten)
"""
from __future__ import annotations

import argparse
import sys

from tbot.config import ROOT, load_config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TBotai paper-tradingbot")
    ap.add_argument("command", choices=["live", "download", "backtest", "summary", "live4h", "download4h", "backtest4h"])
    ap.add_argument("--start", default="2020-01-01", help="begindatum backtest")
    args = ap.parse_args(argv)
    cfg = load_config()

    if args.command == "live":
        from tbot.data import CcxtSource
        from tbot.live import run_live

        status = run_live(cfg, CcxtSource(cfg["exchange"], cfg["quote"]))
        print(f"status: {status}")
        return 0 if status in ("ok", "skip", "killed") else 1

    if args.command == "download":
        from tbot.backtest import download_all
        from tbot.data import CcxtSource

        n = download_all(CcxtSource(cfg["exchange"], cfg["quote"]), cfg, ROOT / "data" / "candles")
        print(f"{n} markten opgeslagen")
        return 0 if n else 1

    if args.command == "backtest":
        from tbot.backtest import load_all_candles, run_backtest, write_results

        candles = load_all_candles(ROOT / "data" / "candles")
        if not candles:
            print("Geen data. Draai eerst: python run.py download")
            return 1
        for label, cost in [("base", cfg["cost_per_side"]), ("stress", cfg["stress_cost_per_side"])]:
            res = run_backtest(candles, cfg, start=args.start, cost=cost)
            write_results(res, cfg, ROOT / "results", label)
            print(f"backtest {label} klaar -> results/backtest_{label}.md")
        return 0

    if args.command == "live4h":
        from tbot.data import CcxtSource
        from tbot.h4 import run_live_h4

        status = run_live_h4(cfg, CcxtSource(cfg["exchange"], cfg["quote"]))
        print(f"status: {status}")
        return 0 if status in ("ok", "skip", "killed") else 1

    if args.command == "download4h":
        import pandas as pd

        from tbot.data import CcxtSource, save_cached

        src = CcxtSource(cfg["exchange"], cfg["quote"])
        now = pd.Timestamp.now(tz="UTC").tz_localize(None).floor("4h")
        for sym in cfg["h4"]["symbols"]:
            df = src.fetch(sym, cfg["h4"]["timeframe"], since=pd.Timestamp("2020-01-01"))
            df = df[df.index < now]
            save_cached(ROOT / "data" / "candles_4h", sym, df)
            print(f"{sym}: {len(df)} candles vanaf {df.index[0] if len(df) else '-'}")
        return 0

    if args.command == "backtest4h":
        import pandas as pd

        from tbot.data import load_cached
        from tbot.h4 import run_backtest_h4, write_results_h4

        candles = {s: load_cached(ROOT / "data" / "candles_4h", s) for s in cfg["h4"]["symbols"]}
        for s_, v in candles.items():
            print(f"{s_}: {0 if v is None else len(v)} candles"
                  + (f" ({v.index[0]} t/m {v.index[-1]})" if v is not None and len(v) else ""))
        if any(v is None or v.empty for v in candles.values()):
            print("Geen (volledige) 4-uurs data. Draai eerst: python run.py download4h")
            return 1
        s5 = None
        p = ROOT / "results" / "equity_base.csv"
        if p.exists():
            e = pd.read_csv(p, index_col="date", parse_dates=["date"])
            s5 = e["S5"] if "S5" in e else None
        for c in cfg["h4"]["backtest_costs"]:
            label = f"{int(round(c * 10000))}bp"
            res = run_backtest_h4(candles, cfg, start="2021-01-01", cost=c)
            write_results_h4(res, cfg, ROOT / "results", label, s5)
            print(f"backtest 4u {label} klaar -> results/backtest_4h_{label}.md")
        return 0

    if args.command == "summary":
        from tbot.ledger import Ledger
        from tbot.live import _write_summary

        _write_summary(Ledger(ROOT / "state" / "ledger.db"), ROOT / "state")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
