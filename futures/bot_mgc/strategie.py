"""Strategieën A-E en controle R (zie HYPOTHESIS.md): kenmerken per dag en de beslissing om 13:00 ET.

Alle varianten handelen hetzelfde venster (13:00-13:29 ET) met dezelfde stop, positiegrootte en kosten; alleen het
signaal verschilt:
- A: ROD (13:00 ÷ slot gisteren − 1), alleen als |ROD| > mediaan van 60 dagen.
- B: altijd long (benchmark).
- C: ROD zonder filter (directe replicatie van Baltussen e.a. 2021).
- D: ochtendsignaal ONFH (08:50 ÷ slot gisteren − 1), alleen als |ONFH| > mediaan van 60 dagen.
- E: alleen als ROD en ONFH dezelfde richting geven; geen filter.
- R: op de dagen waarop A handelt een willekeurige richting (vaste seed) als controle op de backtest zelf.

Deze code wordt door backtest, paper, sim en combine gebruikt. Hij kijkt nooit vooruit: de beslissing voor vandaag
gebruikt alleen prijzen van vandaag tot en met 13:00 ET en eerdere dagen.
"""
import math
import random
import statistics
from dataclasses import dataclass, field

from .tijd import op_tick

# Standaard; strategy.json ("varianten") is leidend voor naam/signaal/filter.
VARIANTEN = {
    "A": {"filter": True, "signaal": "rod", "naam": "A – laatste-halfuur momentum (ROD, filter)"},
    "B": {"filter": False, "signaal": "long", "naam": "B – altijd long (benchmark)"},
    "C": {"filter": False, "signaal": "rod", "naam": "C – ROD zonder filter (replicatie paper)"},
    "D": {"filter": True, "signaal": "onfh", "naam": "D – ochtendsignaal (overnacht + eerste halfuur, filter)"},
    "E": {"filter": False, "signaal": "beide", "naam": "E – eensgezind (ROD en ochtend zelfde richting)"},
    "R": {"filter": True, "signaal": "willekeurig", "naam": "R – willekeurige richting (controle)"},
}
ALLE_VARIANTEN = "ABCDER"


def variant_spec(variant, strat=None):
    v = dict(VARIANTEN[variant])
    if strat and variant in (strat.get("varianten") or {}):
        v.update(strat["varianten"][variant])
    return v


def variant_naam(variant, strat=None):
    return variant_spec(variant, strat)["naam"]


def willekeurige_richting(datum, strat):
    """Vaste muntworp per datum (seed uit strategy.json): elke run, backtest en paper, geeft dezelfde richting."""
    seed = strat.get("willekeurig_seed", 20261003)
    return 1 if random.Random("%s-%s" % (seed, datum.isoformat())).random() < 0.5 else -1

TE_WEINIG_HISTORIE = "te_weinig_historie"
FILTER_ZWAK = "filter_zwak"
GEEN_RICHTING = "geen_richting"
GEEN_DATA = "geen_data"
GEEN_OCHTEND = "geen_ochtenddata"
SIGNALEN_ONEENS = "signalen_oneens"
STOP_TE_KLEIN = "stop_te_klein"
STOP_TE_GROOT = "stop_te_groot"
GEHALVEERD_NUL = "gehalveerd_naar_0"
WEEKSTOP = "weekstop"
INSTAP_TE_LAAT = "instap_te_laat"


@dataclass
class Dag:
    datum: object
    contract: str = ""
    signaal: float = None      # slot van de 12:59-bar (= prijs 13:00)
    slot: float = None         # slot van de 13:29-bar (= prijs 13:30)
    rod: float = None
    ochtend: float = None      # slot van de 08:49-bar (= prijs 08:50)
    onfh: float = None         # ochtend ÷ slot vorige dag − 1 (overnacht + eerste halfuur)
    beweging: float = None     # |slot - signaal| in punten
    redenen: list = field(default_factory=list)
    fomc: bool = False
    geldig: bool = False
    bars: dict = None


def prijs_op(bars, t, vanaf):
    """Slot van de bar die om t begint; ontbreekt die (geen handel in die minuut), dan de laatste bar vanaf 'vanaf'."""
    if not bars:
        return None
    if t in bars:
        return bars[t][3]
    ks = [k for k in bars if vanaf <= k <= t]
    return bars[max(ks)][3] if ks else None


def signaalprijs(bars, strat):
    t = strat["tijden_et"]
    return prijs_op(bars, t["signaal_bar"], t["signaal_vanaf"])


def slotprijs(bars, strat):
    t = strat["tijden_et"]
    return prijs_op(bars, t["slot_bar"], t["slot_vanaf"])


def ochtendprijs(bars, strat):
    t = strat["tijden_et"]
    return prijs_op(bars, t.get("ochtend_bar", "08:49"), t.get("ochtend_vanaf", "08:20"))


def dag_uit_prijzen(datum, contract, sp, sl, vorig_slot, kal, strat, roll_dag=None, ochtend=None):
    d = Dag(datum=datum, contract=contract, signaal=sp, slot=sl, ochtend=ochtend)
    if sp is not None and vorig_slot:
        d.rod = sp / vorig_slot - 1.0
    if ochtend is not None and vorig_slot:
        d.onfh = ochtend / vorig_slot - 1.0
    if sp is not None and sl is not None:
        d.beweging = round(abs(sl - sp), 6)
    d.redenen = kal.redenen_geen_trade(datum, roll_dag=roll_dag)
    d.fomc = kal.is_fomc(datum)
    zet_geldig(d, strat)
    return d


def maak_dag(datum, contract, bars, kal, strat, vorig_slot=None, roll_dag=None):
    d = dag_uit_prijzen(datum, contract, signaalprijs(bars, strat), slotprijs(bars, strat), vorig_slot, kal, strat, roll_dag,
                        ochtend=ochtendprijs(bars, strat))
    d.bars = bars
    return d


def zet_geldig(d, strat):
    d.geldig = (d.signaal is not None and d.slot is not None and d.rod is not None
                and (not d.redenen if strat.get("geldige_dag_zonder_no_trade_dagen", True) else True))
    return d


def bouw_dagen(ruwe, kal, strat, roll_dagen=None):
    """ruwe = [(datum, contract, bars), ...] gesorteerd. De ROD gebruikt het slot van de vorige handelsdag
    volgens de kalender (op maandag de vrijdag), alleen als dat hetzelfde contract is."""
    per, out = {}, []
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
    actie: str
    reden: str = ""
    richting: int = 0
    signaal: float = None
    stop_afstand: float = None   # in punten
    rod: float = None
    onfh: float = None
    mediaan: float = None
    gem_beweging: float = None
    contracten: int = 0

    @property
    def is_trade(self):
        return self.actie == "trade"


def nodige_historie(strat, filter_dagen):
    return max(strat["filter_dagen"], filter_dagen or 0, strat["stop_gem_dagen"])


def _teken(x):
    return (x > 0) - (x < 0)


def beslis(vandaag, historie, strat, variant="A", filter_dagen=None, stop_factor=None):
    """Beslissing om 13:00 ET. historie = eerdere GELDIGE dagen (oudste eerst), zonder vandaag."""
    v = variant_spec(variant, strat)
    sig = v["signaal"]
    fd = strat["filter_dagen"] if filter_dagen is None else filter_dagen
    sf = strat["stop_factor"] if stop_factor is None else stop_factor
    b = Beslissing(datum=vandaag.datum, variant=variant, actie="geen", rod=vandaag.rod, onfh=vandaag.onfh,
                   signaal=vandaag.signaal)
    if vandaag.redenen:
        b.reden = "+".join(vandaag.redenen)
        return b
    if vandaag.signaal is None or vandaag.rod is None:
        b.reden = GEEN_DATA
        return b
    if sig in ("onfh", "beide") and vandaag.onfh is None:
        b.reden = GEEN_OCHTEND
        return b
    # het filter van D kijkt naar |ONFH|, alle andere filters naar |ROD|
    filter_waarde = (lambda dag: dag.onfh) if sig == "onfh" else (lambda dag: dag.rod)
    filter_hist = [h for h in historie if filter_waarde(h) is not None] if (v["filter"] and fd > 0) else historie
    if len(historie) < nodige_historie(strat, fd) or (v["filter"] and fd > 0 and len(filter_hist) < fd):
        b.reden = TE_WEINIG_HISTORIE
        return b
    if sig == "long":
        richting = 1
    elif sig == "onfh":
        richting = _teken(vandaag.onfh)
    elif sig == "beide":
        richting = _teken(vandaag.rod)
        if richting != _teken(vandaag.onfh):
            b.reden = SIGNALEN_ONEENS
            return b
    else:   # rod, en willekeurig (R handelt op precies dezelfde dagen als A: richting volgt pas na het filter)
        richting = _teken(vandaag.rod)
    if richting == 0:
        b.reden = GEEN_RICHTING
        return b
    if v["filter"] and fd > 0:
        b.mediaan = statistics.median(abs(filter_waarde(h)) for h in filter_hist[-fd:])
        if not abs(filter_waarde(vandaag)) > b.mediaan:
            b.reden = FILTER_ZWAK
            return b
    if sig == "willekeurig":
        richting = willekeurige_richting(vandaag.datum, strat)
    n = strat["stop_gem_dagen"]
    b.gem_beweging = sum(h.beweging for h in historie[-n:]) / float(n)
    b.stop_afstand = op_tick(sf * b.gem_beweging)
    b.richting = richting
    if b.stop_afstand < strat["min_stop_punten"] - 1e-9:
        b.reden = STOP_TE_KLEIN
        return b
    b.actie = "trade"
    return b


def contracten(stop_afstand, strat, afstand_tot_bodem=None):
    """(aantal, reden). floor($200 / (stop in punten × $10)), max 10; halveren als saldo − bodem < $600."""
    pv = strat["instrument"]["punt_waarde"]
    n = int(math.floor(strat["risico_per_trade"] / (stop_afstand * pv) + 1e-9))
    n = min(n, strat["max_contracten"])
    if n <= 0:
        return 0, STOP_TE_GROOT
    if afstand_tot_bodem is not None and afstand_tot_bodem < strat["halveren_binnen_usd_van_bodem"]:
        n //= 2
        if n <= 0:
            return 0, GEHALVEERD_NUL
    return n, ""
