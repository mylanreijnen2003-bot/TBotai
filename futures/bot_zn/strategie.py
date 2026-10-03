"""Strategie A (laatste-halfuur momentum) en benchmarks B-D: kenmerken per dag en de beslissing om 14:30 ET.

Deze code wordt door backtest, paper en sim gebruikt. Hij kijkt nooit vooruit: de beslissing voor vandaag
gebruikt alleen de signaalprijs van vandaag (14:29-bar) en eerdere dagen.
"""
import math
import statistics
from dataclasses import dataclass, field

from .tijd import TICK, rond_af, ticks

VARIANTEN = {
    "A": {"filter": True, "richting": "rod", "instap": "limiet", "naam": "A – laatste-halfuur momentum"},
    "B": {"filter": False, "richting": "long", "instap": "limiet", "naam": "B – altijd long"},
    "C": {"filter": False, "richting": "rod", "instap": "limiet", "naam": "C – zonder filter"},
    "D": {"filter": True, "richting": "rod", "instap": "market", "naam": "D – market-instap 14:30:05"},
}

# redenen om niet te traden (naast de kalenderredenen uit kalender_zn)
TE_WEINIG_HISTORIE = "te_weinig_historie"
FILTER_ZWAK = "filter_zwak"
GEEN_RICHTING = "geen_richting"
GEEN_DATA = "geen_data"
STOP_TE_GROOT = "stop_te_groot"
GEHALVEERD_NUL = "gehalveerd_naar_0"
WEEKSTOP = "weekstop"


@dataclass
class Dag:
    """Kenmerken van één handelsdag."""
    datum: object
    contract: str = ""
    signaal: float = None      # slot van de 14:29-bar
    slot: float = None         # slot van de 14:59-bar (= prijs 15:00)
    rod: float = None          # signaal / slot vorige handelsdag - 1
    beweging: int = None       # |slot - signaal| in ticks
    redenen: list = field(default_factory=list)
    veiling: bool = False
    geldig: bool = False
    bars: dict = None          # 'HH:MM' -> (open, high, low, close)


def prijs_op(bars, t, vanaf):
    """Slot van de bar die om t begint; ontbreekt die (geen handel in die minuut), dan de laatste bar vanaf 'vanaf'."""
    if not bars:
        return None
    if t in bars:
        return bars[t][3]
    ks = [k for k in bars if vanaf <= k <= t]
    return bars[max(ks)][3] if ks else None


def signaalprijs(bars, strat):
    return prijs_op(bars, strat["tijden_et"]["signaal_bar"], "14:00")


def slotprijs(bars, strat):
    return prijs_op(bars, "14:59", "14:30")


def maak_dag(datum, contract, bars, kal, strat, vorig_slot=None, roll_dag=None):
    """Kenmerken van één dag. vorig_slot = slot van de vorige handelsdag op HETZELFDE contract (anders None)."""
    d = dag_uit_prijzen(datum, contract, signaalprijs(bars, strat), slotprijs(bars, strat), vorig_slot, kal, strat, roll_dag)
    d.bars = bars
    return d


def dag_uit_prijzen(datum, contract, sp, sl, vorig_slot, kal, strat, roll_dag=None):
    """Zelfde als maak_dag, maar met de prijzen al uitgerekend (live: uit de cache)."""
    d = Dag(datum=datum, contract=contract, signaal=sp, slot=sl)
    if sp is not None and vorig_slot:
        d.rod = sp / vorig_slot - 1.0
    if sp is not None and sl is not None:
        d.beweging = abs(ticks(sl - sp))
    d.redenen = kal.redenen_geen_trade(datum, roll_dag=roll_dag)
    d.veiling = kal.is_veilingdag(datum)
    zet_geldig(d, strat)
    return d


def zet_geldig(d, strat):
    d.geldig = (d.signaal is not None and d.slot is not None and d.rod is not None
                and (not d.redenen if strat.get("geldige_dag_zonder_no_trade_dagen", True) else True))
    return d


def bouw_dagen(ruwe, kal, strat, roll_dagen=None):
    """ruwe = [(datum, contract, bars), ...] gesorteerd. roll_dagen = set datums (backtest .v.0) of None (vaste regel).
    De ROD gebruikt het slot van de vorige handelsdag volgens de kalender, alleen als dat hetzelfde contract is."""
    per = {}
    out = []
    for datum, contract, bars in ruwe:
        prev = per.get(kal.vorige_handelsdag(datum))
        vorig_slot = prev.slot if prev is not None and prev.contract == contract else None
        rd = (datum in roll_dagen) if roll_dagen is not None else None
        d = maak_dag(datum, contract, bars, kal, strat, vorig_slot, rd)
        per[datum] = d
        out.append(d)
    return out


@dataclass
class Beslissing:
    datum: object
    variant: str
    actie: str                 # 'trade' of 'geen'
    reden: str = ""
    richting: int = 0          # +1 long, -1 short
    limiet: float = None
    stop_ticks: int = None
    rod: float = None
    mediaan: float = None
    gem_beweging: float = None
    contracten: int = 0

    @property
    def is_trade(self):
        return self.actie == "trade"


def nodige_historie(strat, filter_dagen):
    return max(strat["filter_dagen"], filter_dagen or 0, strat["stop_gem_dagen"])


def beslis(vandaag, historie, strat, variant="A", filter_dagen=None, stop_factor=None):
    """Beslissing om 14:30 ET. historie = eerdere GELDIGE dagen (oudste eerst), zonder vandaag."""
    v = VARIANTEN[variant]
    fd = strat["filter_dagen"] if filter_dagen is None else filter_dagen
    sf = strat["stop_factor"] if stop_factor is None else stop_factor
    b = Beslissing(datum=vandaag.datum, variant=variant, actie="geen", rod=vandaag.rod)
    if vandaag.redenen:
        b.reden = "+".join(vandaag.redenen)
        return b
    if vandaag.signaal is None or vandaag.rod is None:
        b.reden = GEEN_DATA
        return b
    if len(historie) < nodige_historie(strat, fd):
        b.reden = TE_WEINIG_HISTORIE
        return b
    if v["richting"] == "long":
        richting = 1
    else:
        richting = (vandaag.rod > 0) - (vandaag.rod < 0)
        if richting == 0:
            b.reden = GEEN_RICHTING
            return b
    if v["filter"] and fd > 0:
        b.mediaan = statistics.median(abs(h.rod) for h in historie[-fd:])
        if not abs(vandaag.rod) > b.mediaan:
            b.reden = FILTER_ZWAK
            return b
    n = strat["stop_gem_dagen"]
    b.gem_beweging = sum(h.beweging for h in historie[-n:]) / float(n)
    b.stop_ticks = max(strat["min_stop_ticks"], rond_af(sf * b.gem_beweging))
    b.richting = richting
    b.limiet = vandaag.signaal
    b.actie = "trade"
    return b


def contracten(stop_ticks, strat, afstand_tot_bodem=None):
    """(aantal, reden). floor(risico / (stop × $15,625)), max 3; halveren als saldo − bodem < $600."""
    tw = strat["instrument"]["tick_waarde"]
    n = int(math.floor(strat["risico_per_trade"] / (stop_ticks * tw) + 1e-9))
    n = min(n, strat["max_contracten"])
    if n <= 0:
        return 0, STOP_TE_GROOT
    if afstand_tot_bodem is not None and afstand_tot_bodem < strat["halveren_binnen_usd_van_bodem"]:
        n //= 2
        if n <= 0:
            return 0, GEHALVEERD_NUL
    return n, ""


def stop_prijs(instap, richting, stop_ticks, tick=TICK):
    return instap - richting * stop_ticks * tick
