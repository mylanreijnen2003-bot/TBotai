"""Tijd en prijzen: New York-tijd (ET) is leidend, Amsterdamse tijd alleen voor weergave. Ticks van 0,1 punt."""
import datetime as dt
import math

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore

ET = ZoneInfo("America/New_York")
NL = ZoneInfo("Europe/Amsterdam")
UTC = dt.timezone.utc

TICK = 0.1  # 1 tick = 0,10 punt = $1,00 bij MGC


def et(datum, hhmm):
    """datum + 'HH:MM' of 'HH:MM:SS' -> datetime in ET."""
    parts = [int(x) for x in hhmm.split(":")]
    while len(parts) < 3:
        parts.append(0)
    return dt.datetime(datum.year, datum.month, datum.day, parts[0], parts[1], parts[2], tzinfo=ET)


def nl_tijd(datum, hhmm):
    """Amsterdamse kloktijd ('HH:MM') voor een ET-tijd op die datum."""
    return et(datum, hhmm).astimezone(NL).strftime("%H:%M")


def hms(t):
    return t.strftime("%H:%M:%S")


def rond_af(x):
    """Gewoon afronden (0,5 naar boven), niet de bankiersafronding van Python."""
    return int(math.floor(x + 0.5))


def op_tick(x, tick=TICK):
    """Afronden naar de dichtstbijzijnde tick."""
    return round(rond_af(x / tick) * tick, 6)


def prijs(p):
    return "–" if p is None else "%.1f" % p
