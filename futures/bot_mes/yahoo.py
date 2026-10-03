"""Gratis koersen van Yahoo Finance (via yfinance) voor de MES-bot: geen account, geen API-sleutel.

- Contract ES (grote S&P-future, dezelfde prijs als MES), bijv. ESZ26.CME, volgens de rollregel. Anders ES=F.
- 1-minuutbars met volume (nodig voor de VWAP van strategie A). Yahoo bewaart die 30 dagen, max 8 dagen per verzoek.
- Opwarmen van de historie met 5-minuutbars (60 dagen terug): de prijzen 10:00, 15:30 en 16:00 vallen op de grens.
"""
import datetime as dt
import time

from .kalender import MAAND_CODES
from .tijd import ET

TERUGVAL = "ES=F"


def ticker(jaar, maand, root="ES"):
    return "%s%s%02d.CME" % (root, MAAND_CODES[maand], jaar % 100)


def naar_dagen(df):
    """DataFrame (index = begintijd bar) -> {datum: {'HH:MM' (ET): (o, h, l, c, v)}}."""
    out = {}
    if df is None or len(df) == 0:
        return out
    idx = df.index
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    vol = df["Volume"] if "Volume" in df else [0] * len(df)
    for t, o, h, l, c, v in zip(idx.tz_convert(ET), df["Open"], df["High"], df["Low"], df["Close"], vol):
        if any(x != x for x in (o, h, l, c)):
            continue
        out.setdefault(t.date(), {})[t.strftime("%H:%M")] = (float(o), float(h), float(l), float(c),
                                                             0.0 if v != v else float(v))
    return out


class YahooBron:
    def __init__(self, pogingen=3, pauze=10, log=print):
        self.pogingen, self.pauze, self.log = pogingen, pauze, log

    def _history(self, sym, start, eind, interval):
        import yfinance as yf
        laatste = None
        for poging in range(self.pogingen):
            try:
                return yf.Ticker(sym).history(start=start, end=eind, interval=interval, prepost=True,
                                              auto_adjust=False, actions=False, raise_errors=True)
            except Exception as e:
                laatste = e
                time.sleep(self.pauze * (poging + 1))
        self.log("Yahoo %s %s %s-%s mislukt: %s" % (sym, interval, start, eind, laatste))
        return None

    def bars(self, sym, van, tot, interval="1m"):
        stap = 7 if interval == "1m" else 55
        out, d = {}, van
        while d <= tot:
            e = min(tot, d + dt.timedelta(days=stap - 1))
            for k, v in naar_dagen(self._history(sym, d.isoformat(), (e + dt.timedelta(days=1)).isoformat(), interval)).items():
                if van <= k <= tot:
                    out.setdefault(k, {}).update(v)
            d = e + dt.timedelta(days=1)
        return out
