"""Gratis koersen van Yahoo Finance voor de ZN-fronttest op GitHub. Doet zich voor als de broker-client
(contract_id + bars), zodat dagelijks.Fronttest ongewijzigd blijft. Geen account, geen sleutel.

- Contract: ZN + maandcode + jaar + .CBT (bijv. ZNZ26.CBT), zelfde rollregel als de bot. Lukt dat niet: ZN=F.
- Dagen tot 28 dagen terug: 1-minuutbars. Ouder (tot 58 dagen, alleen voor de historie van de strategieën):
  5-minuutbars. De prijzen die de strategieën uit de historie halen (08:50, 09:30, 14:30, 15:00) vallen op de grens
  van een 5-minuutbar; alleen het 09:59-punt van E ligt in de historie hooguit 1 minuut later.
- Gaat het ophalen mis, dan volgt een VerbindingsFout: er wordt dan niets opgeslagen en de volgende run probeert opnieuw.
"""
import datetime as dt
import time

from .broker import VerbindingsFout
from .kalender_zn import MAAND_CODES
from .tijd import ET, UTC

TERUGVAL = "ZN=F"
MAX_1M = 28
MAX_5M = 58
MAX_DAGEN_PER_VERZOEK = {"1m": 7, "5m": 55}     # Yahoo: 1m max 8 dagen per verzoek, 5m max 60


def ticker(jaar, maand, root="ZN"):
    return "%s%s%02d.CBT" % (root, MAAND_CODES[maand], jaar % 100)


class YahooBroker:
    def __init__(self, vandaag=None, pogingen=3, pauze=10, history=None):
        self.vandaag = vandaag or dt.datetime.now(UTC).astimezone(ET).date()
        self.pogingen = pogingen
        self.pauze = pauze
        self._history = history or self._yf_history
        self.terugval = {}
        self.verzoeken = 0

    def contract_id(self, jaar, maand, zoekterm=None, live=False, symbol_id=None):
        return ticker(jaar, maand)

    def _yf_history(self, sym, start, eind, interval):
        import yfinance as yf
        laatste = None
        for poging in range(self.pogingen):
            try:
                return yf.Ticker(sym).history(start=start, end=eind, interval=interval, prepost=True,
                                              auto_adjust=False, actions=False, raise_errors=True)
            except Exception as e:
                laatste = e
                if "delisted" in str(e).lower() or "no data" in str(e).lower():
                    return None      # echt geen data voor dit symbool/deze periode
                time.sleep(self.pauze * (poging + 1))
        raise VerbindingsFout("Yahoo %s %s: %s" % (sym, interval, laatste))

    def _haal(self, sym, van, tot, interval):
        """[(t_utc, o, h, l, c)] voor kalenderdagen van..tot."""
        self.verzoeken += 1
        df = self._history(sym, van.isoformat(), (tot + dt.timedelta(days=1)).isoformat(), interval)
        out = []
        if df is None or len(df) == 0:
            return out
        idx = df.index
        idx = idx.tz_localize("UTC") if idx.tz is None else idx
        for t, o, h, l, c in zip(idx.tz_convert("UTC"), df["Open"], df["High"], df["Low"], df["Close"]):
            if any(x != x for x in (o, h, l, c)):
                continue
            out.append((t.to_pydatetime(), float(o), float(h), float(l), float(c)))
        return out

    def bars(self, contract_id, start, eind, partieel=False, live=False, limiet=None):
        """Zelfde vorm als de broker: [{'t': datetime UTC, 'o','h','l','c','v'}] oud -> nieuw, [start, eind)."""
        van = start.astimezone(ET).date()
        tot = (eind - dt.timedelta(seconds=1)).astimezone(ET).date()
        grens_1m = self.vandaag - dt.timedelta(days=MAX_1M)
        grens_5m = self.vandaag - dt.timedelta(days=MAX_5M)
        stukken = []
        if tot >= grens_1m:
            stukken.append((max(van, grens_1m), tot, "1m"))
        if van < grens_1m and tot >= grens_5m:
            stukken.append((max(van, grens_5m), min(tot, grens_1m - dt.timedelta(days=1)), "5m"))
        rijen = []
        for a0, b0, iv in stukken:
            stap = MAX_DAGEN_PER_VERZOEK[iv]
            a = a0
            while a <= b0:                 # Yahoo geeft max 8 dagen 1-minuutdata per verzoek: in blokken ophalen
                b = min(b0, a + dt.timedelta(days=stap - 1))
                sym = self.terugval.get(contract_id, contract_id)
                r = self._haal(sym, a, b, iv)
                if not r and iv == "1m" and sym == contract_id and (b - a).days >= 2:
                    # specifiek contract onbekend bij Yahoo: terugvallen op het doorlopende contract
                    r = self._haal(TERUGVAL, a, b, iv)
                    if r:
                        self.terugval[contract_id] = TERUGVAL
                rijen.extend(r)
                a = b + dt.timedelta(days=1)
        s, e = start.astimezone(UTC), eind.astimezone(UTC)
        return [{"t": t, "o": o, "h": h, "l": l, "c": c, "v": 0} for t, o, h, l, c in sorted(rijen) if s <= t < e]
