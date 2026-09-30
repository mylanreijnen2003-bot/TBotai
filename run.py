"""Opdrachtregel voor TBotai.

  python run.py live                 # dagelijkse paper-run (GitHub Actions doet dit elke dag)
  python run.py download             # dagcandles van alle EUR-markten naar data/candles/
  python run.py backtest             # backtest met basiskosten (0,30%) en stresskosten (0,60%)
  python run.py summary              # samenvatting van de live-test opnieuw schrijven
"""
from __future__ import annotations

import argparse
import sys

from tbot.config import ROOT, load_config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TBotai paper-tradingbot")
    ap.add_argument("command", choices=["live", "download", "backtest", "summary"])
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

    if args.command == "summary":
        from tbot.ledger import Ledger
        from tbot.live import _write_summary

        _write_summary(Ledger(ROOT / "state" / "ledger.db"), ROOT / "state")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
