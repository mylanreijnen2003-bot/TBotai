"""Kalender voor MGC: niet-handeldagen, FOMC-dagen (wél traden, apart rapporteren) en de vaste rollregel.

Leest calendar.json: de bestaande sleutels (vervroegde_sluiting, us_feestdagen, geen_trade_periodes, fomc)
plus de toegevoegde sleutels "mgc" (beursfeestdagen en vervroegde sluitingen 2010-2027) en "zn" (FOMC-historie).
Er wordt niets in calendar.json geschreven.
"""
import datetime as dt

MAAND_CODES = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M", 7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
CODE_MAAND = {v: k for k, v in MAAND_CODES.items()}

WEEKEND = "weekend"
FEESTDAG = "feestdag"
VERVROEGD = "vervroegde_sluiting"
KERST = "kerstperiode"
GEEN_TRADE_PERIODE = "geen_trade_periode"
ROLL_DAG = "roll_dag"


def _d(s):
    return dt.date.fromisoformat(s)


class Kalender:
    def __init__(self, cal, strat):
        mgc = cal.get("mgc", {})
        self.feestdagen = {_d(x["datum"]) for x in mgc.get("beursfeestdagen", [])} | \
                          {_d(x["datum"]) for x in cal.get("us_feestdagen", [])}
        self.vervroegd = {_d(x["datum"]) for x in mgc.get("vervroegde_sluiting", [])} | \
                         {_d(x["datum"]) for x in cal.get("vervroegde_sluiting", [])}
        self.fomc = {_d(x) for x in cal.get("zn", {}).get("fomc_besluit", [])} | \
                    {_d(x) for x in cal.get("fomc", {}).get("dagen", [])}
        self.periodes = [(_d(p["van"]), _d(p["tot"])) for p in cal.get("geen_trade_periodes", [])]
        k = strat.get("kerstperiode", {"van": "12-24", "tot": "01-02"})
        self.kerst_van = tuple(int(x) for x in k["van"].split("-"))
        self.kerst_tot = tuple(int(x) for x in k["tot"].split("-"))
        self.roll_n = strat["roll"]["handelsdagen_voor_laatste_handelsdag"]
        self.maanden = [CODE_MAAND[c] for c in strat["instrument"]["contractmaanden"]]

    # ---------- handelsdagen ----------
    def is_handelsdag(self, d):
        return d.weekday() < 5 and d not in self.feestdagen

    def vorige_handelsdag(self, d):
        d -= dt.timedelta(days=1)
        while not self.is_handelsdag(d):
            d -= dt.timedelta(days=1)
        return d

    def handelsdagen_tussen(self, a, b):
        if a == b:
            return 0
        sign, lo, hi = (1, a, b) if a < b else (-1, b, a)
        n, d = 0, lo
        while d < hi:
            d += dt.timedelta(days=1)
            if self.is_handelsdag(d):
                n += 1
        return sign * n

    def _in_kerst(self, d):
        md = (d.month, d.day)
        return md >= self.kerst_van or md <= self.kerst_tot

    # ---------- niet-handeldagen ----------
    def redenen_geen_trade(self, d, roll_dag=None):
        """FOMC-dagen worden wél gehandeld [KEUZE]. roll_dag=None: vaste rollregel; backtest geeft het zelf door."""
        r = []
        if d.weekday() >= 5:
            r.append(WEEKEND)
        if d in self.feestdagen:
            r.append(FEESTDAG)
        if d in self.vervroegd:
            r.append(VERVROEGD)
        if self._in_kerst(d):
            r.append(KERST)
        if any(a <= d <= b for a, b in self.periodes) and KERST not in r:
            r.append(GEEN_TRADE_PERIODE)
        is_roll = (self.is_handelsdag(d) and self.is_roll_dag(d)) if roll_dag is None else roll_dag
        if is_roll:
            r.append(ROLL_DAG)
        return r

    def is_fomc(self, d):
        return d in self.fomc

    # ---------- vaste rollregel (live) ----------
    def laatste_handelsdag_maand(self, jaar, maand):
        d = dt.date(jaar + (maand == 12), maand % 12 + 1, 1) - dt.timedelta(days=1)
        while not self.is_handelsdag(d):
            d -= dt.timedelta(days=1)
        return d

    def roll_datum(self, jaar, leveringsmaand):
        """Eerste dag op het volgende contract: 5 handelsdagen vóór de laatste handelsdag van de maand vóór levering."""
        j, m = (jaar, leveringsmaand - 1) if leveringsmaand > 1 else (jaar - 1, 12)
        d = self.laatste_handelsdag_maand(j, m)
        for _ in range(self.roll_n):
            d = self.vorige_handelsdag(d)
        return d

    def contract_voor(self, d):
        for jaar in (d.year, d.year + 1):
            for m in self.maanden:
                if self.roll_datum(jaar, m) > d:
                    return (jaar, m)
        return (d.year + 2, self.maanden[0])  # pragma: no cover

    def is_roll_dag(self, d):
        j, m = self.contract_voor(d)
        idx = self.maanden.index(m)
        pj, pm = (j, self.maanden[idx - 1]) if idx > 0 else (j - 1, self.maanden[-1])
        return self.roll_datum(pj, pm) == d

    def roll_datums(self, van, tot):
        out = []
        for jaar in range(van.year, tot.year + 2):
            for m in self.maanden:
                r = self.roll_datum(jaar, m)
                if van <= r <= tot:
                    out.append(r)
        return sorted(out)


def contract_code(jaar, maand, root="MGC"):
    return "%s%s%d" % (root, MAAND_CODES[maand], jaar % 10)


def vergelijk_rolls_v0(kal, v0_rolls, max_afwijking):
    """v0_rolls = eerste dagen op een nieuw .v.0-contract. Meldingen bij > max_afwijking handelsdagen verschil."""
    if not v0_rolls:
        return []
    regel = kal.roll_datums(min(v0_rolls) - dt.timedelta(days=90), max(v0_rolls) + dt.timedelta(days=90))
    meldingen = []
    for r in v0_rolls:
        dichtst = min(regel, key=lambda x: abs((x - r).days))
        verschil = kal.handelsdagen_tussen(dichtst, r)
        if abs(verschil) > max_afwijking:
            meldingen.append({"v0_roll": r, "regel_roll": dichtst, "verschil_handelsdagen": verschil})
    return meldingen
