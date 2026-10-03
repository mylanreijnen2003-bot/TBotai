"""Strategie: ROD, filter, richting, stop, positiegrootte, weekstop (plan §11 tests 1-5 en 19)."""
import datetime as dt
import unittest

from bot_zn.tests.hulp import FIRM, KAL, STRAT, bars_lijn, historie
from bot_zn.backtest import run_variant
from bot_zn.strategie import (FILTER_ZWAK, GEEN_RICHTING, GEHALVEERD_NUL, STOP_TE_GROOT, TE_WEINIG_HISTORIE, WEEKSTOP,
                              Dag, beslis, bouw_dagen, contracten)
from bot_zn.tijd import TICK


def bars(signaal, slot):
    b = bars_lijn("14:00", "15:00", signaal)
    b["14:29"] = (signaal, signaal, signaal, signaal)
    b["14:59"] = (slot, slot, slot, slot)
    return b


class Test01ROD(unittest.TestCase):
    def test_rod_gewone_dag_maandag_en_na_feestdag(self):
        ruwe = [
            (dt.date(2026, 1, 8), "Z", bars(109.9, 110.0)),     # do
            (dt.date(2026, 1, 9), "Z", bars(110.0, 110.0)),     # vr: slot 110,0
            (dt.date(2026, 1, 12), "Z", bars(110.11, 110.2)),   # ma: vorige handelsdag = vr
            (dt.date(2026, 1, 16), "Z", bars(110.0, 111.0)),    # vr: slot 111,0
            (dt.date(2026, 1, 20), "Z", bars(111.111, 111.0)),  # di na MLK-dag (ma 19 jan, feestdag)
        ]
        d = {x.datum: x for x in bouw_dagen(ruwe, KAL, STRAT)}
        self.assertAlmostEqual(d[dt.date(2026, 1, 9)].rod, 110.0 / 110.0 - 1)
        self.assertAlmostEqual(d[dt.date(2026, 1, 12)].rod, 110.11 / 110.0 - 1)      # maandag -> vrijdag
        self.assertAlmostEqual(d[dt.date(2026, 1, 20)].rod, 111.111 / 111.0 - 1)     # na feestdag -> vrijdag ervoor
        self.assertIsNone(d[dt.date(2026, 1, 16)].rod)  # do 15 jan ontbreekt in de data: geen ROD

    def test_rod_niet_over_een_contractwissel(self):
        ruwe = [(dt.date(2026, 1, 8), "H", bars(110.0, 110.0)), (dt.date(2026, 1, 9), "M", bars(109.0, 109.0))]
        self.assertIsNone(bouw_dagen(ruwe, KAL, STRAT)[1].rod)


class Test02FilterGeenVooruitkijken(unittest.TestCase):
    def test_mediaan_alleen_vorige_60_dagen(self):
        h = historie(70, rod=0.001)
        # de oudste 10 dagen zijn enorm: die mogen niet meetellen; vandaag zelf ook niet
        for x in h[:10]:
            x.rod = 0.05
        vandaag = Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=0.0011)
        b = beslis(vandaag, h, STRAT, "A")
        self.assertAlmostEqual(b.mediaan, 0.001)
        self.assertTrue(b.is_trade)
        vandaag.rod = 0.0009
        self.assertEqual(beslis(vandaag, h, STRAT, "A").reden, FILTER_ZWAK)
        vandaag.rod = 0.001   # gelijk aan de mediaan is niet groter
        self.assertEqual(beslis(vandaag, h, STRAT, "A").reden, FILTER_ZWAK)

    def test_vandaag_telt_niet_mee(self):
        h = historie(60, rod=0.001)
        vandaag = Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=0.9)
        self.assertAlmostEqual(beslis(vandaag, h, STRAT, "A").mediaan, 0.001)
        self.assertEqual(len(h), 60)

    def test_te_weinig_historie(self):
        vandaag = Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=0.01)
        self.assertEqual(beslis(vandaag, historie(59), STRAT, "A").reden, TE_WEINIG_HISTORIE)


class Test03Richting(unittest.TestCase):
    def test_long_short_geen(self):
        h = historie(60, rod=0.0001)
        for rod, verwacht in ((0.002, 1), (-0.002, -1)):
            b = beslis(Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=rod), h, STRAT, "A")
            self.assertEqual(b.richting, verwacht)
        b = beslis(Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=0.0), h, STRAT, "C")
        self.assertEqual(b.reden, GEEN_RICHTING)
        b = beslis(Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=-0.002), h, STRAT, "B")
        self.assertEqual(b.richting, 1)   # benchmark B is altijd long


class Test04Stop(unittest.TestCase):
    def test_stop_hele_ticks_minimaal_4(self):
        for gem, verwacht in ((2, 4), (3, 5), (4, 6), (5, 8), (7, 11)):   # 1,5 x 3 = 4,5 -> 5 ; 1,5 x 5 = 7,5 -> 8
            b = beslis(Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=0.01), historie(60, beweging=gem), STRAT, "A")
            self.assertEqual(b.stop_ticks, verwacht, "gemiddeld %s ticks" % gem)
        h = historie(60, beweging=4)
        for i, x in enumerate(h[-20:]):
            x.beweging = 3 if i % 2 else 4      # gemiddelde 3,5 -> 5,25 -> 5
        self.assertEqual(beslis(Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=0.01), h, STRAT, "A").stop_ticks, 5)

    def test_stop_prijs(self):
        b = beslis(Dag(datum=dt.date(2026, 1, 1), signaal=110.0, rod=0.01), historie(60, beweging=4), STRAT, "A")
        self.assertEqual((b.limiet, b.stop_ticks), (110.0, 6))


class Test05Positiegrootte(unittest.TestCase):
    def test_contracten(self):
        self.assertEqual(contracten(4, STRAT), (3, ""))
        self.assertEqual(contracten(6, STRAT), (2, ""))
        self.assertEqual(contracten(7, STRAT), (1, ""))
        self.assertEqual(contracten(13, STRAT), (0, STOP_TE_GROOT))
        self.assertEqual(contracten(2, STRAT)[0], 3)   # nooit meer dan 3

    def test_halveren(self):
        self.assertEqual(contracten(4, STRAT, afstand_tot_bodem=599), (1, ""))   # 3 -> 1
        self.assertEqual(contracten(6, STRAT, afstand_tot_bodem=500), (1, ""))   # 2 -> 1
        self.assertEqual(contracten(7, STRAT, afstand_tot_bodem=500), (0, GEHALVEERD_NUL))
        self.assertEqual(contracten(4, STRAT, afstand_tot_bodem=600), (3, ""))   # precies 600 is niet < 600


def verlies_dagen(start, n):
    """n opeenvolgende handelsdagen (vanaf start) met een long-signaal dat op de stop eindigt."""
    out, d = [], start
    while len(out) < n:
        if KAL.is_handelsdag(d) and not KAL.redenen_geen_trade(d):
            b = bars_lijn("14:00", "15:00", 110.0)
            b["14:30"] = (110.0, 110.0, 110.0 - 2 * TICK, 110.0 - 2 * TICK)   # limiet gevuld (doorbraak 2 ticks)
            b["14:31"] = (110.0 - 2 * TICK, 110.0 - 2 * TICK, 110.0 - 8 * TICK, 110.0 - 8 * TICK)  # stop 6 ticks geraakt
            out.append(Dag(datum=d, contract="Z", signaal=110.0, slot=110.0, rod=0.01, beweging=4, bars=b))
        d += dt.timedelta(days=1)
    return out


class Test19WeekstopEnEenTradePerDag(unittest.TestCase):
    def test_weekstop(self):
        h = historie(60, rod=0.0001, beweging=4, start=dt.date(2026, 6, 1))
        dagen = h + verlies_dagen(dt.date(2026, 9, 21), 5)   # ma 21 t/m vr 25 sep 2026
        uitk = [u for u in run_variant(dagen, STRAT, FIRM, "A")[0] if u["datum"] >= dt.date(2026, 9, 21)]
        statussen = [u["status"] for u in uitk]
        # verlies per trade: 2 contracten x (6 stop + 1 slippage) x $15,625 + kosten = $226,24 -> na 4 dagen -$905
        self.assertEqual(statussen, ["gevuld", "gevuld", "gevuld", "gevuld", WEEKSTOP])
        self.assertAlmostEqual(uitk[0]["trade"]["netto"], -(2 * 7 * 15.625 + 2 * 3.62))

    def test_weekstop_reset_volgende_week(self):
        h = historie(60, rod=0.0001, beweging=4, start=dt.date(2026, 6, 1))
        dagen = h + verlies_dagen(dt.date(2026, 9, 21), 6)   # 6e dag = maandag 28 sep
        uitk = run_variant(dagen, STRAT, FIRM, "A")[0]
        self.assertEqual(uitk[-1]["status"], "gevuld")

    def test_max_een_trade_per_dag(self):
        h = historie(60, rod=0.0001, beweging=4, start=dt.date(2026, 6, 1))
        dagen = h + verlies_dagen(dt.date(2026, 9, 21), 1)
        uitk = run_variant(dagen, STRAT, FIRM, "A")[0]
        per_dag = {}
        for u in uitk:
            per_dag[u["datum"]] = per_dag.get(u["datum"], 0) + (1 if u["trade"] else 0)
        self.assertLessEqual(max(per_dag.values()), 1)


if __name__ == "__main__":
    unittest.main()
