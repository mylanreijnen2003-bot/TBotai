"""Fills, kalender, DST, kosten en roll (plan §10 tests 6, 8, 9, 10, 11, 12)."""
import datetime as dt
import unittest

from bot_mgc.tests.hulp import FIRM, KAL, STRAT, bars_lijn, historie
from bot_mgc.backtest import run_variant
from bot_mgc.fills import GESLOTEN, TE_LAAT, TradeSim, simuleer_dag
from bot_mgc.journal_mgc import is_dst_mismatch
from bot_mgc.kalender_mgc import FEESTDAG, KERST, ROLL_DAG, VERVROEGD, vergelijk_rolls_v0
from bot_mgc.strategie import Dag, beslis
from bot_mgc.tijd import et, nl_tijd

P = 2000.0


def dag(d, rod=0.01):
    return Dag(datum=d, signaal=P, rod=rod, redenen=KAL.redenen_geen_trade(d), fomc=KAL.is_fomc(d))


class Test06InstapEnTijdsuitstap(unittest.TestCase):
    def test_instap_na_1302_geen_trade(self):
        b = {k: v for k, v in bars_lijn(prijs=P).items() if k >= "13:02"}   # geen koers in 13:00 en 13:01
        sim = simuleer_dag(b, 1, 6.0, 3, STRAT)
        self.assertEqual(sim.status, TE_LAAT)
        self.assertFalse(sim.gevuld)

    def test_instap_op_1301_mag_nog(self):
        b = {k: v for k, v in bars_lijn(prijs=P).items() if k >= "13:01"}
        sim = simuleer_dag(b, 1, 6.0, 3, STRAT)
        self.assertEqual(sim.instap_bar, "13:01")

    def test_tijdsuitstap_1329(self):
        b = bars_lijn(prijs=P)
        b["13:29"] = (P + 5, P + 6, P + 4, P + 5)
        sim = simuleer_dag(b, 1, 6.0, 3, STRAT)
        self.assertEqual((sim.status, sim.uitstapreden, sim.uitstap_bar_tijd), (GESLOTEN, "tijd", "13:29"))
        self.assertAlmostEqual(sim.uitstap, P + 4.9)          # opening 13:29-bar − 1 tick
        self.assertAlmostEqual(sim.instap, P + 0.1)           # opening 13:00-bar + 1 tick

    def test_short_spiegelbeeld(self):
        b = bars_lijn(prijs=P)
        b["13:29"] = (P - 5, P - 4, P - 6, P - 5)
        sim = simuleer_dag(b, -1, 6.0, 3, STRAT)
        self.assertAlmostEqual(sim.instap, P - 0.1)
        self.assertAlmostEqual(sim.uitstap, P - 4.9)


class Test08NietHandeldagen(unittest.TestCase):
    def test_geen_trade(self):
        h = historie(60, rod=0.0001)
        for d, reden in {dt.date(2026, 12, 28): KERST, dt.date(2027, 1, 2): KERST, dt.date(2026, 11, 27): VERVROEGD,
                         dt.date(2026, 11, 26): FEESTDAG, dt.date(2026, 4, 3): FEESTDAG,
                         dt.date(2026, 11, 20): ROLL_DAG}.items():
            b = beslis(dag(d), h, STRAT, "A")
            self.assertFalse(b.is_trade, d)
            self.assertIn(reden, b.reden, d)

    def test_fomc_dag_wel(self):
        d = dt.date(2026, 10, 28)
        self.assertTrue(KAL.is_fomc(d))
        self.assertTrue(beslis(dag(d), historie(60, rod=0.0001), STRAT, "A").is_trade)


class Test09DST(unittest.TestCase):
    def test_mismatchweek_okt_2026(self):
        for dagnr in range(26, 31):
            d = dt.date(2026, 10, dagnr)
            self.assertEqual(et(d, "13:00").strftime("%H:%M %Z"), "13:00 EDT")
            self.assertEqual(nl_tijd(d, "13:00"), "18:00")
            self.assertTrue(is_dst_mismatch(d))
        self.assertEqual(nl_tijd(dt.date(2026, 10, 22), "13:00"), "19:00")
        self.assertEqual(nl_tijd(dt.date(2026, 11, 3), "13:30"), "19:30")


class Test10StopInInstapbar(unittest.TestCase):
    def test_stop_in_instapbar(self):
        b = bars_lijn(prijs=P)
        b["13:00"] = (P, P, P - 7, P - 6)            # instap 2000,1; stop 1994,1 wordt in dezelfde bar geraakt
        sim = simuleer_dag(b, 1, 6.0, 3, STRAT)
        self.assertEqual((sim.uitstapreden, sim.instap_bar, sim.uitstap_bar_tijd), ("stop", "13:00", "13:00"))
        self.assertAlmostEqual(sim.uitstap, P + 0.1 - 6.0 - 0.1)   # stop − 1 tick

    def test_stop_later(self):
        b = bars_lijn(prijs=P)
        b["13:20"] = (P, P, P - 6.0, P - 5)
        sim = simuleer_dag(b, 1, 6.0, 3, STRAT)
        self.assertEqual((sim.uitstapreden, sim.uitstap_bar_tijd), ("stop", "13:20"))
        b["13:20"] = (P, P, P - 5.8, P - 5)          # laag 1994,2 > stop 1994,1: niet geraakt
        self.assertEqual(simuleer_dag(b, 1, 6.0, 3, STRAT).uitstapreden, "tijd")


class Test11KostenSlippageR(unittest.TestCase):
    def test_normaal(self):
        b = bars_lijn(prijs=P)
        b["13:29"] = (P + 10, P + 10, P + 10, P + 10)
        r = simuleer_dag(b, 1, 6.0, 3, STRAT).resultaat(STRAT["kosten_per_contract_rt"])
        self.assertAlmostEqual(r["bruto"], (9.9 - 0.1) * 10 * 3)      # 9,8 punten x $10 x 3
        self.assertAlmostEqual(r["kosten"], 3 * 2.42)
        self.assertAlmostEqual(r["risico"], 6.0 * 10 * 3)
        self.assertAlmostEqual(r["R"], (294.0 - 7.26) / 180.0)

    def test_stress(self):
        b = bars_lijn(prijs=P)
        b["13:29"] = (P + 10, P + 10, P + 10, P + 10)
        sim = simuleer_dag(b, 1, 6.0, 3, STRAT, stress=True)
        self.assertAlmostEqual(sim.instap, P + 0.2)
        self.assertAlmostEqual(sim.uitstap, P + 9.8)
        r = sim.resultaat(STRAT["kosten_per_contract_rt"])
        self.assertAlmostEqual(r["bruto"], 9.6 * 10 * 3)
        self.assertEqual(STRAT["instrument"]["tick_waarde"], 1.0)


class Test12Roll(unittest.TestCase):
    def test_rolldatums(self):
        # dec 2026 -> feb 2027: laatste handelsdag nov = ma 30 nov; 5 terug (Thanksgiving telt niet) = vr 20 nov
        self.assertEqual(KAL.roll_datum(2026, 12), dt.date(2026, 11, 20))
        self.assertEqual(KAL.contract_voor(dt.date(2026, 11, 20)), (2027, 2))
        # feb 2027 -> apr 2027: laatste handelsdag jan = vr 29 jan; 5 terug = vr 22 jan
        self.assertEqual(KAL.roll_datum(2027, 2), dt.date(2027, 1, 22))
        self.assertEqual(KAL.contract_voor(dt.date(2027, 1, 21)), (2027, 2))
        self.assertTrue(KAL.is_roll_dag(dt.date(2027, 1, 22)))

    def test_afwijking_v0_gelogd(self):
        self.assertEqual(vergelijk_rolls_v0(KAL, [dt.date(2026, 11, 24)], 3), [])
        fout = vergelijk_rolls_v0(KAL, [dt.date(2026, 11, 30)], 3)
        self.assertEqual((len(fout), fout[0]["regel_roll"]), (1, dt.date(2026, 11, 20)))

    def test_backtest_rolldag_uit_v0(self):
        d = dt.date(2026, 9, 22)
        h = historie(60, rod=0.0001, start=dt.date(2026, 6, 1))
        roll = Dag(datum=d, contract="Y", signaal=P, slot=P, rod=0.01, beweging=4.0, bars=bars_lijn("12:30", "13:30", P),
                   redenen=KAL.redenen_geen_trade(d, roll_dag=True))
        self.assertEqual(run_variant(h + [roll], STRAT, FIRM, "A")[0][-1]["status"], ROLL_DAG)

    def test_tradesim_geen_instap_na_1301_bar(self):
        sim = TradeSim(1, 6.0, 3, STRAT)
        sim.bar("13:02", P, P, P, P)
        self.assertEqual(sim.status, TE_LAAT)


if __name__ == "__main__":
    unittest.main()
