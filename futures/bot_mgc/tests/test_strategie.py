"""Strategie: ROD, filter, richting, stop, positiegrootte, weekstop (plan §10 tests 1-5 en 7)."""
import datetime as dt
import unittest

from bot_mgc.tests.hulp import FIRM, KAL, STRAT, bars_lijn, historie
from bot_mgc.backtest import run_variant
from bot_mgc.strategie import (FILTER_ZWAK, GEEN_RICHTING, GEHALVEERD_NUL, STOP_TE_GROOT, STOP_TE_KLEIN, TE_WEINIG_HISTORIE,
                               WEEKSTOP, Dag, beslis, bouw_dagen, contracten)


def bars(signaal, slot):
    b = bars_lijn("12:30", "13:30", signaal)
    b["12:59"] = (signaal,) * 4
    b["13:29"] = (slot,) * 4
    return b


def vandaag(rod, datum=dt.date(2026, 1, 1)):
    return Dag(datum=datum, signaal=2000.0, rod=rod)


class Test01ROD(unittest.TestCase):
    def test_rod_maandag_en_na_feestdag(self):
        ruwe = [
            (dt.date(2026, 1, 8), "G", bars(1999.0, 2000.0)),
            (dt.date(2026, 1, 9), "G", bars(2000.0, 2000.0)),    # vr: slot 2000
            (dt.date(2026, 1, 12), "G", bars(2010.0, 2012.0)),   # ma -> vr
            (dt.date(2026, 1, 16), "G", bars(2000.0, 2020.0)),   # vr: slot 2020
            (dt.date(2026, 1, 20), "G", bars(2030.2, 2031.0)),   # di na MLK-dag (beursfeestdag)
        ]
        d = {x.datum: x for x in bouw_dagen(ruwe, KAL, STRAT)}
        self.assertAlmostEqual(d[dt.date(2026, 1, 12)].rod, 2010.0 / 2000.0 - 1)
        self.assertAlmostEqual(d[dt.date(2026, 1, 20)].rod, 2030.2 / 2020.0 - 1)
        self.assertIsNone(d[dt.date(2026, 1, 16)].rod)      # do 15 jan ontbreekt
        self.assertAlmostEqual(d[dt.date(2026, 1, 12)].beweging, 2.0)

    def test_rod_niet_over_een_contractwissel(self):
        ruwe = [(dt.date(2026, 1, 8), "G", bars(2000.0, 2000.0)), (dt.date(2026, 1, 9), "J", bars(2005.0, 2005.0))]
        self.assertIsNone(bouw_dagen(ruwe, KAL, STRAT)[1].rod)


class Test02FilterGeenVooruitkijken(unittest.TestCase):
    def test_mediaan_alleen_vorige_60_dagen(self):
        h = historie(70, rod=0.001)
        for x in h[:10]:
            x.rod = 0.05
        b = beslis(vandaag(0.0011), h, STRAT, "A")
        self.assertAlmostEqual(b.mediaan, 0.001)
        self.assertTrue(b.is_trade)
        self.assertEqual(beslis(vandaag(0.001), h, STRAT, "A").reden, FILTER_ZWAK)

    def test_vandaag_telt_niet_mee(self):
        h = historie(60, rod=0.001)
        self.assertAlmostEqual(beslis(vandaag(0.9), h, STRAT, "A").mediaan, 0.001)

    def test_te_weinig_historie(self):
        self.assertEqual(beslis(vandaag(0.01), historie(59), STRAT, "A").reden, TE_WEINIG_HISTORIE)


class Test03Richting(unittest.TestCase):
    def test_long_short_geen(self):
        h = historie(60, rod=0.0001)
        self.assertEqual(beslis(vandaag(0.002), h, STRAT, "A").richting, 1)
        self.assertEqual(beslis(vandaag(-0.002), h, STRAT, "A").richting, -1)
        b = beslis(vandaag(0.0), h, STRAT, "C")
        self.assertEqual((b.is_trade, b.reden), (False, GEEN_RICHTING))
        self.assertEqual(beslis(vandaag(-0.002), h, STRAT, "B").richting, 1)   # B altijd long


class Test04Stop(unittest.TestCase):
    def test_stop_afgerond_op_tick(self):
        for gem, verwacht in ((4.0, 6.0), (3.03, 4.5), (2.0, 3.0), (5.37, 8.1)):   # 1,5 x 3,03 = 4,545 -> 4,5
            b = beslis(vandaag(0.01), historie(60, beweging=gem), STRAT, "A")
            self.assertAlmostEqual(b.stop_afstand, verwacht, msg="gemiddeld %s" % gem)

    def test_stop_te_klein(self):
        b = beslis(vandaag(0.01), historie(60, beweging=1.3), STRAT, "A")   # 1,95 -> 2,0: net genoeg
        self.assertTrue(b.is_trade)
        b = beslis(vandaag(0.01), historie(60, beweging=1.2), STRAT, "A")   # 1,8 < 2,0
        self.assertEqual(b.reden, STOP_TE_KLEIN)


class Test05Positiegrootte(unittest.TestCase):
    def test_contracten(self):
        self.assertEqual(contracten(8.0, STRAT), (2, ""))
        self.assertEqual(contracten(6.6, STRAT), (3, ""))
        self.assertEqual(contracten(21.0, STRAT), (0, STOP_TE_GROOT))
        self.assertEqual(contracten(2.0, STRAT), (10, ""))     # maximum 10
        self.assertEqual(contracten(4.0, STRAT), (5, ""))

    def test_halveren(self):
        self.assertEqual(contracten(4.0, STRAT, afstand_tot_bodem=599), (2, ""))    # 5 -> 2
        self.assertEqual(contracten(8.0, STRAT, afstand_tot_bodem=599), (1, ""))    # 2 -> 1
        self.assertEqual(contracten(12.0, STRAT, afstand_tot_bodem=599), (0, GEHALVEERD_NUL))
        self.assertEqual(contracten(4.0, STRAT, afstand_tot_bodem=600), (5, ""))


def verlies_dagen(start, n):
    """n opeenvolgende handelsdagen met een long-signaal dat op de stop (6 punten) eindigt."""
    out, d = [], start
    while len(out) < n:
        if KAL.is_handelsdag(d) and not KAL.redenen_geen_trade(d):
            b = bars_lijn("12:30", "13:30", 2000.0)
            b["13:01"] = (2000.0, 2000.0, 1990.0, 1991.0)
            out.append(Dag(datum=d, contract="Z", signaal=2000.0, slot=2000.0, rod=0.01, beweging=4.0, bars=b))
        d += dt.timedelta(days=1)
    return out


class Test07WeekstopEnEenTradePerDag(unittest.TestCase):
    def test_weekstop(self):
        # gemiddelde beweging 3,33 -> stop 5,0 punten -> 4 contracten. Instap 2000,1 (open + 1 tick), stop 1995,1,
        # fill 1995,0: verlies 4 x 5,1 x $10 + 4 x $2,42 = $213,68. Na 4 dagen -$854,72 -> vrijdag weekstop.
        h = historie(60, rod=0.0001, beweging=10.0 / 3, start=dt.date(2026, 6, 1))
        dagen = h + verlies_dagen(dt.date(2026, 9, 21), 6)       # ma 21 t/m vr 25 sep + ma 28 sep
        uitk = [u for u in run_variant(dagen, STRAT, FIRM, "A")[0] if u["datum"] >= dt.date(2026, 9, 21)]
        self.assertAlmostEqual(uitk[0]["trade"]["netto"], -(4 * 5.1 * 10) - 4 * 2.42)
        self.assertEqual([u["status"] for u in uitk], ["gevuld"] * 4 + [WEEKSTOP, "gevuld"])   # nieuwe week: weer traden

    def test_max_een_trade_per_dag(self):
        h = historie(60, rod=0.0001, beweging=4.0, start=dt.date(2026, 6, 1))
        uitk = run_variant(h + verlies_dagen(dt.date(2026, 9, 21), 3), STRAT, FIRM, "A")[0]
        per_dag = {}
        for u in uitk:
            per_dag[u["datum"]] = per_dag.get(u["datum"], 0) + (1 if u["trade"] else 0)
        self.assertLessEqual(max(per_dag.values()), 1)


if __name__ == "__main__":
    unittest.main()
