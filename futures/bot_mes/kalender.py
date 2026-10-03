"""Kalender MES: handelsdagen (NYSE/CME-feestdagen uit calendar.json), niet-handeldagen en de rollregel.

Niet traden op: weekend, beursfeestdag, vervroegde sluiting, 24 dec t/m 2 jan, FOMC-dagen (plan-MES §5).
Roll: 8 kalenderdagen vóór de expiratie (derde vrijdag van mrt/jun/sep/dec) naar het volgende contract.
"""
import datetime as dt

MAAND_CODES = {3: "H", 6: "M", 9: "U", 12: "Z"}


def _d(s):
    return dt.date.fromisoformat(s)


def derde_vrijdag(jaar, maand):
    d = dt.date(jaar, maand, 15)
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    return d


class Kalender:
    def __init__(self, cal, strat):
        mgc = cal.get("mgc", {})
        self.feestdagen = {_d(x["datum"]) for x in mgc.get("beursfeestdagen", [])} | \
                          {_d(x["datum"]) for x in cal.get("us_feestdagen", [])}
        self.vervroegd = {_d(x["datum"]) for x in mgc.get("vervroegde_sluiting", [])} | \
                         {_d(x["datum"]) for x in cal.get("vervroegde_sluiting", [])}
        self.fomc = {_d(x) for x in cal.get("zn", {}).get("fomc_besluit", [])} | \
                    {_d(x) for x in cal.get("fomc", {}).get("dagen", [])}
        self.maanden = list(strat["instrument"]["contractmaanden"])
        self.roll_dagen = strat["roll_kalenderdagen_voor_expiratie"]

    def is_handelsdag(self, d):
        return d.weekday() < 5 and d not in self.feestdagen

    def vorige_handelsdag(self, d):
        d -= dt.timedelta(days=1)
        while not self.is_handelsdag(d):
            d -= dt.timedelta(days=1)
        return d

    def redenen_geen_trade(self, d):
        r = []
        if d.weekday() >= 5:
            r.append("weekend")
        if d in self.feestdagen:
            r.append("feestdag")
        if d in self.vervroegd:
            r.append("vervroegde_sluiting")
        if (d.month, d.day) >= (12, 24) or (d.month, d.day) <= (1, 2):
            r.append("kerstperiode")
        if d in self.fomc:
            r.append("fomc")
        return r

    def roll_datum(self, jaar, maand):
        return derde_vrijdag(jaar, maand) - dt.timedelta(days=self.roll_dagen)

    def contract_voor(self, d):
        """(jaar, maand) van het front-month contract dat de bot op dag d volgt."""
        for jaar in (d.year, d.year + 1):
            for m in self.maanden:
                if self.roll_datum(jaar, m) > d:
                    return (jaar, m)
        return (d.year + 1, self.maanden[0])  # pragma: no cover


def contract_code(jaar, maand, root="ES"):
    return "%s%s%d" % (root, MAAND_CODES[maand], jaar % 10)
