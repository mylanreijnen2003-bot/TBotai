"""GitHub-versie: forward test op (nep-)Yahoo-data. Geen netwerk: een nep-bron levert de koersen."""
import copy
import datetime as dt
import random
import unittest

from bot_mgc.tests.hulp import FIRM, KAL, STRAT, TijdelijkeMap
from bot_mgc.backtest import run_variant, trades_van
from bot_mgc.forward import _lees_csv, rapporteer, run
from bot_mgc.journal_mgc import lees
from bot_mgc.logboek import lees_signalen
from bot_mgc.strategie import bouw_dagen
from bot_mgc.tijd import UTC
from bot_mgc.yahoo import ticker

SYM = ticker(2026, 12)          # GCZ26.CMX


def nepkoersen(van=dt.date(2026, 4, 1), tot=dt.date(2026, 11, 13), seed=7):
    """1-minuutbars 08:15-08:55 en 12:30-13:40 ET per handelsdag (random walk)."""
    rng, p, uit = random.Random(seed), 4000.0, {}
    d = van
    while d <= tot:
        if KAL.is_handelsdag(d):
            bars = {}
            p += rng.gauss(0, 15)                      # overnacht
            for h, m0, m1 in ((8, 15, 55), (12, 30, 59), (13, 0, 40)):
                for mm in range(m0, m1 + 1):
                    c = round(p + rng.gauss(0, 0.8), 1)
                    bars["%02d:%02d" % (h, mm)] = (p, round(max(p, c) + 0.3, 1), round(min(p, c) - 0.3, 1), c)
                    p = c
            uit[d] = bars
        d += dt.timedelta(days=1)
    return uit


def naar_5m(bars):
    out = {}
    for k in sorted(bars):
        h, m = k.split(":")
        sleutel = "%s:%02d" % (h, int(m) // 5 * 5)
        o, hi, lo, c = bars[k]
        if sleutel in out:
            o0, h0, l0, _ = out[sleutel]
            out[sleutel] = (o0, max(h0, hi), min(l0, lo), c)
        else:
            out[sleutel] = (o, hi, lo, c)
    return out


class NepBron:
    def __init__(self, koersen, tot=None, symbolen=(SYM,)):
        self.koersen, self.tot, self.symbolen = koersen, tot, symbolen
        self.verzoeken = []

    def bars(self, sym, van, tot, interval="1m"):
        self.verzoeken.append((sym, van, tot, interval))
        if sym not in self.symbolen:
            return {}
        return {d: (b if interval == "1m" else naar_5m(b)) for d, b in self.koersen.items()
                if van <= d <= tot and (self.tot is None or d <= self.tot)}


def strat_test():
    s = copy.deepcopy(STRAT)
    s["forward"].update({"max_dagen_terug_1m": 60, "max_dagen_terug_5m": 200})
    return s


def utc(d, hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return dt.datetime(d.year, d.month, d.day, h, m, tzinfo=UTC)


class TestForward(unittest.TestCase):
    def test_zelfde_trades_als_backtest(self):
        """De forward test geeft per strategie precies dezelfde trades als de backtest-code op dezelfde koersen."""
        koersen = nepkoersen()
        strat = strat_test()
        with TijdelijkeMap() as m:
            res = run(NepBron(koersen), m, nu=utc(dt.date(2026, 11, 13), "20:00"), strat=strat)
            self.assertFalse(res["gestopt"])
            journal = [r for r in lees(m / "journal_bot.csv") if r["account"] == "mgc-paper"]
            self.assertGreater(len(journal), 30)
            ruwe = [(d, "GCZ6", b) for d, b in sorted(koersen.items())]
            rolls = {d for d, _, _ in ruwe if KAL.is_roll_dag(d)}
            dagen = bouw_dagen(ruwe, KAL, strat, roll_dagen=rolls)
            start = dt.date.fromisoformat(strat["forward"]["startdatum"])
            for var in strat["paper_varianten"]:
                bt = trades_van(run_variant(dagen, strat, FIRM, var, vanaf=start)[0])
                fw = [r for r in journal if r["setup"] == "G-" + var]
                with self.subTest(variant=var):
                    self.assertEqual([t["datum"].isoformat() for t in bt], [r["datum"] for r in fw])
                    for t, r in zip(bt, fw):
                        self.assertEqual(t["contracten"], int(r["contracten"]))
                        self.assertAlmostEqual(t["netto"], float(r["netto_pnl"]), places=2)
                        self.assertEqual("long" if t["richting"] > 0 else "short", r["richting"])
                        self.assertAlmostEqual(t["instap"], float(r["werkelijke_instap"]), places=1)
                        self.assertAlmostEqual(t["uitstap"], float(r["uitstapprijs"]), places=1)
                        self.assertAlmostEqual(t["R"], float(r["R"]), places=2)

    def test_niet_dubbel_en_inhalen(self):
        koersen = nepkoersen()
        strat = strat_test()
        with TijdelijkeMap() as m:
            run(NepBron(koersen), m, nu=utc(dt.date(2026, 10, 7), "20:00"), strat=strat)      # ma 5 t/m wo 7 okt
            self.assertEqual([r["datum"] for r in _lees_csv(m / "verwerkt.csv")], ["2026-10-05", "2026-10-06", "2026-10-07"])
            n1 = len(lees(m / "journal_bot.csv"))
            run(NepBron(koersen), m, nu=utc(dt.date(2026, 10, 7), "21:00"), strat=strat)      # nog een keer: niets nieuws
            self.assertEqual(len(lees(m / "journal_bot.csv")), n1)
            run(NepBron(koersen), m, nu=utc(dt.date(2026, 10, 12), "20:00"), strat=strat)     # do, vr en ma ingehaald
            self.assertEqual([r["datum"] for r in _lees_csv(m / "verwerkt.csv")][-3:], ["2026-10-08", "2026-10-09", "2026-10-12"])
            sig = lees_signalen(m / "logs", "mgc-paper")
            self.assertEqual(len([r for r in sig if r["datum"] == "2026-10-09"]), 6)          # één regel per strategie

    def test_vandaag_pas_na_het_slot(self):
        with TijdelijkeMap() as m:
            run(NepBron(nepkoersen()), m, nu=utc(dt.date(2026, 10, 5), "16:00"), strat=strat_test())   # 12:00 ET
            self.assertEqual(_lees_csv(m / "verwerkt.csv"), [])

    def test_geen_data_wachten_dan_opgeven(self):
        koersen = nepkoersen()
        strat = strat_test()
        with TijdelijkeMap() as m:
            run(NepBron(koersen, tot=dt.date(2026, 10, 5)), m, nu=utc(dt.date(2026, 10, 6), "20:00"), strat=strat)
            self.assertEqual([r["datum"] for r in _lees_csv(m / "verwerkt.csv")], ["2026-10-05"])   # 6 okt: opnieuw proberen
            run(NepBron(koersen, tot=dt.date(2026, 10, 5)), m, nu=utc(dt.date(2026, 10, 12), "20:00"), strat=strat)
            st = {r["datum"]: r["status"] for r in _lees_csv(m / "verwerkt.csv")}
            self.assertEqual(st["2026-10-06"], "geen_data")
            self.assertNotIn("2026-10-12", st)

    def test_terugval_op_gc_f(self):
        koersen = nepkoersen()
        with TijdelijkeMap() as m:
            run(NepBron(koersen, symbolen=("GC=F",)), m, nu=utc(dt.date(2026, 10, 6), "20:00"), strat=strat_test())
            self.assertEqual({r["contract"] for r in _lees_csv(m / "verwerkt.csv")}, {"GC=F"})

    def test_noodstop(self):
        with TijdelijkeMap() as m:
            (m / "STOP").write_text("")
            self.assertTrue(run(NepBron(nepkoersen()), m, nu=utc(dt.date(2026, 10, 6), "20:00"), strat=strat_test())["gestopt"])

    def test_rapporten(self):
        with TijdelijkeMap() as m:
            res = run(NepBron(nepkoersen()), m, nu=utc(dt.date(2026, 11, 13), "20:00"), strat=strat_test())
            md = rapporteer(res, m).read_text(encoding="utf-8")
            for stuk in ("dagrapport 13-11-2026", "## Sinds de start", "## Eindoordeel forward test", "| A – "):
                self.assertIn(stuk, md)
            self.assertTrue((m / "reports" / "dagrapport.html").exists())
            self.assertTrue((m / "reports" / "dagrapporten" / "2026-11-13.md").exists())


if __name__ == "__main__":
    unittest.main()
