"""Gesimuleerde fills op 1-minuutbars. Wordt door de backtest én de paper-modus gebruikt (zelfde code).

Aannames (conservatief, plan §8):
- Market-instap (13:00:05): opening van de 13:00-bar + 1 tick (in je nadeel). Ontbreekt die bar, dan de
  13:01-bar (fill vóór 13:02:00). Geen van beide: geen trade (instap_te_laat).
- Stop: geraakt als laag <= stop (long), vanaf de instapbar t/m de 13:28-bar. Fill op stop − 1 tick.
  Opent een bar al voorbij de stop (gat), dan fill op de opening − 1 tick (niet op de stopprijs).
  In de instapbar eerst de fill (op de opening), dan de stop.
- Tijdsuitstap 13:29:00: opening van de 13:29-bar − 1 tick.
- Stress: 2 ticks slippage per kant.
"""
from .tijd import TICK

WACHT = "wacht"
OPEN = "open"
GESLOTEN = "gesloten"
TE_LAAT = "instap_te_laat"


class TradeSim:
    def __init__(self, richting, stop_afstand, contracten, strat, stress=False):
        self.richting = richting
        self.stop_afstand = stop_afstand
        self.contracten = contracten
        self.strat = strat
        f = strat["stress" if stress else "fill"]
        self.slip = f["slippage_ticks"] * TICK
        self.instap_slip = f["market_instap_slippage_ticks"] * TICK
        t = strat["tijden_et"]
        self.eerste_bar = t["eerste_bar"]                 # 13:00
        self.laatste_instap_bar = t["laatste_instap_bar"]  # 13:01
        self.laatste_stop_bar = t["laatste_stop_bar"]     # 13:28
        self.status = WACHT
        self.instap = self.stop = self.uitstap = None
        self.instap_bar = self.uitstap_bar_tijd = self.uitstapreden = None
        self.slechtste = self.beste = None
        self.open_1329 = None

    def _sluit(self, minuut, prijs, reden):
        self.status = GESLOTEN
        self.uitstap = round(prijs, 6)
        self.uitstap_bar_tijd = minuut
        self.uitstapreden = reden

    def _extremen(self, h, l):
        if self.richting > 0:
            self.slechtste, self.beste = min(self.slechtste, l), max(self.beste, h)
        else:
            self.slechtste, self.beste = max(self.slechtste, h), min(self.beste, l)

    def _check_stop(self, minuut, h, l, o=None):
        if (l <= self.stop) if self.richting > 0 else (h >= self.stop):
            basis = self.stop
            if o is not None:   # gat over de stop heen: de opening is de eerste prijs die je kunt krijgen
                basis = min(o, self.stop) if self.richting > 0 else max(o, self.stop)
            p = basis - self.richting * self.slip
            self._extremen(p, p)
            self._sluit(minuut, p, "stop")
            return True
        return False

    def bar(self, minuut, o, h, l, c):
        """Verwerk één afgeronde 1-minuutbar (minuut = begintijd 'HH:MM' in ET)."""
        if self.status in (GESLOTEN, TE_LAAT) or minuut < self.eerste_bar:
            return self.status
        if self.status == WACHT:
            if minuut > self.laatste_instap_bar:
                self.status = TE_LAAT
                return self.status
            self.instap = round(o + self.richting * self.instap_slip, 6)
            self.instap_bar = minuut
            self.stop = round(self.instap - self.richting * self.stop_afstand, 6)
            self.slechtste = self.beste = self.instap
            self.status = OPEN
            if not self._check_stop(minuut, h, l):   # stop in de instapbar
                self._extremen(h, l)
            return self.status
        if minuut <= self.laatste_stop_bar:
            if not self._check_stop(minuut, h, l, o):
                self._extremen(h, l)
            return self.status
        self.open_1329 = o
        self._sluit(minuut, o - self.richting * self.slip, "tijd")
        return self.status

    def einde_instapvenster(self):
        """Om 13:02:00 ET nog geen fill: geen trade."""
        if self.status == WACHT:
            self.status = TE_LAAT
        return self.status

    def einde_data(self, laatste_close=None):
        if self.status == WACHT:
            self.status = TE_LAAT
        elif self.status == OPEN and laatste_close is not None:
            self._sluit("einde", laatste_close - self.richting * self.slip, "tijd_geen_bar")
        return self.status

    @property
    def gevuld(self):
        return self.instap is not None

    def resultaat(self, kosten_per_contract):
        if self.status != GESLOTEN:
            return None
        pv = self.strat["instrument"]["punt_waarde"]
        n = self.contracten
        bruto = (self.uitstap - self.instap) * self.richting * pv * n
        kosten = kosten_per_contract * n
        netto = bruto - kosten
        risico = self.stop_afstand * pv * n
        mae = min(0.0, (self.slechtste - self.instap) * self.richting * pv * n)
        mfe = max(0.0, (self.beste - self.instap) * self.richting * pv * n)
        return {"bruto": bruto, "kosten": kosten, "netto": netto, "risico": risico,
                "R": netto / risico if risico else None, "mae": min(mae, netto, 0.0), "mfe": mfe}


def simuleer_dag(bars, richting, stop_afstand, contracten, strat, stress=False):
    """Speelt de bars van 13:00 t/m 13:35 af. bars = {'HH:MM': (o,h,l,c)}."""
    sim = TradeSim(richting, stop_afstand, contracten, strat, stress)
    laatste = None
    for m in sorted(k for k in bars if "13:00" <= k <= "13:35"):
        o, h, l, c = bars[m]
        sim.bar(m, o, h, l, c)
        if m <= sim.laatste_stop_bar:
            laatste = c
        if sim.status in (GESLOTEN, TE_LAAT):
            break
    if sim.status == WACHT:
        sim.einde_instapvenster()
    if sim.status == OPEN:
        sim.einde_data(laatste)
    return sim
