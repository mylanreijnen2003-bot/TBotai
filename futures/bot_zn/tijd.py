"""Tijd en prijzen: New York-tijd (ET) is leidend, Amsterdamse tijd alleen voor weergave. Ticks en 32ste-notatie."""
import datetime as dt
import math

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore

ET = ZoneInfo("America/New_York")
NL = ZoneInfo("Europe/Amsterdam")
UTC = dt.timezone.utc

TICK = 0.015625  # 1/64 punt


def et(datum, hhmm):
    """datum + 'HH:MM' of 'HH:MM:SS' -> datetime in ET."""
    parts = [int(x) for x in hhmm.split(":")]
    while len(parts) < 3:
        parts.append(0)
    return dt.datetime(datum.year, datum.month, datum.day, parts[0], parts[1], parts[2], tzinfo=ET)


def nl_tijd(datum, hhmm):
    """Amsterdamse kloktijd ('HH:MM') voor een ET-tijd op die datum."""
    return et(datum, hhmm).astimezone(NL).strftime("%H:%M")


def nu_et():
    return dt.datetime.now(ET)


def hms(t):
    """datetime -> 'HH:MM:SS' (in de tijdzone van t)."""
    return t.strftime("%H:%M:%S")


def ticks(prijsverschil, tick=TICK):
    """Prijsverschil -> aantal ticks (afgerond op hele ticks)."""
    return int(math.floor(prijsverschil / tick + 0.5)) if prijsverschil >= 0 else -int(math.floor(-prijsverschil / tick + 0.5))


def rond_af(x):
    """Gewoon afronden (0,5 naar boven), niet de bankiersafronding van Python."""
    return int(math.floor(x + 0.5))


def in_32ste(prijs):
    """ZN-notatie: 110.515625 -> '110-16+' (16,5/32). Een '+' is een halve 32ste (= 1 tick van 1/64)."""
    if prijs is None:
        return "–"
    halve = rond_af(prijs * 64)  # aantal 64ste
    heel, rest = divmod(halve, 64)
    s = "%d-%02d" % (heel, rest // 2)
    return s + ("+" if rest % 2 else "")


def prijs_tekst(prijs):
    return "–" if prijs is None else "%.6f (%s)" % (prijs, in_32ste(prijs))
