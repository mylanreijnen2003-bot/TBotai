"""Live-bewaking (plan §9): vergelijking met de backtest en de automatische NO-GO.

- Elke 20 trades/signalen: bot_zn/reports/live_vs_backtest.html bijwerken.
- Na >= 60 trades: gemiddelde R < 0 én t-stat <= −1,0 -> status NO-GO in bot_zn/status.json.
  Daarna plaatst de bot geen orders meer en logt hij alleen nog in paper.
- Gemiddelde slippage meer dan 1 tick slechter dan de aanname -> melding.
"""
import datetime as dt
import json
from pathlib import Path

from .instellingen import BOT
from .rapport import schrijf_live_rapport
from .statistiek import t_stat

STATUS = BOT / "status.json"


def lees_status(pad=STATUS):
    p = Path(pad)
    if not p.exists():
        return {"status": "actief"}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {"status": "actief"}


def is_no_go(pad=STATUS):
    return lees_status(pad).get("status") == "NO-GO"


def zet_no_go(reden, pad=STATUS):
    Path(pad).write_text(json.dumps({"status": "NO-GO", "reden": reden, "sinds": dt.datetime.now().isoformat(timespec="seconds")},
                                    indent=2, ensure_ascii=False), encoding="utf-8")


def evalueer(rs, signalen, gevuld, slippages, strat):
    """rs = R per trade (live), signalen = aantal signalen, gevuld = aantal gevulde, slippages = ticks slechter dan aanname per trade."""
    lv = strat["live"]
    n = len(rs)
    exp = sum(rs) / n if n else None
    ts = t_stat(rs)
    res = {"trades": n, "signalen": signalen, "expectancy_R": exp, "t_stat": ts,
           "winrate": (sum(1 for r in rs if r > 0) / n) if n else None,
           "vulgraad": (gevuld / signalen) if signalen else None,
           "slippage": (sum(slippages) / len(slippages)) if slippages else None,
           "no_go": False, "meldingen": []}
    if n >= lv["bewaking_min_trades"] and exp is not None and exp < 0 and ts is not None and ts <= lv["bewaking_t_stat_grens"]:
        res["no_go"] = True
        res["meldingen"].append("AUTOMATISCHE STOP: na %d trades gemiddeld %+.3fR met t-stat %.2f (grens %.1f). Status NO-GO: "
                                "geen orders meer, alleen nog loggen in paper." % (n, exp, ts, lv["bewaking_t_stat_grens"]))
    if res["slippage"] is not None and res["slippage"] > lv["slippage_waarschuwing_ticks"]:
        res["meldingen"].append("Slippage gemiddeld %.2f ticks slechter dan de aanname (meer dan %d tick)."
                                % (res["slippage"], lv["slippage_waarschuwing_ticks"]))
    return res


def bijwerken(account, rs, signalen, gevuld, slippages, strat, logboek=None, forceer=False,
              status_pad=STATUS, rapport_pad=None, backtest_pad=None):
    """Roep aan na elke trade of elk signaal. Schrijft het rapport bij elke 20e trade/signaal (of forceer)."""
    res = evalueer(rs, signalen, gevuld, slippages, strat)
    n_elk = strat["live"]["bewaking_elke_n"]
    if res["no_go"] and not is_no_go(status_pad):
        zet_no_go(res["meldingen"][0], status_pad)
        if logboek:
            logboek.alarm(res["meldingen"][0])
        forceer = True
    elif logboek:
        for m in res["meldingen"]:
            logboek.waarschuwing(m)
    if forceer or (signalen and signalen % n_elk == 0) or (res["trades"] and res["trades"] % n_elk == 0):
        bt = {}
        bp = Path(backtest_pad or BOT / "reports" / "backtest_samenvatting.json")
        if bp.exists():
            bt = json.loads(bp.read_text(encoding="utf-8"))
            bt["slippage"] = 0.0
        live = dict(res, status="NO-GO" if is_no_go(status_pad) else "actief")
        schrijf_live_rapport(rapport_pad or BOT / "reports" / "live_vs_backtest.html", account, live, bt, res["meldingen"])
    return res
