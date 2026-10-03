"""Gesimuleerde fills op 1-minuutbars. Wordt door de backtest én de paper-modus gebruikt (zelfde code).

Aannames (conservatief, plan §8):
- Limiet-instap: alleen gevuld als een bar van 14:30 t/m 14:34 de limiet met 1 tick doorbreekt
  (long: laag <= limiet − 1 tick). Fill op de limietprijs.
- Market-instap (benchmark D): opening van de 14:30-bar + 1 tick (in je nadeel).
- Stop: geraakt als laag <= stop (long), vanaf de fill-bar t/m de 14:58-bar. Fill op stop − 1 tick.
  In de fill-bar eerst de fill, dan de stop.
- Tijdsuitstap: opening van de 14:59-bar − 1 tick.
- Stress: doorbraak 2 ticks, 2 ticks slippage.
"""
from .tijd import TICK

WACHT = "wacht"
OPEN = "open"
GESLOTEN = "gesloten"
NIET_GEVULD = "niet_gevuld"


class TradeSim:
    def __init__(self, richting, limiet, stop_ticks, contracten, strat, instap="limiet", stress=False):
        self.richting = richting
        self.limiet = limiet
        self.stop_ticks = stop_ticks
        self.contracten = contracten
        self.instap_type = instap
        self.strat = strat
        f = strat["stress" if stress else "fill"]
        self.doorbraak = f["limiet_doorbraak_ticks"] * TICK
        self.slip = f["slippage_ticks"] * TICK
        self.market_slip = f["market_instap_slippage_ticks"] * TICK
        t = strat["tijden_et"]
        self.instap_eind_bar = t["instap_eind"][:5]          # 14:34
        self.laatste_stop_bar = t["laatste_stop_bar"]       # 14:58
        self.uitstap_bar = t["uitstap"][:5]                 # 14:59
        self.status = WACHT
        self.instap = None
        self.stop = None
        self.instap_bar = None
        self.uitstap = None
        self.uitstap_bar_tijd = None
        self.uitstapreden = None
        self.slechtste = None   # slechtste prijs tijdens de trade (voor MAE)
        self.beste = None       # beste prijs (voor MFE)
        self.open_1459 = None

    # ---------- intern ----------
    def _gevuld(self, minuut, prijs):
        self.status = OPEN
        self.instap = prijs
        self.instap_bar = minuut
        self.stop = prijs - self.richting * self.stop_ticks * TICK
        self.slechtste = self.beste = prijs

    def _sluit(self, minuut, prijs, reden):
        self.status = GESLOTEN
        self.uitstap = prijs
        self.uitstap_bar_tijd = minuut
        self.uitstapreden = reden

    def _update_extremen(self, h, l):
        if self.richting > 0:
            self.slechtste, self.beste = min(self.slechtste, l), max(self.beste, h)
        else:
            self.slechtste, self.beste = max(self.slechtste, h), min(self.beste, l)

    def _check_stop(self, minuut, h, l):
        geraakt = l <= self.stop if self.richting > 0 else h >= self.stop
        if geraakt:
            prijs = self.stop - self.richting * self.slip
            # na de stop is de positie weg: het slechtste punt is de stopfill, niet het laag van de bar
            self._update_extremen(prijs, prijs)
            self._sluit(minuut, prijs, "stop")
        return geraakt

    # ---------- publiek ----------
    def bar(self, minuut, o, h, l, c):
        """Verwerk één afgeronde 1-minuutbar (minuut = begintijd 'HH:MM' in ET)."""
        if self.status in (GESLOTEN, NIET_GEVULD) or minuut < "14:30":
            return self.status
        if self.status == WACHT:
            if minuut > self.instap_eind_bar:
                self.status = NIET_GEVULD
                return self.status
            if self.instap_type == "market":
                # market order om 14:30:05: opening van de eerste bar vanaf 14:30 + slippage
                self._gevuld(minuut, o + self.richting * self.market_slip)
            else:
                doorbroken = (l <= self.limiet - self.doorbraak) if self.richting > 0 else (h >= self.limiet + self.doorbraak)
                if not doorbroken:
                    return self.status
                self._gevuld(minuut, self.limiet)
            # in de fill-bar: eerst de fill, dan de stop
            if minuut <= self.laatste_stop_bar:
                if self._check_stop(minuut, h, l):
                    return self.status
                self._update_extremen(h, l)
            return self.status
        # status OPEN
        if minuut <= self.laatste_stop_bar:
            if not self._check_stop(minuut, h, l):
                self._update_extremen(h, l)
            return self.status
        # tijdsuitstap om 14:59:00: opening van de 14:59-bar (of de eerste bar daarna) − slippage
        self.open_1459 = o
        self._sluit(minuut, o - self.richting * self.slip, "tijd")
        return self.status

    def einde_instapvenster(self):
        """Om 14:35:00 ET: nog niet gevuld -> order geannuleerd, geen trade."""
        if self.status == WACHT:
            self.status = NIET_GEVULD
        return self.status

    def einde_data(self, laatste_close=None):
        """Geen bar meer na 14:58 (bijv. ontbrekende data): sluiten op de laatste koers − slippage."""
        if self.status == WACHT:
            self.status = NIET_GEVULD
        elif self.status == OPEN and laatste_close is not None:
            self._sluit("einde", laatste_close - self.richting * self.slip, "tijd_geen_bar")
        return self.status

    # ---------- resultaat ----------
    @property
    def gevuld(self):
        return self.instap is not None

    def pnl_ticks(self):
        return None if self.uitstap is None else round((self.uitstap - self.instap) * self.richting / TICK, 6)

    def resultaat(self, kosten_per_contract):
        """Netto P&L, risico, R, MAE/MFE in dollars."""
        if self.status != GESLOTEN:
            return None
        pv = self.strat["instrument"]["punt_waarde"]
        tw = self.strat["instrument"]["tick_waarde"]
        n = self.contracten
        bruto = (self.uitstap - self.instap) * self.richting * pv * n
        kosten = kosten_per_contract * n
        netto = bruto - kosten
        risico = self.stop_ticks * tw * n
        mae = min(0.0, (self.slechtste - self.instap) * self.richting * pv * n)
        mfe = max(0.0, (self.beste - self.instap) * self.richting * pv * n)
        return {"bruto": bruto, "kosten": kosten, "netto": netto, "risico": risico,
                "R": netto / risico if risico else None, "mae": min(mae, netto, 0.0), "mfe": mfe}


def simuleer_dag(bars, richting, limiet, stop_ticks, contracten, strat, instap="limiet", stress=False):
    """Speelt alle bars van 14:30 tot en met 15:05 af. bars = {'HH:MM': (o,h,l,c)}."""
    sim = TradeSim(richting, limiet, stop_ticks, contracten, strat, instap, stress)
    laatste = None
    for m in sorted(k for k in bars if "14:30" <= k <= "15:05"):
        o, h, l, c = bars[m]
        sim.bar(m, o, h, l, c)
        if m <= "14:58":
            laatste = c
        if sim.status in (GESLOTEN, NIET_GEVULD):
            break
    if sim.status == WACHT:
        sim.einde_instapvenster()
    if sim.status == OPEN:
        sim.einde_data(laatste)
    return sim
