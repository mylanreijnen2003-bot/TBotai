"""Kalender, DST, roll en rekenwerk (plan §11 tests 9-12)."""
import datetime as dt
import unittest

from bot_zn.tests.hulp import FIRM, KAL, STRAT, bars_lijn, historie
from bot_zn.backtest import run_variant
from bot_zn.fills import simuleer_dag
from bot_zn.journal_zn import is_dst_mismatch
from bot_zn.kalender_zn import FOMC, KERST, NOTULEN, ROLL_DAG, VERVROEGD, vergelijk_rolls_v0
from bot_zn.strategie import Dag, beslis
from bot_zn.tijd import TICK, et, in_32ste, nl_tijd


def dag(d, rod=0.01):
    return Dag(datum=d, signaal=110.0, rod=rod, redenen=KAL.redenen_geen_trade(d), veiling=KAL.is_veilingdag(d))


class Test09NietHandeldagen(unittest.TestCase):
    def test_geen_trade(self):
        gevallen = {
            dt.date(2026, 10, 28): FOMC,          # FOMC-besluit
            dt.date(2026, 10, 7): NOTULEN,        # notulen
            dt.date(2025, 11, 28): VERVROEGD,     # dag na Thanksgiving
            dt.date(2026, 12, 28): KERST,         # kerstperiode 24 dec - 2 jan
            dt.date(2027, 1, 2): KERST,
            dt.date(2026, 11, 20): ROLL_DAG,      # eerste dag op het maart-contract
        }
        h = historie(60, rod=0.0001)
        for d, reden in gevallen.items():
            b = beslis(dag(d), h, STRAT, "A")
            self.assertFalse(b.is_trade, d)
            self.assertIn(reden, b.reden, d)

    def test_weekend_en_feestdag(self):
        h = historie(60, rod=0.0001)
        self.assertIn("weekend", beslis(dag(dt.date(2026, 10, 3)), h, STRAT, "A").reden)
        self.assertIn("feestdag", beslis(dag(dt.date(2026, 11, 26)), h, STRAT, "A").reden)

    def test_veilingdag_wel(self):
        d = dt.date(2026, 9, 10)            # 30-jaars veiling om 13:00 ET
        self.assertTrue(KAL.is_veilingdag(d))
        self.assertTrue(beslis(dag(d), historie(60, rod=0.0001), STRAT, "A").is_trade)


class Test10DST(unittest.TestCase):
    def test_mismatchweek_okt_2026(self):
        for dagnr in range(26, 31):
            d = dt.date(2026, 10, dagnr)
            self.assertEqual(et(d, "14:30").strftime("%H:%M %Z"), "14:30 EDT")
            self.assertEqual(nl_tijd(d, "14:30"), "19:30")     # 1 uur eerder dan normaal
            self.assertTrue(is_dst_mismatch(d))
        self.assertEqual(nl_tijd(dt.date(2026, 10, 22), "14:30"), "20:30")
        self.assertEqual(nl_tijd(dt.date(2026, 11, 3), "14:30"), "20:30")
        self.assertFalse(is_dst_mismatch(dt.date(2026, 11, 3)))
        self.assertEqual(nl_tijd(dt.date(2027, 3, 16), "14:30"), "19:30")   # maart-mismatch


class Test11Rekenen(unittest.TestCase):
    def test_tick_kosten_r(self):
        self.assertEqual(STRAT["instrument"]["tick_waarde"], 15.625)
        self.assertAlmostEqual(TICK * STRAT["instrument"]["punt_waarde"], 15.625)
        b = bars_lijn(prijs=110.0)
        b["14:30"] = (110.0, 110.0, 110.0 - TICK, 110.0)
        b["14:59"] = (110.0 + 9 * TICK,) * 4      # uitstap op 8 ticks winst (open − 1 tick)
        r = simuleer_dag(b, 1, 110.0, 6, 2, STRAT).resultaat(STRAT["kosten_per_contract_rt"])
        self.assertAlmostEqual(r["bruto"], 8 * 15.625 * 2)
        self.assertAlmostEqual(r["kosten"], 2 * 3.62)
        self.assertAlmostEqual(r["risico"], 6 * 15.625 * 2)
        self.assertAlmostEqual(r["R"], (250.0 - 7.24) / 187.5)

    def test_32ste(self):
        self.assertEqual(in_32ste(110.5), "110-16")
        self.assertEqual(in_32ste(110.515625), "110-16+")
        self.assertEqual(in_32ste(109.984375), "109-31+")
        self.assertEqual(in_32ste(111.0), "111-00")


class Test12Roll(unittest.TestCase):
    def test_rolldatums(self):
        # dec 2026: laatste handelsdag nov = ma 30 nov; 5 handelsdagen terug (Thanksgiving telt niet) = vr 20 nov
        self.assertEqual(KAL.roll_datum(2026, 12), dt.date(2026, 11, 20))
        self.assertEqual(KAL.roll_datum(2027, 3), dt.date(2027, 2, 19))
        self.assertEqual(KAL.contract_voor(dt.date(2026, 11, 19)), (2026, 12))
        self.assertEqual(KAL.contract_voor(dt.date(2026, 11, 20)), (2027, 3))
        self.assertTrue(KAL.is_roll_dag(dt.date(2026, 11, 20)))
        self.assertFalse(KAL.is_roll_dag(dt.date(2026, 11, 23)))

    def test_afwijking_v0_wordt_gemeld(self):
        ok = vergelijk_rolls_v0(KAL, [dt.date(2026, 11, 23)], 3)        # 1 handelsdag verschil
        self.assertEqual(ok, [])
        fout = vergelijk_rolls_v0(KAL, [dt.date(2026, 11, 30)], 3)      # 5 handelsdagen verschil
        self.assertEqual(len(fout), 1)
        self.assertEqual(fout[0]["regel_roll"], dt.date(2026, 11, 20))

    def test_backtest_rolldag_uit_v0(self):
        """In de backtest is de eerste dag op een nieuw .v.0-contract de roll_dag (geen trade)."""
        d = dt.date(2026, 9, 22)
        b = bars_lijn("14:00", "15:00", 110.0)
        h = historie(60, rod=0.0001, start=dt.date(2026, 6, 1))
        roll = Dag(datum=d, contract="Y", signaal=110.0, slot=110.0, rod=0.01, beweging=4, bars=b,
                   redenen=KAL.redenen_geen_trade(d, roll_dag=True))
        u = run_variant(h + [roll], STRAT, FIRM, "A")[0][-1]
        self.assertEqual(u["status"], ROLL_DAG)


if __name__ == "__main__":
    unittest.main()
