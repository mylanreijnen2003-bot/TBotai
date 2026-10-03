"""Dagelijkse fronttest: speelt na het slot alle strategieën (A, B1, B2, C, D, E, G, H) af op de koersen van die dag.

- Geen orders: alleen koersen ophalen bij TopstepX (ProjectX API) en gesimuleerde fills.
- Elke strategie ziet van vandaag alleen de koersen vóór zijn eigen beslismoment (geen vooruitkijken).
- Gemiste dagen (pc uit) worden de volgende keer ingehaald.
- Uitvoer: journal_bot.csv (account zn-paper, setup ZN-A, ZN-B1, ...), logs/fronttest_signalen.csv en
  reports/fronttest.html.

Gebruik: python -m bot_zn.dagelijks [--auto] [--dag JJJJ-MM-DD]
"""
import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from .instellingen import BOT, lees_env, load_calendar, load_config, load_strategy
from .journal_zn import voeg_live_trade_toe
from .kalender_zn import Kalender, contract_code
from .multi import bouw_mdagen, load_strategieen, maak_strategie, speel_dag
from .releases import releases_10u
from .tijd import ET, et

ACCOUNT = "zn-paper"
VENSTER = ("08:00", "15:15")
HISTORIE_DAGEN = 150          # kalenderdagen terug voor de historie van de strategieën
KLAAR_NA = "15:20:00"         # ET: daarna is de dag compleet
SIGNAAL_KOLOMMEN = ["datum", "strategie", "status", "reden", "richting", "contracten", "instap", "uitstap",
                    "uitstapreden", "instap_bar", "uitstap_bar", "netto", "R", "verwerkt_op"]


def setup(sid):
    return "ZN-" + sid


class Fronttest:
    def __init__(self, broker, bot_map=BOT, cfg=None, log=print):
        self.broker = broker
        self.map = Path(bot_map)
        self.cfg = cfg or {}
        self.log = log
        self.strat = load_strategy()
        self.alg = load_strategieen()
        cal = load_calendar()
        self.kal = Kalender(cal, self.strat)
        self.veilingen = {dt.date.fromisoformat(x["datum"]): x.get("looptijden", "")
                          for x in cal.get("zn", {}).get("treasury_veiling_13u", [])}
        self.releases = releases_10u(2010, dt.date.today().year + 1, self.kal)
        self.cache_pad = self.map / "data" / "fronttest_bars.csv"
        self.status_pad = self.map / "data" / "fronttest_status.json"
        self.signalen_pad = self.map / "logs" / "fronttest_signalen.csv"
        self.journal_pad = self.map / "journal_bot.csv"
        self.cache = self._lees_cache()
        self._cids = {}

    # ---------------- koersen ----------------
    def _lees_cache(self):
        c = {}
        if self.cache_pad.exists():
            with open(self.cache_pad, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    k = (r["datum"], r["contract"])
                    c.setdefault(k, {})
                    if r["tijd_et"]:
                        c[k][r["tijd_et"]] = (float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]))
        return c

    def _schrijf_cache(self):
        self.cache_pad.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_pad, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["datum", "contract", "tijd_et", "o", "h", "l", "c"])
            oud = (dt.datetime.now(ET).date() - dt.timedelta(days=HISTORIE_DAGEN + 30)).isoformat()
            for (d, code), bars in sorted(self.cache.items()):
                if d < oud:              # niet meer nodig voor de historie: bestand klein houden
                    continue
                if not bars:
                    w.writerow([d, code, "", "", "", "", ""])   # dag zonder koersen: niet opnieuw ophalen
                for t, (o, h, l, c) in sorted(bars.items()):
                    w.writerow([d, code, t, o, h, l, c])

    def _cid(self, jm):
        if jm not in self._cids:
            self._cids[jm] = self.broker.contract_id(jm[0], jm[1], zoekterm=self.cfg.get("contract_zoekterm", "ZN"),
                                                     live=bool(self.cfg.get("data_live", False)),
                                                     symbol_id=self.cfg.get("contract_symbol_id"))
        return self._cids[jm]

    def _haal(self, jm, dagen):
        """Haalt ontbrekende dagen op voor contract jm, in blokken van maximaal 10 kalenderdagen."""
        code = contract_code(*jm)
        nodig = sorted(d for d in dagen if (d.isoformat(), code) not in self.cache)
        i = 0
        while i < len(nodig):
            start = nodig[i]
            j = i
            while j + 1 < len(nodig) and (nodig[j + 1] - start).days < 10:
                j += 1
            eind = nodig[j]
            bars = self.broker.bars(self._cid(jm), et(start, "00:00"), et(eind + dt.timedelta(days=1), "00:00"),
                                    live=bool(self.cfg.get("data_live", False)), limiet=20000)
            per_dag = {}
            for b in bars:
                t = b["t"].astimezone(ET)
                hm = t.strftime("%H:%M")
                if VENSTER[0] <= hm <= VENSTER[1]:
                    per_dag.setdefault(t.date().isoformat(), {})[hm] = (b["o"], b["h"], b["l"], b["c"])
            recent = dt.datetime.now(ET).date() - dt.timedelta(days=3)
            for d in nodig[i:j + 1]:
                b = per_dag.get(d.isoformat(), {})
                if b or d < recent:      # een recente dag zonder koersen niet vastleggen: later opnieuw proberen
                    self.cache[(d.isoformat(), code)] = b
            i = j + 1

    def dagen_voor(self, doel):
        """MDagen van de historie + de doeldag, allemaal op het contract van de doeldag (consistente prijzen)."""
        jm = self.kal.contract_voor(doel)
        code = contract_code(*jm)
        dagen, d = [], doel - dt.timedelta(days=HISTORIE_DAGEN)
        while d <= doel:
            if self.kal.is_handelsdag(d):
                dagen.append(d)
            d += dt.timedelta(days=1)
        self._haal(jm, dagen)
        ruwe = [(d, code, self.cache[(d.isoformat(), code)]) for d in dagen if self.cache.get((d.isoformat(), code))]
        return bouw_mdagen(ruwe, self.kal, veilingen=self.veilingen, releases=self.releases)

    # ---------------- logboek ----------------
    def verwerkt(self):
        if not self.signalen_pad.exists():
            return set()
        with open(self.signalen_pad, newline="", encoding="utf-8") as f:
            return {(r["datum"], r["strategie"]) for r in csv.DictReader(f)}

    def _log_signaal(self, rij):
        self.signalen_pad.parent.mkdir(parents=True, exist_ok=True)
        nieuw = not self.signalen_pad.exists()
        with open(self.signalen_pad, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SIGNAAL_KOLOMMEN, extrasaction="ignore")
            if nieuw:
                w.writeheader()
            w.writerow(rij)

    # ---------------- één dag ----------------
    def verwerk_dag(self, doel):
        gedaan = self.verwerkt()
        sids = [s for s in self.alg["strategieen"] if (doel.isoformat(), s) not in gedaan]
        if not sids:
            return 0
        mdagen = self.dagen_voor(doel)
        vandaag = [m for m in mdagen if m.datum == doel]
        if not vandaag:
            self.log("%s: geen koersen ontvangen (beurs dicht of nog geen data); later opnieuw." % doel)
            return 0
        vandaag = vandaag[0]
        geschiedenis = [m for m in mdagen if m.datum < doel]
        n = 0
        for sid in sids:
            s = maak_strategie(sid, self.alg, self.kal)
            for m in geschiedenis:
                s.na_dag(m)
            # De fronttest meet de strategie zelf: positiegrootte volgens het risico ($200, max 3), maar zonder
            # account-regels (halveren, weekstop). Die horen bij het account in fase C, niet bij de vergelijking.
            u = speel_dag(s, vandaag, self.alg)
            t = u["trade"]
            rij = {"datum": doel.isoformat(), "strategie": sid, "status": u["status"], "reden": u["reden"],
                   "verwerkt_op": dt.datetime.now(ET).strftime("%Y-%m-%d %H:%M")}
            if t:
                info = t.get("info") or {}
                voeg_live_trade_toe(dict(t, limiet=t.get("signaal_prijs") or t["instap"], rod=info.get("rod"),
                                         mediaan=info.get("drempel"), notitie="fronttest " + sid),
                                    ACCOUNT, setup=setup(sid), pad=self.journal_pad)
                rij.update({"richting": "long" if t["richting"] > 0 else "short", "contracten": t["contracten"],
                            "instap": t["instap"], "uitstap": t["uitstap"], "uitstapreden": t["uitstapreden"],
                            "instap_bar": t["instap_bar"], "uitstap_bar": t["uitstap_bar"],
                            "netto": "%.2f" % t["netto"], "R": "%.3f" % t["R"]})
                n += 1
            self._log_signaal(rij)
        self.log("%s: %d strategieën afgespeeld, %d trades." % (doel, len(sids), n))
        return n

    # ---------------- welke dagen ----------------
    def laatste_complete_dag(self, nu=None):
        nu = nu or dt.datetime.now(ET)
        d = nu.date() if nu.strftime("%H:%M:%S") >= KLAAR_NA else nu.date() - dt.timedelta(days=1)
        while not self.kal.is_handelsdag(d):
            d -= dt.timedelta(days=1)
        return d

    def te_doen(self, nu=None):
        """Handelsdagen na de laatst verwerkte dag t/m de laatste complete dag. De eerste keer: alleen de laatste."""
        eind = self.laatste_complete_dag(nu)
        status = json.loads(self.status_pad.read_text(encoding="utf-8")) if self.status_pad.exists() else {}
        if not status.get("laatst_verwerkt"):
            return [eind]
        d = dt.date.fromisoformat(status["laatst_verwerkt"]) + dt.timedelta(days=1)
        out = []
        while d <= eind and len(out) < 30:
            if self.kal.is_handelsdag(d):
                out.append(d)
            d += dt.timedelta(days=1)
        return out

    def draai(self, nu=None, dagen=None):
        dagen = dagen or self.te_doen(nu)
        for d in dagen:
            self.verwerk_dag(d)
            status = json.loads(self.status_pad.read_text(encoding="utf-8")) if self.status_pad.exists() else {}
            if (d.isoformat(), list(self.alg["strategieen"])[-1]) in self.verwerkt():
                status.setdefault("start", d.isoformat())
                status["laatst_verwerkt"] = max(d.isoformat(), status.get("laatst_verwerkt", ""))
                self.status_pad.parent.mkdir(parents=True, exist_ok=True)
                self.status_pad.write_text(json.dumps(status, indent=2), encoding="utf-8")
        self._schrijf_cache()
        from .fronttest_rapport import schrijf_fronttest_rapport
        return schrijf_fronttest_rapport(self.map, self.alg)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="vanuit de geplande taak (geen vragen)")
    ap.add_argument("--dag", default=None, help="één bepaalde dag (JJJJ-MM-DD) opnieuw proberen")
    a = ap.parse_args(argv)
    print("%s ZN-fronttest gestart" % dt.datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"))
    env = lees_env()
    if not env.get("PROJECTX_USERNAME") or not env.get("PROJECTX_API_KEY"):
        print("PROJECTX_USERNAME en PROJECTX_API_KEY ontbreken in .env (daytrading-map).")
        return 2
    from .broker import ApiFout, ProjectXClient, VerbindingsFout
    cfg = load_config()
    broker = ProjectXClient(env["PROJECTX_USERNAME"], env["PROJECTX_API_KEY"], cfg.get("api_basis", "https://api.topstepx.com"))
    try:
        broker.login()
        ft = Fronttest(broker, BOT, cfg)
        pad = ft.draai(dagen=[dt.date.fromisoformat(a.dag)] if a.dag else None)
    except (ApiFout, VerbindingsFout) as e:
        print("Mislukt: %s. De volgende run haalt de gemiste dagen in." % e)
        return 1
    print("Rapport: %s" % pad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
