"""Gedeelde hulpjes voor de ZN-tests: instellingen, nep-dagen en een tijdelijke bot-map."""
import csv
import datetime as dt
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot_zn.instellingen import load_calendar, load_firm, load_strategy  # noqa: E402
from bot_zn.kalender_zn import Kalender, contract_code  # noqa: E402
from bot_zn.logboek import Logboek  # noqa: E402
from bot_zn.strategie import Dag  # noqa: E402
from bot_zn.tijd import ET, TICK  # noqa: E402

STRAT = load_strategy()
CAL = load_calendar()
KAL = Kalender(CAL, STRAT)
FIRM = load_firm("topstep_50k")


def historie(n=60, rod=0.0005, beweging=4, start=dt.date(2025, 1, 1)):
    """n geldige nep-dagen met vaste |ROD| en beweging (in ticks)."""
    out, d = [], start
    for i in range(n):
        out.append(Dag(datum=d + dt.timedelta(days=i), contract="X", signaal=110.0, slot=110.0,
                       rod=rod if i % 2 else -rod, beweging=beweging, geldig=True))
    return out


def bars_lijn(start="14:30", eind="14:59", prijs=110.0, breed=0):
    """Vlakke bars (open=high=low=close=prijs, eventueel +/- breed ticks)."""
    out = {}
    h, m = (int(x) for x in start.split(":"))
    t = dt.datetime(2000, 1, 1, h, m)
    while t.strftime("%H:%M") <= eind:
        out[t.strftime("%H:%M")] = (prijs, prijs + breed * TICK, prijs - breed * TICK, prijs)
        t += dt.timedelta(minutes=1)
    return out


class TijdelijkeMap:
    """Een lege bot-map (logs, data, reports) zodat tests nooit in de echte bot_zn schrijven."""

    def __enter__(self):
        self.pad = Path(tempfile.mkdtemp(prefix="znbot_"))
        for sub in ("logs", "data", "reports"):
            (self.pad / sub).mkdir()
        return self.pad

    def __exit__(self, *a):
        shutil.rmtree(self.pad, ignore_errors=True)


def logboek(map_, klok=None):
    return Logboek("test", map_ / "logs", echo=False, klok=klok)


def vul_cache(map_, vandaag, signaal=110.0, beweging_ticks=4, dagen=150):
    """Schrijft data/live_dagen.csv met nepprijzen voor alle handelsdagen vóór vandaag, op elk contract.
    Alle dagen hebben dezelfde |ROD| (beweging_ticks ten opzichte van de vorige dag) en dezelfde beweging."""
    rijen, slots = [], {}
    d = vandaag - dt.timedelta(days=dagen)
    i = 0
    while d < vandaag:
        if KAL.is_handelsdag(d):
            for jm in {KAL.contract_voor(d), KAL.contract_voor(vandaag), KAL.contract_voor(d - dt.timedelta(days=100))}:
                sp = signaal
                rijen.append([d.isoformat(), contract_code(*jm), sp, sp + beweging_ticks * TICK * (1 if i % 2 else -1)])
            slots[d] = sp + beweging_ticks * TICK * (1 if i % 2 else -1)
            i += 1
        d += dt.timedelta(days=1)
    with open(map_ / "data" / "live_dagen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["datum", "contract", "signaal", "slot"])
        w.writerows(rijen)
    return slots


def et_tijd(datum, hhmmss):
    h, m, s = (int(x) for x in hhmmss.split(":"))
    return dt.datetime(datum.year, datum.month, datum.day, h, m, s, tzinfo=ET)


def dag_bars(datum, signaal, pad):
    """Bars voor de nep-broker: 14:00-14:29 op 'signaal', daarna de prijzen uit pad {'HH:MM': (o,h,l,c)}."""
    out = {}
    for mm in range(0, 30):
        out[et_tijd(datum, "14:%02d:00" % mm)] = (signaal, signaal, signaal, signaal)
    for k, v in pad.items():
        h, m = k.split(":")
        out[et_tijd(datum, "%s:%s:00" % (h, m))] = v
    return out


def draai(runner, broker, datum, van="14:19:00", tot="15:06:00", stap=1, na_tick=None):
    """Laat de runner seconde voor seconde lopen."""
    t = et_tijd(datum, van)
    eind = et_tijd(datum, tot)
    while t <= eind and not runner.gestopt:
        broker.nu = t
        runner.tick(t)
        if na_tick:
            na_tick(t)
        t += dt.timedelta(seconds=stap)
