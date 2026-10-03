"""Gratis koersdata van Yahoo Finance (via yfinance): geen account, geen API-sleutel.

- Per dag haalt de bot 1-minuutbars op van het goudcontract dat hij volgens de rollregel volgt (bijv. GCZ26.CMX,
  de grote goudfuture; dezelfde prijs als MGC). Yahoo bewaart 1-minuutdata 30 dagen, max 8 dagen per verzoek.
- Voor de opwarmperiode (de filters hebben 60 dagen historie nodig) gebruikt hij 5-minuutbars (60 dagen terug).
  De prijzen die de strategie gebruikt (08:50, 13:00 en 13:30 ET) vallen precies op de grens van een 5-minuutbar.
- Lukt het specifieke contract niet, dan valt hij terug op GC=F (doorlopend contract van Yahoo). Dat wordt in de
  data als ander contract genoteerd, zodat de bot nooit een signaal over een contractwissel heen berekent.
"""
import datetime as dt
import time

from .kalender_mgc import MAAND_CODES
from .tijd import ET

TERUGVAL = "GC=F"


def ticker(jaar, maand, root="GC"):
    return "%s%s%02d.CMX" % (root, MAAND_CODES[maand], jaar % 100)


def _naar_dagen(df):
    """DataFrame (index = begintijd bar) -> {datum: {'HH:MM' (ET): (o, h, l, c)}}."""
    out = {}
    if df is None or len(df) == 0:
        return out
    idx = df.index
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    idx = idx.tz_convert(ET)
    for t, o, h, l, c in zip(idx, df["Open"], df["High"], df["Low"], df["Close"]):
        if any(x != x for x in (o, h, l, c)):   # NaN
            continue
        out.setdefault(t.date(), {})[t.strftime("%H:%M")] = (round(float(o), 6), round(float(h), 6),
                                                             round(float(l), 6), round(float(c), 6))
    return out


class YahooBron:
    """Echte databron. Alle netwerkverkeer zit hier; de rest van de bot is zonder netwerk te testen."""

    def __init__(self, pogingen=3, pauze=10, log=print):
        self.pogingen = pogingen
        self.pauze = pauze
        self.log = log

    def _history(self, sym, start, eind, interval):
        import yfinance as yf   # pas hier importeren: tests hebben yfinance niet nodig
        laatste = None
        for poging in range(self.pogingen):
            try:
                df = yf.Ticker(sym).history(start=start, end=eind, interval=interval, prepost=True,
                                            auto_adjust=False, actions=False, raise_errors=True)
                return df
            except Exception as e:   # netwerk, rate limit, onbekend symbool
                laatste = e
                time.sleep(self.pauze * (poging + 1))
        self.log("Yahoo %s %s %s-%s mislukt: %s" % (sym, interval, start, eind, laatste))
        return None

    def bars(self, sym, van, tot, interval="1m"):
        """{datum: {'HH:MM': (o,h,l,c)}} voor kalenderdagen van..tot (inclusief). 1m in stukken van 7 dagen."""
        stap = 7 if interval == "1m" else 55
        out, d = {}, van
        while d <= tot:
            e = min(tot, d + dt.timedelta(days=stap - 1))
            df = self._history(sym, d.isoformat(), (e + dt.timedelta(days=1)).isoformat(), interval)
            for k, v in _naar_dagen(df).items():
                if van <= k <= tot:
                    out.setdefault(k, {}).update(v)
            d = e + dt.timedelta(days=1)
        return out
