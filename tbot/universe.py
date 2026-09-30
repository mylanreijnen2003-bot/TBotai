"""Maandelijkse keuze van het universum (welke munten meedoen).

Regels (HYPOTHESIS.md): elke 1e van de maand de top-15 EUR-paren op mediaan
dagvolume in EUR over 30 dagen, met minstens 365 dagen koershistorie en een
mediaan |dagrendement| van minstens 0,5% (sluit stablecoins uit), plus een
vaste uitsluitlijst.
"""
from __future__ import annotations

import pandas as pd


def base_of(symbol: str) -> str:
    return symbol.split("/")[0].upper()


def select_universe(candles: dict[str, pd.DataFrame], asof: pd.Timestamp, cfg: dict) -> list[str]:
    """Kies het universum met ALLEEN data t/m `asof` (laatste gesloten dag)."""
    ucfg = cfg["universe"]
    exclude = {b.upper() for b in ucfg["exclude_bases"]}
    n_vol = ucfg["volume_days"]
    scored = []
    for sym, df in candles.items():
        if base_of(sym) in exclude or df is None or df.empty:
            continue
        hist = df[df.index <= asof]
        if len(hist) < ucfg["min_history_days"]:
            continue
        if hist.index[-1] != asof:  # munt moet op de peildatum nog handelen
            continue
        last = hist.tail(n_vol)
        eur_vol = (last["volume"] * last["close"]).median()
        rets = hist["close"].pct_change().tail(n_vol).abs().median()
        if pd.isna(eur_vol) or pd.isna(rets) or rets < ucfg["min_median_abs_return"]:
            continue
        scored.append((float(eur_vol), sym))
    # hoogste volume eerst; bij gelijke stand alfabetisch (deterministisch)
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [s for _, s in scored[: ucfg["size"]]]


def is_universe_day(fill_date: pd.Timestamp) -> bool:
    """Het universum wisselt op de 1e van de maand (om 00:00 UTC)."""
    return fill_date.day == 1
