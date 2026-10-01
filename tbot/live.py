"""Dagelijkse live paper-run.

Volgorde:
 1. KILL-bestand aanwezig?            -> niets doen
 2. Reconciliatie (cash/posities uit trades opnieuw opbouwen); verschil -> stoppen
 3. Dag al verwerkt?                   -> niets doen (idempotent)
 4. Universum kiezen op de 1e van de maand (of bij de allereerste run)
 5. Koersen ophalen, signaal op slot gisteren, uitvoering tegen open vandaag
 6. Alles vastleggen, samenvatting schrijven, optioneel Telegram
"""
from __future__ import annotations

import json
import traceback
from pathlib import Path

import pandas as pd

from . import notify
from .config import ROOT
from .data import closed_only
from .engine import new_portfolios, step
from .features import Features
from .ledger import Ledger
from .report import summary_markdown
from .strategies import STRATEGIES
from .universe import select_universe


def utc_today() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()


def run_live(
    cfg: dict,
    source,
    state_dir: str | Path = ROOT / "state",
    today: pd.Timestamp | None = None,
    kill_file: str | Path = ROOT / "KILL",
    results_dir: str | Path = ROOT / "results",
    observe: bool = True,
    log=print,
) -> str:
    """Voert één dag uit. Geeft een status terug: ok / skip / killed / halted / error."""
    state_dir = Path(state_dir)
    today = utc_today() if today is None else pd.Timestamp(today).normalize()
    t = today - pd.Timedelta(days=1)  # laatste gesloten dag
    now_iso = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    bar = t.date().isoformat()

    if Path(kill_file).exists():
        msg = "KILL-bestand gevonden: bot staat stil. Verwijder het bestand om verder te gaan."
        log(msg)
        notify.telegram(f"TBotai: {msg}")
        return "killed"

    ledger = Ledger(state_dir / "ledger.db")
    start_cap = float(cfg["start_capital_eur"])

    problems = ledger.reconcile(start_cap)
    if problems:
        msg = "Reconciliatie mislukt, bot stopt:\n" + "\n".join(problems[:10])
        log(msg)
        ledger.record_run(bar, now_iso, "halted", msg[:1000])
        ledger.commit()
        notify.telegram(f"TBotai ⚠️ {msg}")
        return "halted"

    if ledger.already_processed(bar):
        log(f"Dag {bar} is al verwerkt; niets te doen.")
        return "skip"

    try:
        pfs = ledger.load_portfolios()
        first_day = not pfs
        if first_day:
            pfs = new_portfolios(cfg)
            ledger.set_meta("start_date", today.date().isoformat())
            ledger.set_meta("strategy_version", cfg["strategy_version"])
        elif ledger.get_meta("strategy_version") != cfg["strategy_version"]:
            raise RuntimeError("strategy_version in config.yaml wijkt af van de lopende test. Start een nieuwe state-map.")

        # --- universum ---------------------------------------------------
        month = today.strftime("%Y-%m")
        universe = ledger.get_universe(month)
        uday = False
        if universe is None:
            # eerste run van de maand (normaal de 1e; bij een gemiste run de eerstvolgende dag)
            log("Universum kiezen: alle EUR-markten scannen ...")
            scan = {}
            for sym in source.list_markets():
                try:
                    scan[sym] = closed_only(source.fetch_daily(sym, days=cfg["universe"]["min_history_days"] + 40), today)
                except Exception as e:
                    log(f"  {sym}: overgeslagen ({e.__class__.__name__})")
            universe = select_universe(scan, t, cfg)
            if not universe:
                raise RuntimeError("Geen enkele munt voldoet aan de universum-eisen (data-probleem?)")
            ledger.set_universe(month, universe, bar)
            uday = True
        log(f"Universum ({len(universe)}): {', '.join(universe)}")

        # --- koersen -----------------------------------------------------
        needed = set(universe) | {cfg["benchmark_btc_symbol"]}
        for pf in pfs.values():
            needed |= set(pf.qty)
        closes, prices, stale = {}, {}, []
        for sym in sorted(needed):
            df = source.fetch_daily(sym, days=cfg["live"]["history_days"])
            done = closed_only(df, today)
            closes[sym] = done["close"]
            if len(done) == 0 or done.index[-1] != t:
                stale.append(sym)
            if today in df.index and df.loc[today, "open"] > 0:
                prices[sym] = float(df.loc[today, "open"])  # open van vandaag = uitvoeringsprijs
            elif len(done):
                prices[sym] = float(done["close"].iloc[-1])
        if stale:
            log(f"Let op: geen slotkoers van {bar} voor {', '.join(stale)}")

        feats = Features(closes, cfg)
        res = step(t, today, prices, universe, feats, pfs, cfg, first_day, uday)

        # --- vastleggen --------------------------------------------------
        date = today.date().isoformat()
        lines = [f"TBotai {date} (signaal {bar})"]
        for name in STRATEGIES:
            r = res[name]
            pf = pfs[name]
            ledger.add_trades(name, date, r.trades, cfg["strategy_version"])
            ledger.save_portfolio(pf)
            ledger.add_equity(name, date, r.equity, r.cash, r.exposure, r.n_positions)
            acted = {tr.symbol: f"{tr.side} ({tr.reason})" for tr in r.trades}
            if r.targets is not None:
                syms = sorted(set(r.targets) | set(r.weights_before))
                ledger.add_decisions(
                    name,
                    date,
                    [
                        (s, float(r.targets.get(s, 0.0)), float(r.weights_before.get(s, 0.0)), acted.get(s, "geen"))
                        for s in syms
                    ],
                )
            lines.append(
                f"{name}: €{r.equity:,.0f} | belegd {r.exposure * 100:.0f}% | {len(r.trades)} trades"
            )

        if observe and cfg["live"].get("fear_greed"):
            fg = notify.fear_greed()
            if fg:
                ledger.add_observation(date, "fear_greed", fg[0], fg[1], now_iso)
        if observe and cfg["live"].get("funding"):
            fr = notify.btc_funding()
            if fr:
                ledger.add_observation(date, "btc_funding", fr[0], fr[1], now_iso)

        # drawdown-alarm: 1,5x slechtste backtest-drawdown (alleen een melding)
        alarm = _drawdown_alarm(ledger, Path(results_dir))
        if alarm:
            lines.append(alarm)

        ledger.record_run(bar, now_iso, "ok", "")
        ledger.commit()

        # herhaalde controle na het wegschrijven
        post = ledger.reconcile(start_cap)
        if post:
            raise RuntimeError("Reconciliatie na run mislukt: " + "; ".join(post[:5]))

        ledger.export_csv(state_dir)
        _write_summary(ledger, state_dir)
        text = "\n".join(lines)
        log(text)
        notify.telegram(text)
        return "ok"
    except Exception as e:
        ledger.rollback()
        msg = f"{e.__class__.__name__}: {e}"
        log(traceback.format_exc())
        ledger.record_run(bar, now_iso, "error", msg[:1000])
        ledger.commit()
        notify.telegram(f"TBotai ⚠️ run mislukt: {msg}")
        return "error"


def _equity_frames(ledger: Ledger) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df = pd.read_sql_query("SELECT * FROM equity", ledger.db, parse_dates=["date"])
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
    eq = df.pivot(index="date", columns="strategy", values="equity").sort_index()
    ex = df.pivot(index="date", columns="strategy", values="exposure").sort_index()
    tr = pd.read_sql_query("SELECT strategy, SUM(notional) AS n FROM trades GROUP BY strategy", ledger.db)
    traded = dict(zip(tr["strategy"], tr["n"]))
    cols = [c for c in STRATEGIES if c in eq.columns]
    return eq[cols], ex[cols], traded


def _write_summary(ledger: Ledger, state_dir: Path) -> None:
    eq, ex, traded = _equity_frames(ledger)
    start = ledger.get_meta("start_date")
    head = [
        "# Live paper-test — stand van zaken",
        "",
        f"Start: {start}. Een paper-test van maanden controleert code en kosten; hij wijst géén winnaar aan.",
        "",
    ]
    from .config import load_config

    cap = float(load_config()["start_capital_eur"])
    body = summary_markdown(eq, ex, traded, "Resultaten sinds start", cap) if not eq.empty else "Nog geen data.\n"
    (state_dir / "summary.md").write_text("\n".join(head) + body, encoding="utf-8")


def _drawdown_alarm(ledger: Ledger, results_dir: Path) -> str | None:
    p = results_dir / "summary_base.json"
    if not p.exists():
        return None
    try:
        worst = json.loads(p.read_text())
    except Exception:
        return None
    eq, _, _ = _equity_frames(ledger)
    msgs = []
    for name in eq.columns:
        bt = worst.get(name, {}).get("max_drawdown")
        if bt is None or len(eq[name]) < 2:
            continue
        dd = float((eq[name] / eq[name].cummax() - 1).min())
        if dd < 1.5 * bt:
            msgs.append(f"{name} drawdown {dd * 100:.1f}% < 1,5× backtest ({bt * 100:.1f}%)")
    return ("⚠️ Herzie de code: " + "; ".join(msgs)) if msgs else None
