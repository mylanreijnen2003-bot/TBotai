"""De vijf vooraf vastgelegde portefeuilles (zie HYPOTHESIS.md).

Elke functie geeft doelgewichten terug ({munt: aandeel van het vermogen}),
of None = "vandaag niets doen" (alleen munten buiten het universum verkopen).
Doelgewichten tellen nooit op tot meer dan 1 (geen hefboom).
"""
from __future__ import annotations

import math

import pandas as pd

from .features import Features

# Actieve portefeuilles. S7–S9 zijn op 1 okt 2026 afgevallen (H7–H9); hun regels blijven hieronder staan
# zodat de uitkomst herhaalbaar is, maar ze draaien niet meer mee.
STRATEGIES = ["S1", "S2", "S3", "S4", "S10", "M1", "M2", "B1", "B2"]


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


def s7_targets(t, universe, feats: Features, cfg) -> dict[str, float]:
    """S7 — S4 × BTC-regime: alleen belegd als BTC-EUR slot > SMA200 van BTC-EUR."""
    k = cfg["s7"]
    btc = k["regime_symbol"]
    c, m = feats.close(btc, t), feats.sma(btc, t, k["sma"])
    regime = 1.0 if (not math.isnan(m) and c > m) else 0.0
    return {s: regime * w for s, w in s4_targets(t, universe, feats, cfg).items()}


def s8_targets(t, fill_date, feats: Features, cfg) -> dict[str, float] | None:
    """S8 — BTC/ETH traag tijdreeks-momentum, wekelijks.

    Per munt: s1 = slot_t > slot_{t-28}, s2 = slot_t > slot_{t-84}, s3 = slot_t > SMA200_t.
    w = (1/aantal munten) × (s1+s2+s3)/3. Alleen op de vaste uitvoeringsdag (standaard maandag).
    """
    k = cfg["s8"]
    if pd.Timestamp(fill_date).weekday() != k["weekday"]:
        return None
    syms = k["symbols"]
    out = {}
    for sym in syms:
        c = feats.close(sym, t)
        sigs = []
        for n in k["lookbacks"]:
            then = feats.close(sym, t - pd.Timedelta(days=n))
            sigs.append(1.0 if (not math.isnan(then) and not math.isnan(c) and c > then) else 0.0)
        m = feats.sma(sym, t, k["sma"])
        sigs.append(1.0 if (not math.isnan(m) and c > m) else 0.0)
        out[sym] = (1.0 / len(syms)) * sum(sigs) / len(sigs)
    return out


def s9_targets(t, universe, feats: Features, cfg) -> dict[str, float]:
    """S9 — Keltner/Donchian-breakout met ratchet-stop; w = min(1,5/N; (1/N)/σ90) als de toestand aan staat."""
    n = len(universe)
    if n == 0:
        return {}
    k = cfg["s9"]
    tg = {}
    for s in universe:
        if not feats.keltner_on(s, t):
            tg[s] = 0.0
            continue
        sig = feats.sigma(s, t)
        if math.isnan(sig) or sig <= 0:
            tg[s] = 0.0
            continue
        tg[s] = min(k["max_weight_mult"] / n, (1.0 / n) / sig)
    tot = sum(tg.values())
    if tot > 1.0:
        tg = {s: w / tot for s, w in tg.items()}
    return tg


def s10_targets(t, feats: Features, cfg) -> dict[str, float]:
    """S10 — BTC-cyclus: w_BTC = aantal van [slot > SMA100, SMA200, SMA350] / 3."""
    k = cfg["s10"]
    sym = k["symbol"]
    c = feats.close(sym, t)
    on = 0
    for n in k["smas"]:
        m = feats.sma(sym, t, n)
        on += 1 if (not math.isnan(m) and c > m) else 0
    return {sym: on / len(k["smas"])}


def extra_symbols(cfg) -> set[str]:
    """Munten die buiten het universum nodig zijn (benchmarks, S7, S8, S10)."""
    return {cfg["benchmark_btc_symbol"], cfg["s7"]["regime_symbol"], cfg["s10"]["symbol"], *cfg["s8"]["symbols"]}


def b1_targets(first_day: bool, cfg) -> dict[str, float] | None:
    """B1 — 100% BTC, eenmalig kopen en vasthouden."""
    return {cfg["benchmark_btc_symbol"]: 1.0} if first_day else None


def b2_targets(first_day: bool, universe_day: bool, universe) -> dict[str, float] | None:
    """B2 — gelijk verdeeld universum; herbalanceren alleen bij de maandelijkse wissel."""
    if not (first_day or universe_day) or not universe:
        return None
    return {s: 1.0 / len(universe) for s in universe}


def s8_latest_targets(t, fill_date, feats: Features, cfg) -> dict[str, float]:
    """Doelgewichten van S8 zoals vastgesteld op de laatste uitvoeringsdag (maandag) op of vóór fill_date."""
    k = cfg["s8"]
    fill = pd.Timestamp(fill_date)
    back = (fill.weekday() - k["weekday"]) % 7
    last_fill = fill - pd.Timedelta(days=back)
    return s8_targets(last_fill - pd.Timedelta(days=1), last_fill, feats, cfg)


def mix_targets(name: str, t, fill_date, universe, feats: Features, cfg) -> dict[str, float]:
    """M1/M2 — gewogen gemiddelde van de doelgewichten van de deelstrategieën (config: mixes)."""
    out: dict[str, float] = {}
    for comp, w in cfg["mixes"][name].items():
        if comp == "S8":
            tg = s8_latest_targets(t, fill_date, feats, cfg)
        else:
            tg = targets_for(comp, t, fill_date, universe, feats, cfg, False, False)
        for sym, x in (tg or {}).items():
            out[sym] = out.get(sym, 0.0) + w * x
    return out


def targets_for(name: str, t, fill_date, universe, feats: Features, cfg, first_day: bool, universe_day: bool):
    if name in cfg.get("mixes", {}):
        return mix_targets(name, t, fill_date, universe, feats, cfg)
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
    if name == "S7":
        return s7_targets(t, universe, feats, cfg)
    if name == "S8":
        return s8_targets(t, fill_date, feats, cfg)
    if name == "S9":
        return s9_targets(t, universe, feats, cfg)
    if name == "S10":
        return s10_targets(t, feats, cfg)
    if name == "B1":
        return b1_targets(first_day, cfg)
    if name == "B2":
        return b2_targets(first_day, universe_day, universe)
    raise ValueError(name)


# Welke portefeuilles de band-regel gebruiken en munten buiten het universum verkopen
USES_BAND = {"S1": True, "S2": True, "S3": True, "S4": True, "S7": True, "S8": False, "S9": True, "S10": True,
             "M1": True, "M2": True, "B1": False, "B2": False}
FOLLOWS_UNIVERSE = {"S1": True, "S2": True, "S3": True, "S4": True, "S7": True, "S8": False, "S9": True,
                    "S10": False, "M1": False, "M2": False, "B1": False, "B2": True}
