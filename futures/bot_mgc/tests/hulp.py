"""Gedeelde hulpjes voor de MGC-tests: instellingen, nep-dagen en een tijdelijke bot-map."""
import csv
import datetime as dt
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot_mgc.instellingen import load_calendar, load_firm, load_personal, load_strategy  # noqa: E402
from bot_mgc.kalender_mgc import Kalender, contract_code  # noqa: E402
from bot_mgc.logboek import Logboek  # noqa: E402
from bot_mgc.strategie import Dag  # noqa: E402
from bot_mgc.tijd import ET, TICK  # noqa: E402

STRAT = load_strategy()
CAL = load_calendar()
KAL = Kalender(CAL, STRAT)
FIRM = load_firm("topstep_50k")
RULES = load_personal()


def historie(n=60, rod=0.0005, beweging=4.0, start=dt.date(2025, 1, 1)):
    """n geldige nep-dagen met vaste |ROD| en beweging (in punten)."""
    out, d = [], start
    for i in range(n):
        out.append(Dag(datum=d + dt.timedelta(days=i), contract="X", signaal=2000.0, slot=2000.0,
                       rod=rod if i % 2 else -rod, beweging=beweging, geldig=True))
    return out


def bars_lijn(start="13:00", eind="13:29", prijs=2000.0, breed=0):
    """Vlakke bars (open=high=low=close=prijs, eventueel +/- breed ticks)."""
    out = {}
    h, m = (int(x) for x in start.split(":"))
    t = dt.datetime(2000, 1, 1, h, m)
    while t.strftime("%H:%M") <= eind:
        out[t.strftime("%H:%M")] = (prijs, prijs + breed * TICK, prijs - breed * TICK, prijs)
        t += dt.timedelta(minutes=1)
    return out


class TijdelijkeMap:
    """Een lege bot-map (logs, data, reports) zodat tests nooit in de echte bot_mgc schrijven."""

    def __enter__(self):
        self.pad = Path(tempfile.mkdtemp(prefix="mgcbot_"))
        for sub in ("logs", "data", "reports"):
            (self.pad / sub).mkdir()
        return self.pad

    def __exit__(self, *a):
        shutil.rmtree(self.pad, ignore_errors=True)


def logboek(map_, klok=None):
    return Logboek("test", map_ / "logs", echo=False, klok=klok)


def vul_cache(map_, vandaag, signaal=2000.0, beweging_ticks=40, dagen=150, met_ochtend=False):
    """Schrijft data/live_dagen.csv met nepprijzen voor alle handelsdagen vóór vandaag, op elk contract.
    Alle dagen hebben dezelfde |ROD| en dezelfde beweging (beweging_ticks x 0,1 punt). met_ochtend: de ochtendprijs
    (08:50) is gelijk aan de signaalprijs, zodat ook D en E historie hebben."""
    rijen, slots = [], {}
    d = vandaag - dt.timedelta(days=dagen)
    i = 0
    while d < vandaag:
        if KAL.is_handelsdag(d):
            for jm in {KAL.contract_voor(d), KAL.contract_voor(vandaag), KAL.contract_voor(d - dt.timedelta(days=100))}:
                sp = signaal
                rijen.append([d.isoformat(), contract_code(*jm), sp, sp + beweging_ticks * TICK * (1 if i % 2 else -1),
                              sp if met_ochtend else ""])
            slots[d] = sp + beweging_ticks * TICK * (1 if i % 2 else -1)
            i += 1
        d += dt.timedelta(days=1)
    with open(map_ / "data" / "live_dagen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["datum", "contract", "signaal", "slot", "ochtend"])
        w.writerows(rijen)
    return slots


def et_tijd(datum, hhmmss):
    h, m, s = (int(x) for x in hhmmss.split(":"))
    return dt.datetime(datum.year, datum.month, datum.day, h, m, s, tzinfo=ET)


def dag_bars(datum, signaal, pad, ochtend=None):
    """Bars voor de nep-broker: 12:30-12:59 op 'signaal', daarna de prijzen uit pad {'HH:MM': (o,h,l,c)}.
    ochtend: ook 08:20-08:50 op die prijs (ochtendsignaal D/E)."""
    out = {}
    if ochtend is not None:
        for mm in range(20, 51):
            out[et_tijd(datum, "08:%02d:00" % mm)] = (ochtend,) * 4
    for mm in range(30, 60):
        out[et_tijd(datum, "12:%02d:00" % mm)] = (signaal, signaal, signaal, signaal)
    for k, v in pad.items():
        h, m = k.split(":")
        out[et_tijd(datum, "%s:%s:00" % (h, m))] = v
    return out


def draai(runner, broker, datum, van="12:49:00", tot="13:36:00", stap=1, na_tick=None):
    """Laat de runner seconde voor seconde lopen."""
    t = et_tijd(datum, van)
    eind = et_tijd(datum, tot)
    while t <= eind and not runner.gestopt:
        broker.nu = t
        runner.tick(t)
        if na_tick:
            na_tick(t)
        t += dt.timedelta(seconds=stap)
