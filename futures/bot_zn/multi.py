"""Meerdere strategieën naast elkaar: kenmerken per dag, de strategieën A t/m H, één fill-simulatie en één dagafspeler.

De dagelijkse fronttest (dagelijks.py) gebruikt speel_dag(): dezelfde beslis- en fill-code als een latere
backtest zou gebruiken. Een strategie krijgt van vandaag alleen de bars vóór zijn beslismoment te zien
(bars_tot), zodat hij structureel niet vooruit kan kijken.
"""
import datetime as dt
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from .instellingen import BOT
from .tijd import TICK, rond_af

TICK_WAARDE = 15.625
PUNT_WAARDE = 1000.0


def load_strategieen(pad=None):
    with open(pad or BOT / "strategieen.json", encoding="utf-8") as f:
        return json.load(f)


# ======================= prijzen en kenmerken =======================
def plus_min(hhmm, minuten):
    h, m = (int(x) for x in hhmm.split(":"))
    t = h * 60 + m + minuten
    return "%02d:%02d" % (t // 60, t % 60)


def p_om(bars, hhmm, vanaf):
    """Prijs op tijdstip hhmm = slot van de laatste bar die vóór hhmm begon (niet eerder dan 'vanaf')."""
    if not bars:
        return None
    ks = [k for k in bars if vanaf <= k < hhmm]
    return bars[max(ks)][3] if ks else None


def ticks_tussen(a, b):
    return abs(rond_af((a - b) / TICK)) if a is not None and b is not None else None


@dataclass
class MDag:
    datum: object
    contract: str
    bars: dict
    redenen: list = field(default_factory=list)
    veiling: str = ""
    release: str = ""
    vorige: object = None          # MDag van de vorige handelsdag (alleen als die in de data zit)
    p1500: float = None
    p1430: float = None
    r_lh: float = None             # rendement laatste half uur (14:30 -> 15:00)
    beweging_lh: int = None        # |15:00 - 14:30| in ticks
    rod: float = None
    r_pre10: float = None          # rendement 09:30 -> 09:59

    @property
    def vorig_slot(self):
        """Slot (15:00) van de vorige handelsdag op hetzelfde contract, anders None."""
        v = self.vorige
        return v.p1500 if v is not None and v.contract == self.contract else None


def maak_mdag(datum, contract, bars, kal, vorige=None, roll_dag=None, veiling="", release=""):
    d = MDag(datum=datum, contract=contract, bars=bars, veiling=veiling, release=release, vorige=vorige)
    d.redenen = kal.redenen_geen_trade(datum, roll_dag=roll_dag)
    d.p1430 = p_om(bars, "14:30", "14:00")
    d.p1500 = p_om(bars, "15:00", "14:30")
    if d.p1430 and d.p1500:
        d.r_lh = d.p1500 / d.p1430 - 1
        d.beweging_lh = ticks_tussen(d.p1500, d.p1430)
    if d.p1430 and d.vorig_slot:
        d.rod = d.p1430 / d.vorig_slot - 1
    p930, p959 = p_om(bars, "09:30", "09:00"), p_om(bars, "09:59", "09:30")
    if p930 and p959:
        d.r_pre10 = p959 / p930 - 1
    return d


def bouw_mdagen(ruwe, kal, roll_dagen=None, veilingen=None, releases=None):
    """ruwe = [(datum, contract, bars)] gesorteerd -> [MDag]. vorige = vorige handelsdag volgens de kalender."""
    per, out = {}, []
    for datum, contract, bars in ruwe:
        vorige = per.get(kal.vorige_handelsdag(datum))
        rd = (datum in roll_dagen) if roll_dagen is not None else None
        d = maak_mdag(datum, contract, bars, kal, vorige, rd, (veilingen or {}).get(datum, ""), (releases or {}).get(datum, ""))
        per[datum] = d
        out.append(d)
    return out


def kwantiel(waarden, pct):
    s = sorted(waarden)
    if not s:
        return None
    if pct == 50:
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0
    pos = (len(s) - 1) * pct / 100.0
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


# ======================= signalen =======================
@dataclass
class Signaal:
    richting: int                 # +1 long, -1 short, 0 = nog onbekend (breakout)
    soort: str                    # 'limiet' | 'market' | 'breakout'
    van: str                      # eerste bar waarin gevuld mag worden
    tot: str                      # laatste bar waarin gevuld mag worden
    uit: str                      # tijdsuitstap op de opening van deze bar
    stop_ticks: int
    prijs: float = None           # limietprijs
    hoog: float = None            # breakout
    laag: float = None
    info: dict = field(default_factory=dict)


class Geen(Exception):
    """Geen trade; de tekst is de reden."""


class Strategie:
    """Basis: houdt zijn eigen historie bij (alleen eerdere dagen) en geeft per dag een Signaal of een reden."""
    min_historie = 0

    def __init__(self, sid, defin, params, alg, kal=None):
        self.id = sid
        self.naam = defin["naam"]
        self.params = params
        self.alg = alg
        self.kal = kal
        self.blokkades = set(alg["basis_blokkades"]) | set(defin.get("extra_blokkades", []))
        self.hist = []

    def beslis_tijd(self):
        raise NotImplementedError

    def geblokkeerd(self, dag):
        r = [x for x in dag.redenen if x in self.blokkades]
        return "+".join(r)

    def na_dag(self, dag):
        """Na afloop van een dag: de volledige dag mag nu in de historie."""
        self.hist.append(dag)

    def signaal(self, dag, bars_tot):
        raise NotImplementedError


class LaatsteHalfuur(Strategie):
    """A, B1, B2: rest-of-day-rendement tot signaal_tijd voorspelt de rest tot 15:00."""

    def beslis_tijd(self):
        return self.params["signaal_tijd"]

    def _kenmerken(self, d):
        t = self.params["signaal_tijd"]
        p_sig = p_om(d.bars, t, "14:00")
        vs = d.vorig_slot
        if p_sig is None or not vs or d.p1500 is None:
            return None
        return (abs(p_sig / vs - 1), ticks_tussen(d.p1500, p_sig))

    def na_dag(self, dag):
        if dag.redenen:
            return   # geldige dagen = zonder enige niet-handeldag (precies zoals strategie A)
        k = self._kenmerken(dag)
        if k is not None:
            self.hist.append(k)

    def signaal(self, dag, bars_tot):
        p = self.params
        t = p["signaal_tijd"]
        sig = p_om(bars_tot, t, "14:00")
        vs = dag.vorig_slot
        if sig is None or not vs:
            raise Geen("geen_data")
        rod = sig / vs - 1
        if len(self.hist) < 60:
            raise Geen("te_weinig_historie")
        richting = (rod > 0) - (rod < 0)
        if richting == 0:
            raise Geen("geen_richting")
        drempel = kwantiel([h[0] for h in self.hist[-60:]], p["drempel_pct"])
        if not abs(rod) > drempel:
            raise Geen("filter_zwak")
        if p.get("teken_filter"):
            ochtend = p_om(bars_tot, p["teken_filter"], "08:00")
            if ochtend is None:
                raise Geen("geen_data")
            if (ochtend / vs - 1) * rod <= 0:
                raise Geen("teken_ongelijk")
        gem = sum(h[1] for h in self.hist[-20:]) / 20.0
        stop = max(self.alg["min_stop_ticks"], rond_af(p["stop_factor"] * gem))
        return Signaal(richting, "limiet", t, plus_min(t, p["venster_min"] - 1), "14:59", stop, prijs=sig,
                       info={"rod": rod, "drempel": drempel})


class Maandeinde(Strategie):
    """C: long op de laatste N handelsdagen van de maand (index-extensie)."""

    def beslis_tijd(self):
        return self.params["instap"]

    def _laatste_n(self, datum):
        """Aantal handelsdagen dat na 'datum' nog in dezelfde maand valt (max 5)."""
        d, n = datum, 0
        while True:
            d += dt.timedelta(days=1)
            if self.kal.is_handelsdag(d):
                if d.month != datum.month:
                    return n
                n += 1
                if n >= 5:
                    return n

    def signaal(self, dag, bars_tot):
        p = self.params
        if self._laatste_n(dag.datum) >= p["laatste_dagen"]:
            raise Geen("geen_maandeinde")
        return Signaal(1, "market", p["instap"], plus_min(p["instap"], 1), p["uit"], p["stop_ticks"])


class Veiling(Strategie):
    """D: long na de veilinguitslag van 13:00 ET."""

    def beslis_tijd(self):
        return "13:02" if self.params["voorwaarde"] == "eerst_omlaag" else "13:01"

    def _past(self, looptijden):
        keuze = self.params["veilingen"]
        if not looptijden:
            return False
        if keuze == "alle":
            return True
        delen = [x.strip() for x in looptijden.split(",")]
        if keuze == "10":
            return any(x.startswith("10-Year Note") for x in delen)
        return any(any(x.startswith(t) for t in ("5-Year Note", "10-Year Note", "30-Year Bond")) for x in delen)

    def signaal(self, dag, bars_tot):
        p = self.params
        if not self._past(dag.veiling):
            raise Geen("geen_veiling")
        if p["voorwaarde"] == "eerst_omlaag":
            a, b = p_om(bars_tot, "13:00", "12:50"), p_om(bars_tot, "13:02", "13:00")
            if a is None or b is None:
                raise Geen("geen_data")
            if not b < a:
                raise Geen("niet_eerst_omlaag")
            return Signaal(1, "market", "13:02", "13:03", p["uit"], p["stop_ticks"])
        return Signaal(1, "market", "13:01", "13:02", p["uit"], p["stop_ticks"])


class Drift10u(Strategie):
    """E: om 09:59 in de richting van 09:30 -> 09:59 als die beweging groot is, op dagen met een 10:00-cijfer."""
    min_historie = 20

    def beslis_tijd(self):
        return "09:59"

    def na_dag(self, dag):
        if dag.r_pre10 is not None:
            self.hist.append(abs(dag.r_pre10))

    def signaal(self, dag, bars_tot):
        p = self.params
        if not dag.release:
            raise Geen("geen_release")
        a, b = p_om(bars_tot, "09:30", "09:00"), p_om(bars_tot, "09:59", "09:30")
        if a is None or b is None:
            raise Geen("geen_data")
        if len(self.hist) < 20:
            raise Geen("te_weinig_historie")
        r = b / a - 1
        gem = sum(self.hist[-20:]) / 20.0
        if not abs(r) > p["k"] * gem or r == 0:
            raise Geen("filter_zwak")
        return Signaal(1 if r > 0 else -1, "market", "09:59", "09:59", p["uit"], p["stop_ticks"], info={"r": r})


class ORB(Strategie):
    """G: breakout van de range 08:20 -> 08:20 + range_min (controlegroep)."""

    def beslis_tijd(self):
        return plus_min("08:20", self.params["range_min"])

    def signaal(self, dag, bars_tot):
        p = self.params
        eind = self.beslis_tijd()
        r = [v for k, v in bars_tot.items() if "08:20" <= k < eind]
        if len(r) < max(3, p["range_min"] // 3):
            raise Geen("geen_data")
        hoog, laag = max(b[1] for b in r), min(b[2] for b in r)
        breedte = max(1, rond_af((hoog - laag) / TICK))
        stop = max(self.alg["min_stop_ticks"], min(breedte, p["max_stop_ticks"]))
        return Signaal(0, "breakout", eind, p["breakout_tot"], p["uit"], stop, hoog=hoog, laag=laag)


class OchtendReversal(Strategie):
    """H: om 08:20 tegen het laatste half uur van gisteren in, als dat groot was."""

    def beslis_tijd(self):
        return "08:20"

    def na_dag(self, dag):
        if dag.r_lh is not None:
            self.hist.append(abs(dag.r_lh))

    def signaal(self, dag, bars_tot):
        p = self.params
        v = dag.vorige
        if v is None or v.r_lh is None:
            raise Geen("geen_data")
        if len(self.hist) < 61:
            raise Geen("te_weinig_historie")
        drempel = kwantiel(self.hist[-61:-1], p["drempel_pct"])   # zonder gisteren zelf
        if not abs(v.r_lh) > drempel or v.r_lh == 0:
            raise Geen("filter_zwak")
        return Signaal(-1 if v.r_lh > 0 else 1, "market", "08:20", "08:21", p["uit"], p["stop_ticks"])


SOORTEN = {"laatste_halfuur": LaatsteHalfuur, "maandeinde": Maandeinde, "veiling": Veiling,
           "drift_10u": Drift10u, "orb": ORB, "ochtend_reversal": OchtendReversal}


def maak_strategie(sid, alg, kal, params=None):
    defin = alg["strategieen"][sid]
    p = dict(defin["standaard"])
    p.update(params or {})
    return SOORTEN[defin["soort"]](sid, defin, p, alg, kal)


def grid_configs(sid, alg):
    """Alle combinaties uit het grid -> [(label, params)]. De standaardinstelling zit er altijd bij."""
    defin = alg["strategieen"][sid]
    combos = [{}]
    for k, waarden in defin.get("grid", {}).items():
        combos = [dict(c, **{k: w}) for c in combos for w in waarden]
    out = []
    for c in combos:
        p = dict(defin["standaard"], **c)
        out.append((label(sid, c), p))
    if not any(p == defin["standaard"] for _, p in out):
        out.insert(0, (sid, dict(defin["standaard"])))
    return out


def label(sid, wijziging):
    if not wijziging:
        return sid
    return sid + " (" + ", ".join("%s=%s" % (k, v) for k, v in sorted(wijziging.items())) + ")"


# ======================= fill-simulatie (zelfde voor backtest en paper) =======================
def simuleer(signaal, bars, contracten, alg, stress=False):
    """Speelt één signaal af op de bars van de dag. -> dict met trade of None (niet gevuld)."""
    slip = (alg["stress_slippage_ticks"] if stress else alg["slippage_ticks"]) * TICK
    doorbraak = (alg["stress_limiet_doorbraak_ticks"] if stress else alg["limiet_doorbraak_ticks"]) * TICK
    s = signaal
    r, instap, instap_bar, stop = s.richting, None, None, None
    slechtste = beste = None
    uitstap = uit_bar = reden = None
    laatste = None
    for m in sorted(k for k in bars if k >= s.van):
        o, h, l, c = bars[m]
        if instap is None:
            if m > s.tot:
                return None
            if s.soort == "market":
                instap = o + r * slip
            elif s.soort == "limiet":
                if (l <= s.prijs - doorbraak) if r > 0 else (h >= s.prijs + doorbraak):
                    instap = s.prijs
            elif s.soort == "breakout":
                omhoog = h >= s.hoog + TICK
                omlaag = l <= s.laag - TICK
                if omhoog and omlaag:   # beide kanten in één bar: conservatief = long en meteen gestopt
                    r = 1
                    instap = s.hoog + TICK + slip
                    stop = instap - s.stop_ticks * TICK
                    instap_bar = m
                    slechtste = beste = instap
                    uitstap, uit_bar, reden = stop - slip, m, "stop"
                    break
                if omhoog:
                    r, instap = 1, max(o, s.hoog + TICK) + slip
                elif omlaag:
                    r, instap = -1, min(o, s.laag - TICK) - slip
            if instap is None:
                continue
            instap_bar = m
            stop = instap - r * s.stop_ticks * TICK
            slechtste = beste = instap
        if m >= s.uit:
            uitstap, uit_bar, reden = o - r * slip, m, "tijd"
            break
        if (l <= stop) if r > 0 else (h >= stop):
            uitstap, uit_bar, reden = stop - r * slip, m, "stop"
            slechtste = min(slechtste, uitstap) if r > 0 else max(slechtste, uitstap)
            break
        slechtste = min(slechtste, l) if r > 0 else max(slechtste, h)
        beste = max(beste, h) if r > 0 else min(beste, l)
        laatste = c
    if instap is None:
        return None
    if uitstap is None:   # data hield op vóór de uitstaptijd
        uitstap, uit_bar, reden = (laatste if laatste is not None else instap) - r * slip, "einde", "tijd_geen_bar"
    n = contracten
    bruto = (uitstap - instap) * r * PUNT_WAARDE * n
    kosten = alg["kosten_per_contract_rt"] * n
    netto = bruto - kosten
    risico = s.stop_ticks * TICK_WAARDE * n
    mae = min(0.0, (slechtste - instap) * r * PUNT_WAARDE * n, netto)
    mfe = max(0.0, (beste - instap) * r * PUNT_WAARDE * n)
    return {"richting": r, "instap": round(instap, 6), "uitstap": round(uitstap, 6), "stop": round(stop, 6),
            "instap_bar": instap_bar, "uitstap_bar": uit_bar, "uitstapreden": reden, "contracten": n,
            "stop_ticks": s.stop_ticks, "bruto": bruto, "kosten": kosten, "netto": netto, "risico": risico,
            "R": netto / risico if risico else None, "mae": mae, "mfe": mfe}


def aantal_contracten(stop_ticks, alg, afstand_tot_bodem=None, halveren_onder=600):
    n = int(math.floor(alg["risico_per_trade"] / (stop_ticks * TICK_WAARDE) + 1e-9))
    n = min(n, alg["max_contracten"])
    if n <= 0:
        return 0, "stop_te_groot"
    if afstand_tot_bodem is not None and afstand_tot_bodem < halveren_onder:
        n //= 2
        if n <= 0:
            return 0, "gehalveerd_naar_0"
    return n, ""


def speel_dag(strategie, dag, alg, stress=False, afstand_tot_bodem=None, week_pnl=0.0, weekstop=800):
    """Eén strategie, één dag. -> uitkomst {'datum','strategie','status','reden','trade'}. Werkt de historie NIET bij."""
    u = {"datum": dag.datum, "strategie": strategie.id, "status": "geen", "reden": "", "trade": None}
    blok = strategie.geblokkeerd(dag)
    if blok:
        u["reden"] = blok
        return u
    tijd = strategie.beslis_tijd()
    bars_tot = {k: v for k, v in dag.bars.items() if k < tijd}
    try:
        s = strategie.signaal(dag, bars_tot)
    except Geen as g:
        u["reden"] = str(g)
        return u
    if week_pnl <= -weekstop:
        u["reden"] = "weekstop"
        return u
    n, reden = aantal_contracten(s.stop_ticks, alg, afstand_tot_bodem)
    if n == 0:
        u["reden"] = reden
        return u
    t = simuleer(s, dag.bars, n, alg, stress)
    if t is None:
        u["status"], u["reden"] = "niet_gevuld", "niet_gevuld"
        return u
    t.update({"datum": dag.datum, "strategie": strategie.id, "signaal_prijs": s.prijs, "info": s.info,
              "veiling": bool(dag.veiling), "fomc": "fomc" in dag.redenen})
    u["status"], u["trade"] = "gevuld", t
    return u


def lees_json(pad):
    p = Path(pad)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
