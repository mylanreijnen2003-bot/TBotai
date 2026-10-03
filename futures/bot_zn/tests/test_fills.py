"""Fills: limiet-doorbraak, fill en stop in dezelfde bar, tijdsuitstap (plan §11 tests 6-8)."""
import unittest

from bot_zn.tests.hulp import STRAT, bars_lijn
from bot_zn.fills import GESLOTEN, NIET_GEVULD, TradeSim, simuleer_dag
from bot_zn.tijd import TICK

L = 110.0


class Test06LimietFill(unittest.TestCase):
    def test_alleen_gevuld_bij_doorbraak_van_1_tick(self):
        b = bars_lijn(prijs=L + 2 * TICK)
        b["14:31"] = (L + TICK, L + TICK, L, L)            # raakt de limiet precies: NIET gevuld
        sim = simuleer_dag(b, 1, L, 6, 2, STRAT)
        self.assertEqual(sim.status, NIET_GEVULD)
        b["14:32"] = (L, L, L - TICK, L)                   # doorbraak van 1 tick: gevuld op de limiet
        sim = simuleer_dag(b, 1, L, 6, 2, STRAT)
        self.assertTrue(sim.gevuld)
        self.assertEqual((sim.instap, sim.instap_bar), (L, "14:32"))

    def test_short_spiegelbeeld(self):
        b = bars_lijn(prijs=L - 2 * TICK)
        b["14:33"] = (L, L + TICK, L, L)
        sim = simuleer_dag(b, -1, L, 6, 1, STRAT)
        self.assertEqual((sim.instap, sim.instap_bar), (L, "14:33"))

    def test_niet_gevuld_voor_1435(self):
        b = bars_lijn(prijs=L + 3 * TICK)
        b["14:35"] = (L, L, L - 5 * TICK, L)               # doorbraak pas om 14:35: te laat
        sim = simuleer_dag(b, 1, L, 6, 2, STRAT)
        self.assertEqual(sim.status, NIET_GEVULD)
        self.assertIsNone(sim.resultaat(3.62))

    def test_stress_vraagt_2_ticks(self):
        b = bars_lijn(prijs=L + 2 * TICK)
        b["14:31"] = (L, L, L - TICK, L)
        self.assertTrue(simuleer_dag(b, 1, L, 6, 2, STRAT).gevuld)
        self.assertFalse(simuleer_dag(b, 1, L, 6, 2, STRAT, stress=True).gevuld)


class Test07FillEnStopZelfdeBar(unittest.TestCase):
    def test_eerst_fill_dan_stop(self):
        b = bars_lijn(prijs=L + 2 * TICK)
        b["14:30"] = (L + 2 * TICK, L + 2 * TICK, L - 7 * TICK, L - 6 * TICK)   # door limiet én stop (6 ticks)
        sim = simuleer_dag(b, 1, L, 6, 2, STRAT)
        self.assertEqual((sim.status, sim.uitstapreden, sim.instap_bar, sim.uitstap_bar_tijd), (GESLOTEN, "stop", "14:30", "14:30"))
        self.assertAlmostEqual(sim.uitstap, L - 7 * TICK)    # stop − 1 tick
        r = sim.resultaat(3.62)
        self.assertAlmostEqual(r["netto"], -(7 * 15.625 * 2) - 2 * 3.62)


class Test08Tijdsuitstap(unittest.TestCase):
    def test_uitstap_1459_open_min_1_tick(self):
        b = bars_lijn(prijs=L + TICK)
        b["14:30"] = (L, L, L - TICK, L)
        b["14:59"] = (L + 10 * TICK, L + 11 * TICK, L + 9 * TICK, L + 10 * TICK)
        sim = simuleer_dag(b, 1, L, 6, 2, STRAT)
        self.assertEqual((sim.uitstapreden, sim.uitstap_bar_tijd), ("tijd", "14:59"))
        self.assertAlmostEqual(sim.uitstap, L + 9 * TICK)

    def test_stop_niet_meer_in_1459_bar(self):
        b = bars_lijn(prijs=L)
        b["14:30"] = (L, L, L - TICK, L)
        b["14:59"] = (L, L, L - 20 * TICK, L - 20 * TICK)  # na 14:59:00 is de positie al dicht
        sim = simuleer_dag(b, 1, L, 6, 2, STRAT)
        self.assertEqual(sim.uitstapreden, "tijd")

    def test_geen_instap_na_143459(self):
        sim = TradeSim(1, L, 6, 2, STRAT)
        sim.bar("14:35", L, L, L - 10 * TICK, L)
        self.assertEqual(sim.status, NIET_GEVULD)
        self.assertFalse(sim.gevuld)


if __name__ == "__main__":
    unittest.main()
