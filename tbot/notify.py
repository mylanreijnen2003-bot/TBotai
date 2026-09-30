"""Meldingen via Telegram (optioneel) en extra observaties die ALLEEN gelogd worden.

Fear & Greed en funding rates worden elke dag met tijdstempel opgeslagen,
zodat we later een eerlijke A/B-test kunnen doen. Ze sturen niets aan.
"""
from __future__ import annotations

import os

import requests


def telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text[:4000], "disable_web_page_preview": True},
            timeout=15,
        )
        return r.ok
    except Exception:
        return False


def fear_greed() -> tuple[float, str] | None:
    """alternative.me Crypto Fear & Greed Index (gratis, geen sleutel)."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=15)
        d = r.json()["data"][0]
        return float(d["value"]), d.get("value_classification", "")
    except Exception:
        return None


def btc_funding() -> tuple[float, str] | None:
    """BTC-funding rate van een perpetual-markt (best effort; alleen informatie)."""
    try:
        import ccxt

        for ex_id, sym in [("krakenfutures", "BTC/USD:USD"), ("okx", "BTC/USDT:USDT"), ("bybit", "BTC/USDT:USDT")]:
            try:
                ex = getattr(ccxt, ex_id)({"enableRateLimit": True, "timeout": 15000})
                fr = ex.fetch_funding_rate(sym)
                rate = fr.get("fundingRate")
                if rate is not None:
                    return float(rate), ex_id
            except Exception:
                continue
    except Exception:
        return None
    return None
