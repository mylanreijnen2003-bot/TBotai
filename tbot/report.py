"""Prestatiecijfers en de statistische toets uit HYPOTHESIS.md."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

DAYS = 365


def metrics(equity: pd.Series, exposure: pd.Series | None = None, traded: float | None = None) -> dict:
    """CAGR, Sharpe, max drawdown, Calmar, omzet en blootstelling voor één equity-reeks."""
    e = equity.dropna()
    if len(e) < 2:
        return {"dagen": len(e)}
    r = e.pct_change().dropna()
    days = (e.index[-1] - e.index[0]).days or 1
    cagr = (e.iloc[-1] / e.iloc[0]) ** (DAYS / days) - 1
    sd = r.std(ddof=1)
    sharpe = r.mean() / sd * math.sqrt(DAYS) if sd > 0 else float("nan")
    dd = (e / e.cummax() - 1).min()
    out = {
        "dagen": days,
        "eindwaarde": float(e.iloc[-1]),
        "rendement_totaal": float(e.iloc[-1] / e.iloc[0] - 1),
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "max_drawdown": float(dd),
        "calmar": float(cagr / abs(dd)) if dd < 0 else float("nan"),
    }
    if exposure is not None and len(exposure):
        out["gem_blootstelling"] = float(exposure.mean())
        out["pct_tijd_belegd"] = float((exposure > 0.01).mean())
    if traded is not None:
        out["omzet_per_jaar"] = float(traded / e.mean() * DAYS / days)
    return out


def _blocks(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    starts = rng.integers(0, n - block + 1, size=math.ceil(n / block))
    return np.concatenate([np.arange(s, s + block) for s in starts])[:n]


def paired_test(eq_a: pd.Series, eq_b: pd.Series, block: int = 20, n_boot: int = 5000, seed: int = 7) -> dict:
    """Gepaarde block-bootstrap op de dagelijkse verschilreeks (a - b).

    Houdt rekening met dikke staarten en met dagen die op elkaar lijken.
    p_mean: kans (onder 'geen verschil') op een gemiddeld dagverschil minstens zo groot als gemeten.
    p_sharpe: aandeel bootstrap-trekkingen waarin Sharpe(a) <= Sharpe(b).
    """
    df = pd.concat([eq_a.pct_change(), eq_b.pct_change()], axis=1, keys=["a", "b"]).dropna()
    n = len(df)
    if n < max(2 * block, 30):
        return {"n_dagen": n, "p_mean": float("nan"), "p_sharpe": float("nan"), "verschil_per_jaar": float("nan")}
    a, b = df["a"].to_numpy(), df["b"].to_numpy()
    d = a - b
    obs = d.mean()
    rng = np.random.default_rng(seed)
    centered = d - obs
    boot_mean = np.empty(n_boot)
    boot_sr = np.empty(n_boot)

    def sr(x):
        s = x.std(ddof=1)
        return x.mean() / s * math.sqrt(DAYS) if s > 0 else 0.0

    for i in range(n_boot):
        idx = _blocks(n, block, rng)
        boot_mean[i] = centered[idx].mean()
        boot_sr[i] = sr(a[idx]) - sr(b[idx])
    return {
        "n_dagen": n,
        "verschil_per_jaar": float(obs * DAYS),
        "p_mean": float((boot_mean >= obs).mean()),
        "sharpe_verschil": float(sr(a) - sr(b)),
        "p_sharpe": float((boot_sr <= 0).mean()),
    }


def fmt_pct(x) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:.1f}%"


def fmt_num(x) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}"


def summary_markdown(
    equity: pd.DataFrame, exposure: pd.DataFrame | None, traded: dict, title: str, start_capital: float | None = None
) -> str:
    """Tabel per portefeuille + de hypothesetoetsen H1-H3."""
    lines = [f"## {title}", ""]
    if equity.empty or len(equity) < 2:
        return "\n".join(lines + ["Nog te weinig data.", ""])
    lines += [
        f"Periode: {equity.index[0].date()} t/m {equity.index[-1].date()}",
        "",
        "| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |",
        "|---|---|---|---|---|---|---|---|",
    ]
    days = (equity.index[-1] - equity.index[0]).days
    if days < 90:
        # jaarcijfers (CAGR, Sharpe, omzet/jaar) zijn bij zo weinig dagen betekenisloos
        lines[-2:] = [
            "| Portefeuille | Eindwaarde | Rendement | Max drawdown | Belegd nu |",
            "|---|---|---|---|---|",
        ]
        for col in equity.columns:
            e = equity[col].dropna()
            base = start_capital or e.iloc[0]
            ex_now = exposure[col].dropna().iloc[-1] if exposure is not None and col in exposure else float("nan")
            lines.append(
                f"| {col} | €{e.iloc[-1]:,.0f} | {fmt_pct(e.iloc[-1] / base - 1)} | "
                f"{fmt_pct(float((e / e.cummax() - 1).min()))} | {fmt_pct(ex_now)} |"
            )
        lines += ["", f"Rendement is inclusief kosten, gemeten vanaf het startkapitaal. Jaarcijfers en hypothesetoetsen verschijnen na 90 dagen (nu {days})."]
        return "\n".join(lines + [""])
    m = {}
    for col in equity.columns:
        ex = exposure[col] if exposure is not None and col in exposure else None
        m[col] = metrics(equity[col], ex, traded.get(col))
        x = m[col]
        lines.append(
            f"| {col} | €{x.get('eindwaarde', float('nan')):,.0f} | {fmt_pct(x.get('cagr'))} | {fmt_num(x.get('sharpe'))} | "
            f"{fmt_pct(x.get('max_drawdown'))} | {fmt_num(x.get('calmar'))} | {fmt_pct(x.get('gem_blootstelling'))} | "
            f"{fmt_pct(x.get('omzet_per_jaar'))} |"
        )
    lines += ["", "**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):", ""]
    if "S1" in m and "B2" in m and "max_drawdown" in m["S1"]:
        h1_dd = m["S1"]["max_drawdown"] >= 0.5 * m["B2"]["max_drawdown"]
        h1_sr = m["S1"]["sharpe"] >= m["B2"]["sharpe"]
        lines.append(
            f"- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown {'ja' if h1_dd else 'nee'}, "
            f"Sharpe {'ja' if h1_sr else 'nee'}"
        )
    for name, bench, lim in [("S4", "B2", 0.70)]:
        if name in m and bench in m and "cagr" in m[name]:
            ok_r = m[name]["cagr"] >= m[bench]["cagr"]
            ok_dd = m[name]["max_drawdown"] >= lim * m[bench]["max_drawdown"]
            hn = "H4"
            lines.append(
                f"- {hn} ({name} CAGR ≥ {bench} én drawdown ≤ {int(lim * 100)}% van {bench}): "
                f"rendement {'ja' if ok_r else 'nee'}, drawdown {'ja' if ok_dd else 'nee'}"
            )
    for label, a, b in [
        ("H2 (S1 − S2)", "S1", "S2"),
        ("H3 (S1 − S3)", "S1", "S3"),
        ("S1 − B2", "S1", "B2"),
        ("S4 − B2", "S4", "B2"),
    ]:
        if a in equity and b in equity:
            p = paired_test(equity[a], equity[b])
            lines.append(
                f"- {label}: verschil {fmt_pct(p['verschil_per_jaar'])}/jaar, p = {fmt_num(p['p_mean'])}; "
                f"Sharpe-verschil {fmt_num(p.get('sharpe_verschil'))}, p = {fmt_num(p['p_sharpe'])} ({p['n_dagen']} dagen)"
            )
    return "\n".join(lines + [""])
