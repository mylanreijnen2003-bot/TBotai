"""De MES-strategieën (zie HYPOTHESIS.md). Eén functie per strategie; alle gebruiken dezelfde fill-code (kern).

Geen vooruitkijken: elke strategie neemt zijn beslissing alleen op bars die al afgesloten zijn op het beslismoment.
- A: na 14:45 alleen 5-minuutbars die gesloten zijn, instap op de opening van de volgende bar.
- B, C, D, E, R: signaal op koersen t/m 15:30 (of 10:00) en eerdere dagen; instap op de opening van 15:30.
- G: alleen de eerste 5 minuten (09:30-09:34); instap op de opening van 09:35.
"""
import random
import statistics
from dataclasses import dataclass, field

from .kern import contracten, op_tick, open_vanaf, prijs_om, simuleer_trade, vijf_minuten, vwap_reeks


@dataclass
class Dag:
    datum: object
    contract: str
    bars: dict
    p1000: float = None
    p1530: float = None
    p1600: float = None
    vorig_slot: float = None       # prijs 16:00 van de vorige handelsdag, zelfde contract
    redenen: list = field(default_factory=list)

    @property
    def rod(self):
        return self.p1530 / self.vorig_slot - 1 if self.p1530 and self.vorig_slot else None

    @property
    def r1000(self):
        return self.p1000 / self.vorig_slot - 1 if self.p1000 and self.vorig_slot else None

    @property
    def beweging(self):
        return abs(self.p1600 - self.p1530) if self.p1600 is not None and self.p1530 is not None else None

    @property
    def geldig(self):
        return not self.redenen and self.rod is not None and self.beweging is not None


def prijzen(bars):
    """(p1000, p1530, p1600): de drie prijzen die de historie nodig heeft. Werkt ook met 5-minuutbars."""
    return prijs_om(bars, "10:00", "09:30"), prijs_om(bars, "15:30", "15:00"), prijs_om(bars, "16:00", "15:30")


def maak_dag(datum, contract, bars, vorig_slot, kal):
    p1000, p1530, p1600 = prijzen(bars)
    return Dag(datum, contract, bars, p1000, p1530, p1600, vorig_slot, kal.redenen_geen_trade(datum))


def willekeurige_richting(datum, strat):
    return 1 if random.Random("%s-%s" % (strat.get("willekeurig_seed", 20261003), datum.isoformat())).random() < 0.5 else -1


class Rekening:
    """Wat een strategie op één dag van zijn eigen virtuele account moet weten."""

    def __init__(self, afstand_tot_bodem=None, week_pnl=0.0):
        self.afstand = afstand_tot_bodem
        self.week_pnl = week_pnl
        self.dag_pnl = 0.0

    def afstand_nu(self):
        return None if self.afstand is None else self.afstand + self.dag_pnl


def _trade(dag, strat, rek, richting, instap_tijd, uitstap_tijd, stop_fn, doel_R=None, tot=None, max_stop=None):
    """Market-instap op de opening van instap_tijd (+1 tick). stop_fn(instap) -> stopprijs. -> (trade, reden)."""
    tick = strat["instrument"]["tick"]
    minuut, o = open_vanaf(dag.bars, instap_tijd, tot or instap_tijd)
    if o is None:
        return None, "geen_data"
    instap = o + richting * strat["slippage_ticks"] * tick
    stop = stop_fn(instap)
    afstand = abs(instap - stop)
    if afstand < strat["min_stop_punten"] - 1e-9:
        return None, "stop_te_klein"
    if max_stop is not None and afstand > max_stop + 1e-9:
        return None, "stop_te_groot"
    n, reden = contracten(afstand, strat, rek.afstand_nu())
    if n == 0:
        return None, reden
    doel = instap + richting * doel_R * afstand if doel_R else None
    t = simuleer_trade(dag.bars, richting, minuut, instap, stop, doel, uitstap_tijd, n, strat)
    if t is None:
        return None, "geen_data"
    rek.dag_pnl += t["netto"]
    return t, ""


# ---------------------------------------------------------------- A: laatste-uur trendvervolg
def strategie_a(dag, strat, rek):
    p = strat["A"]
    tick = strat["instrument"]["tick"]
    bars = {k: v for k, v in dag.bars.items() if "09:30" <= k <= "15:59"}
    if "09:30" not in bars or p["bias_bar"] not in vijf_minuten(bars):
        return [], "geen_data"
    vw = vwap_reeks(bars)
    b5 = vijf_minuten(bars)
    orb = [v for k, v in bars.items() if p["or_van"] <= k <= p["or_tot"]]
    or_hi, or_lo = max(x[1] for x in orb), min(x[2] for x in orb)

    def vwap_eind(k5):     # VWAP na het slot van de 5-minuutbar die om k5 begint
        ks = [k for k in vw if k5 <= k < _plus5(k5)]
        return vw[max(ks)] if ks else None

    bias_c = b5[p["bias_bar"]][3]
    bv = vwap_eind(p["bias_bar"])
    if bias_c > bv and bias_c > or_hi:
        r = 1
    elif bias_c < bv and bias_c < or_lo:
        r = -1
    else:
        return [], "geen_bias"
    trades, reden = [], "geen_trigger"
    verliezen = 0
    reeks = sorted(k for k in b5 if k >= p["bias_bar"])
    vorige = b5[reeks[0]]
    pullback = None          # extreem (laag bij long, hoog bij short) sinds de start van de pullback
    vrij_vanaf = "14:45"     # na een trade pas weer zoeken vanaf de bar na de uitstap
    for k5 in reeks[1:]:
        o, h, l, c, _ = b5[k5]
        if k5 < vrij_vanaf:
            vorige = b5[k5]
            continue
        if _plus5(k5) > p["instap_tot"]:
            break
        vwk = vwap_eind(k5)
        if pullback is None:
            if (c < vorige[3]) if r > 0 else (c > vorige[3]):
                pullback = l if r > 0 else h
        else:
            trigger = (c > o and c > vorige[1] and c > vwk) if r > 0 else (c < o and c < vorige[2] and c < vwk)
            if trigger:
                geldig = (pullback <= vwk + p["pullback_tolerantie_punten"]) if r > 0 else \
                         (pullback >= vwk - p["pullback_tolerantie_punten"])
                extreem, pullback = pullback, None
                instap_t = _plus5(k5)
                if not geldig:
                    reden = "pullback_te_ver_van_vwap"
                elif not (p["instap_van"] <= instap_t <= p["instap_tot"]):
                    reden = "instap_buiten_venster"
                else:
                    stop = extreem - r * tick
                    t, reden = _trade(dag, strat, rek, r, instap_t, p["uitstap"], lambda inst, s=stop: s,
                                      doel_R=p["doel_R"], tot=_plus5(instap_t), max_stop=p["max_stop_punten"])
                    if t:
                        trades.append(t)
                        verliezen += t["netto"] < 0
                        vrij_vanaf = _plus5(_vloer5(t["uitstap_minuut"]))
                        if (len(trades) >= p["max_trades_per_dag"] or verliezen >= p["dagstop_verliezen"]
                                or rek.dag_pnl <= -p["dagstop_usd"] or rek.dag_pnl >= p["winstplafond_usd"]):
                            break
            else:
                pullback = min(pullback, l) if r > 0 else max(pullback, h)
        vorige = b5[k5]
    return trades, ("" if trades else reden)


def _vloer5(k):
    h, m = k.split(":")
    return "%s:%02d" % (h, int(m) // 5 * 5)


def _plus5(k):
    h, m = (int(x) for x in k.split(":"))
    t = h * 60 + m + 5
    return "%02d:%02d" % (t // 60, t % 60)


# ---------------------------------------------------------------- B: benchmark uit het plan
def strategie_b(dag, strat, rek):
    p = strat["B"]
    o930 = dag.bars.get("09:30", (None,))[0]
    p1000 = prijs_om(dag.bars, "10:00", "09:30")
    if o930 is None or p1000 is None:
        return [], "geen_data"
    r = (p1000 > o930) - (p1000 < o930)
    if r == 0:
        return [], "geen_richting"
    t, reden = _trade(dag, strat, rek, r, p["instap"], p["uitstap"], lambda inst: inst - r * p["stop_punten"], tot="15:31")
    return ([t] if t else []), reden


# ---------------------------------------------------------------- C, D, E, R: laatste half uur
def strategie_laatste_halfuur(dag, hist, strat, rek, var):
    v = strat["varianten"][var]
    p = strat["laatste_halfuur"]
    tick = strat["instrument"]["tick"]
    nodig = max(p["stop_gem_dagen"], p["filter_dagen"] if v["filter"] else 0)
    if len(hist) < nodig:
        return [], "te_weinig_historie"
    signaal = dag.r1000 if v["signaal"] == "r1000" else dag.rod
    if signaal is None:
        return [], "geen_data"
    r = (signaal > 0) - (signaal < 0)
    if r == 0:
        return [], "geen_richting"
    if v["filter"]:
        mediaan = statistics.median(abs(h.rod) for h in hist[-p["filter_dagen"]:])
        if not abs(dag.rod) > mediaan:
            return [], "filter_zwak"
    if v["signaal"] == "willekeurig":
        r = willekeurige_richting(dag.datum, strat)
    stop_pt = op_tick(p["stop_factor"] * sum(h.beweging for h in hist[-p["stop_gem_dagen"]:]) / p["stop_gem_dagen"], tick)
    t, reden = _trade(dag, strat, rek, r, p["instap"], p["uitstap"], lambda inst: inst - r * stop_pt, tot="15:31")
    return ([t] if t else []), reden


# ---------------------------------------------------------------- G: opening range breakout
def strategie_g(dag, strat, rek):
    p = strat["G"]
    tick = strat["instrument"]["tick"]
    eerste = [dag.bars[k] for k in sorted(dag.bars) if "09:30" <= k <= "09:34"]
    if not eerste or "09:30" not in dag.bars:
        return [], "geen_data"
    o, c = eerste[0][0], eerste[-1][3]
    hi, lo = max(x[1] for x in eerste), min(x[2] for x in eerste)
    r = (c > o) - (c < o)
    if r == 0:
        return [], "geen_richting"
    stop = lo - tick if r > 0 else hi + tick
    t, reden = _trade(dag, strat, rek, r, p["instap"], p["uitstap"], lambda inst: stop, doel_R=p["doel_R"], tot="09:36")
    return ([t] if t else []), reden


def speel(var, dag, hist, strat, rek):
    """-> (trades, reden). Niet-handeldagen en de weekstop eerst."""
    if dag.redenen:
        return [], "+".join(dag.redenen)
    if rek.week_pnl <= -strat["weekstop_usd"]:
        return [], "weekstop"
    soort = strat["varianten"][var]["soort"]
    if soort == "trendvervolg":
        trades, reden = strategie_a(dag, strat, rek)
    elif soort == "benchmark_b":
        trades, reden = strategie_b(dag, strat, rek)
    elif soort == "orb":
        trades, reden = strategie_g(dag, strat, rek)
    else:
        trades, reden = strategie_laatste_halfuur(dag, hist, strat, rek, var)
    for t in trades:
        t["strategie"] = var
    return trades, reden
