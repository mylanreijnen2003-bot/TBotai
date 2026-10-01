"""Beoordeling van de vooraf vastgelegde doelen H7–H10 (HYPOTHESIS.md, aanvulling 1 okt 2026).

Schrijft results/hypotheses.md. Rekent niets nieuws uit aan de strategieën zelf:
alleen de criteria die vóór de backtest zijn vastgelegd.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import pandas as pd

from .report import fmt_num, fmt_pct, metrics

HOLDOUT = pd.Timestamp("2025-04-01")
EULER = 0.5772156649
N01 = NormalDist()

# naam: (max drawdown-grens als positief getal of "B1x2/3", omschrijving)
CRITERIA = {
    "S7": 0.30,
    "S8": 0.35,
    "S9": 0.35,
    "S10": "B1",  # max drawdown ≤ 2/3 van die van B1
}


def _cagr(e: pd.Series) -> float:
    e = e.dropna()
    if len(e) < 2:
        return float("nan")
    days = (e.index[-1] - e.index[0]).days or 1
    return (e.iloc[-1] / e.iloc[0]) ** (365 / days) - 1


def _dd(e: pd.Series) -> float:
    e = e.dropna()
    return float((e / e.cummax() - 1).min()) if len(e) else float("nan")


def deflated_sharpe(returns: pd.DataFrame, target: str, n_trials: int) -> float:
    """Deflated Sharpe Ratio (Bailey & López de Prado 2014), op dagrendementen.

    De spreiding V komt uit de Sharpe-ratio's van de strategieën in `returns`;
    het aantal proeven N komt uit de config (ook eerder afgevallen varianten).
    """
    r = returns.dropna(how="all")
    srs = r.mean() / r.std(ddof=1)
    v = float(srs.var(ddof=1)) if len(srs) > 1 else 0.0
    n = max(int(n_trials), 2)
    sr0 = math.sqrt(v) * ((1 - EULER) * N01.inv_cdf(1 - 1 / n) + EULER * N01.inv_cdf(1 - 1 / (n * math.e)))
    x = r[target].dropna()
    t = len(x)
    sr = float(x.mean() / x.std(ddof=1))
    skew = float(x.skew())
    kurt = float(x.kurt()) + 3.0
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr * sr
    if denom <= 0 or t < 3:
        return float("nan")
    return N01.cdf((sr - sr0) * math.sqrt(t - 1) / math.sqrt(denom))


def evaluate(base: dict, stress: dict, cfg: dict, s8_variants: dict[int, pd.Series] | None = None) -> tuple[str, dict]:
    eq, eqs = base["equity"], stress["equity"]
    rets = eq[[c for c in eq.columns if c.startswith("S")]].pct_change()
    hold = eq[eq.index >= HOLDOUT]
    b1_dd = _dd(eq["B1"])
    b1_hold = _cagr(hold["B1"])
    lines = [
        "# Beoordeling H7–H10 (vooraf vastgelegd op 1 okt 2026)",
        "",
        f"Backtest {eq.index[0].date()} t/m {eq.index[-1].date()}. Holdout vanaf {HOLDOUT.date()} "
        f"(let op: deze periode was al gezien bij S1–S6, dus geen schone test).",
        f"Aantal geteste varianten voor de deflated Sharpe: {cfg['n_trials']}.",
        "",
        "| Strategie | CAGR 0,30% | Max drawdown | CAGR 0,60% | Holdout CAGR | DSR | Oordeel |",
        "|---|---|---|---|---|---|---|",
    ]
    verdicts = {}
    for name, lim in CRITERIA.items():
        if name not in eq:
            continue
        cagr = _cagr(eq[name])
        if name == "S8" and s8_variants:
            cagr = sum(_cagr(s) for s in s8_variants.values()) / len(s8_variants)
        dd = _dd(eq[name])
        dd_lim = (2 / 3) * abs(b1_dd) if lim == "B1" else lim
        c_stress = _cagr(eqs[name])
        c_hold = _cagr(hold[name])
        dsr = deflated_sharpe(rets, name, cfg["n_trials"])
        checks = {
            "CAGR ≥ 20%": cagr >= 0.20,
            f"drawdown ≤ {dd_lim * 100:.0f}%": dd >= -dd_lim,
            "CAGR bij 0,60% ≥ 15%": c_stress >= 0.15,
            "holdout ≥ 0% en ≥ B1": c_hold >= 0 and c_hold >= b1_hold,
            "DSR ≥ 0,90": (not math.isnan(dsr)) and dsr >= 0.90,
        }
        ok = all(checks.values())
        failed = [k for k, v in checks.items() if not v]
        verdicts[name] = {"geslaagd": ok, "gezakt_op": failed}
        lines.append(
            f"| {name} | {fmt_pct(cagr)} | {fmt_pct(dd)} | {fmt_pct(c_stress)} | {fmt_pct(c_hold)} | "
            f"{fmt_num(dsr)} | {'**geslaagd**' if ok else 'gezakt: ' + ', '.join(failed)} |"
        )
    lines += ["", f"Ter vergelijking B1 (BTC vasthouden): CAGR {fmt_pct(_cagr(eq['B1']))}, "
                  f"max drawdown {fmt_pct(b1_dd)}, holdout {fmt_pct(b1_hold)}."]
    if s8_variants:
        lines += ["", "S8 per uitvoeringsdag (0 = maandag; CAGR-criterium gebruikt het gemiddelde):", ""]
        for d, s in sorted(s8_variants.items()):
            lines.append(f"- dag {d}: CAGR {fmt_pct(_cagr(s))}, max drawdown {fmt_pct(_dd(s))}")
    if "S9" in eq and "S4" in eq:
        corr = eq["S9"].pct_change().corr(eq["S4"].pct_change())
        lines += ["", f"Correlatie dagrendement S9 met S4: {fmt_num(corr)}."]
    for n in [c for c in ("S7", "S9") if c in eq]:
        m = metrics(eq[n], base["exposure"][n] if n in base["exposure"] else None, base["traded"].get(n))
        lines.append(f"{n}: gemiddeld {fmt_pct(m.get('gem_blootstelling'))} belegd, omzet {fmt_pct(m.get('omzet_per_jaar'))} per jaar.")
    return "\n".join(lines) + "\n", verdicts
