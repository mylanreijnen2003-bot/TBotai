"""De vijf vooraf vastgelegde portefeuilles (zie HYPOTHESIS.md).

Elke functie geeft doelgewichten terug ({munt: aandeel van het vermogen}),
of None = "vandaag niets doen" (alleen munten buiten het universum verkopen).
Doelgewichten tellen nooit op tot meer dan 1 (geen hefboom).
"""
from __future__ import annotations

import math

import pandas as pd

from .features import Features

STRATEGIES = ["S1", "S2", "S3", "S4", "B1", "B2"]


def _vol_scale(feats: Features, sym: str, t, cfg) -> float:
    sig = feats.sigma(sym, t)
    if math.isnan(sig) or sig <= 0:
        return 0.0  # onvoldoende historie: niet beleggen
    return min(1.0, cfg["vol_target"] / sig)


def s1_targets(t, universe, feats: Features, cfg) -> dict[str, float]:
    """S1 — Donchian-trend-ensemble: w = (1/N) × (actieve signalen / 9) × min(1; 0,25/σ90)."""
    n = len(universe)
    if n == 0:
        return {}
    return {s: (1.0 / n) * feats.trend_fraction(s, t) * _vol_scale(feats, s, t, cfg) for s in universe}


def s2_targets(t, universe, feats: Features, cfg) -> dict[str, float]:
    """S2 — controle: w = (1/N) × min(1; 0,25/σ90), zonder trendsignaal."""
    n = len(universe)
    if n == 0:
        return {}
    return {s: (1.0 / n) * _vol_scale(feats, s, t, cfg) for s in universe}


def s3_targets(t, fill_date, universe, feats: Features, cfg) -> dict[str, float] | None:
    """S3 — wekelijkse marktschakelaar, alleen op maandag (fill-dag).

    M = gemiddelde over het universum van close_t / close_{t-28} - 1.
    M > 0 -> 1/N in elke munt, anders 100% cash.
    """
    if pd.Timestamp(fill_date).weekday() != 0:
        return None
    n = len(universe)
    if n == 0:
        return {}
    rets = [feats.ret(s, t, cfg["s3_lookback"]) for s in universe]
    rets = [r for r in rets if not math.isnan(r)]
    m = sum(rets) / len(rets) if rets else float("nan")
    if not rets or m <= 0:
        return {s: 0.0 for s in universe}
    return {s: 1.0 / n for s in universe}


def s4_targets(t, universe, feats: Features, cfg) -> dict[str, float]:
    """S4 — trend zonder volatiliteitsrem (gericht op rendement): w = (1/N) × (actieve signalen / 9)."""
    n = len(universe)
    if n == 0:
        return {}
    return {s: (1.0 / n) * feats.trend_fraction(s, t) for s in universe}


def b1_targets(first_day: bool, cfg) -> dict[str, float] | None:
    """B1 — 100% BTC, eenmalig kopen en vasthouden."""
    return {cfg["benchmark_btc_symbol"]: 1.0} if first_day else None


def b2_targets(first_day: bool, universe_day: bool, universe) -> dict[str, float] | None:
    """B2 — gelijk verdeeld universum; herbalanceren alleen bij de maandelijkse wissel."""
    if not (first_day or universe_day) or not universe:
        return None
    return {s: 1.0 / len(universe) for s in universe}


def targets_for(name: str, t, fill_date, universe, feats: Features, cfg, first_day: bool, universe_day: bool):
    if name == "S1":
        return s1_targets(t, universe, feats, cfg)
    if name == "S2":
        return s2_targets(t, universe, feats, cfg)
    if name == "S3":
        tg = s3_targets(t, fill_date, universe, feats, cfg)
        # eerste dag: S3 start in cash tot de eerste maandag
        return tg
    if name == "S4":
        return s4_targets(t, universe, feats, cfg)
    if name == "B1":
        return b1_targets(first_day, cfg)
    if name == "B2":
        return b2_targets(first_day, universe_day, universe)
    raise ValueError(name)


# Welke portefeuilles de band-regel gebruiken en munten buiten het universum verkopen
USES_BAND = {"S1": True, "S2": True, "S3": True, "S4": True, "B1": False, "B2": False}
FOLLOWS_UNIVERSE = {"S1": True, "S2": True, "S3": True, "S4": True, "B1": False, "B2": True}
