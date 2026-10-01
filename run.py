"""Opdrachtregel voor TBotai.

  python run.py live                 # dagelijkse paper-run (GitHub Actions doet dit elke dag)
  python run.py download             # dagcandles van alle EUR-markten naar data/candles/
  python run.py backtest             # backtest met basiskosten (0,30%) en stresskosten (0,60%)
  python run.py summary              # samenvatting van de live-test opnieuw schrijven
  python run.py verify               # controle: live-run opnieuw uitrekenen en vergelijken (wekelijks)
"""
from __future__ import annotations

import argparse
import sys

from tbot.config import ROOT, load_config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TBotai paper-tradingbot")
    ap.add_argument("command", choices=["live", "download", "backtest", "summary", "verify"])
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
        import copy
        import json

        from tbot.evaluate import evaluate

        runs = {}
        for label, cost in [("base", cfg["cost_per_side"]), ("stress", cfg["stress_cost_per_side"])]:
            runs[label] = run_backtest(candles, cfg, start=args.start, cost=cost)
            write_results(runs[label], cfg, ROOT / "results", label)
            print(f"backtest {label} klaar -> results/backtest_{label}.md")
        # S8-robuustheid: dezelfde regels met elke weekdag als uitvoeringsdag
        variants = {cfg["s8"]["weekday"]: runs["base"]["equity"]["S8"]} if "S8" in runs["base"]["equity"] else {}
        for d in (range(7) if variants else []):
            if d in variants:
                continue
            c2 = copy.deepcopy(cfg)
            c2["s8"]["weekday"] = d
            variants[d] = run_backtest(candles, c2, start=args.start, only=["S8"])["equity"]["S8"]
            print(f"S8 weekdag {d} klaar")
        text, verdicts = evaluate(runs["base"], runs["stress"], cfg, variants)
        (ROOT / "results" / "hypotheses.md").write_text(text, encoding="utf-8")
        (ROOT / "results" / "hypotheses.json").write_text(json.dumps(verdicts, indent=2), encoding="utf-8")
        print(text)
        return 0

    if args.command == "verify":
        import pandas as pd

        from tbot import notify
        from tbot.data import CcxtSource
        from tbot.ledger import Ledger
        from tbot.verify import replay, report_markdown, symbols_needed

        ledger = Ledger(ROOT / "state" / "ledger.db", readonly=True)
        bars = ledger.ok_bars()
        if not bars:
            print("Nog geen live-dagen om te controleren.")
            return 0
        since = pd.Timestamp(bars[0]) - pd.Timedelta(days=int(cfg["live"]["history_days"]) + 5)
        src = CcxtSource(cfg["exchange"], cfg["quote"])
        candles = {}
        for sym in symbols_needed(ledger, cfg):
            try:
                candles[sym] = src.fetch_daily(sym, since=since)
            except Exception as e:
                print(f"  {sym}: niet opgehaald ({e.__class__.__name__})")
        res = replay(ledger, candles, cfg)
        now = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")
        out = ROOT / "results" / "verify_live.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report_markdown(res, now), encoding="utf-8")
        if res["diffs"]:
            print(f"{len(res['diffs'])} verschil(len) -> results/verify_live.md")
            notify.telegram(
                f"TBotai ⚠️ controle live vs. code: {len(res['diffs'])} verschil(len). "
                f"Eerste: {res['diffs'][0][:300]} — zie results/verify_live.md"
            )
            return 1
        if res["days"] == 0:
            print("Niets gecontroleerd: geen bruikbare koersdata.")
            return 1
        print(f"Geen verschillen ({res['days']} dagen, {res['trades']} trades).")
        return 0

    if args.command == "summary":
        from tbot.ledger import Ledger
        from tbot.live import _write_summary

        _write_summary(Ledger(ROOT / "state" / "ledger.db"), ROOT / "state")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
