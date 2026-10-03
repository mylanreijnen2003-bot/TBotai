"""Strategieën D, E en controle R, het gat over de stop en het dagrapport."""
import datetime as dt
import unittest

from bot_mgc.tests.hulp import FIRM, KAL, STRAT, TijdelijkeMap, bars_lijn, historie
from bot_mgc.dagrapport import schrijf_dagrapport
from bot_mgc.fills import simuleer_dag
from bot_mgc.strategie import (FILTER_ZWAK, GEEN_OCHTEND, SIGNALEN_ONEENS, TE_WEINIG_HISTORIE, Dag, beslis, bouw_dagen,
                               willekeurige_richting)

P = 2000.0


def met_onfh(h, onfh):
    for i, x in enumerate(h):
        x.onfh = onfh if i % 2 else -onfh
    return h


def vandaag(rod, onfh, datum=dt.date(2026, 1, 1)):
    return Dag(datum=datum, signaal=P, rod=rod, onfh=onfh)


class TestD(unittest.TestCase):
    def test_richting_en_filter_op_ochtend(self):
        h = met_onfh(historie(60, rod=0.001), 0.002)
        b = beslis(vandaag(-0.01, 0.003), h, STRAT, "D")      # ROD short, ochtend long: D volgt de ochtend
        self.assertTrue(b.is_trade)
        self.assertEqual(b.richting, 1)
        self.assertAlmostEqual(b.mediaan, 0.002)
        self.assertEqual(beslis(vandaag(0.01, 0.002), h, STRAT, "D").reden, FILTER_ZWAK)

    def test_geen_ochtenddata(self):
        h = met_onfh(historie(60), 0.002)
        self.assertEqual(beslis(vandaag(0.01, None), h, STRAT, "D").reden, GEEN_OCHTEND)
        h[5].onfh = None   # dag zonder ochtendkoers telt niet mee voor het D-filter: maar 59 over
        self.assertEqual(beslis(vandaag(0.01, 0.01), h, STRAT, "D").reden, TE_WEINIG_HISTORIE)

    def test_onfh_uit_data(self):
        def bars(och, sig, slot):
            b = bars_lijn("12:30", "13:30", sig)
            b.update(bars_lijn("08:20", "08:50", och))
            b["13:29"] = (slot,) * 4
            return b
        ruwe = [(dt.date(2026, 1, 8), "G", bars(1990.0, 1999.0, 2000.0)), (dt.date(2026, 1, 9), "G", bars(2010.0, 2004.0, 2001.0))]
        d = bouw_dagen(ruwe, KAL, STRAT)[1]
        self.assertAlmostEqual(d.onfh, 2010.0 / 2000.0 - 1)
        self.assertAlmostEqual(d.rod, 2004.0 / 2000.0 - 1)


class TestE(unittest.TestCase):
    def test_alleen_als_eens(self):
        h = met_onfh(historie(60), 0.002)
        b = beslis(vandaag(0.0001, 0.0001), h, STRAT, "E")     # geen filter: ook kleine signalen
        self.assertEqual((b.is_trade, b.richting), (True, 1))
        self.assertEqual(beslis(vandaag(-0.002, -0.001), h, STRAT, "E").richting, -1)
        self.assertEqual(beslis(vandaag(0.002, -0.001), h, STRAT, "E").reden, SIGNALEN_ONEENS)


class TestR(unittest.TestCase):
    def test_zelfde_dagen_als_a_vaste_munt(self):
        h = historie(60, rod=0.001)
        dagen = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(200)]
        richtingen = []
        for d in dagen:
            a = beslis(vandaag(0.002, None, d), h, STRAT, "A")
            r = beslis(vandaag(0.002, None, d), h, STRAT, "R")
            self.assertEqual(a.is_trade, r.is_trade)
            self.assertEqual(r.richting, willekeurige_richting(d, STRAT))
            richtingen.append(r.richting)
            self.assertFalse(beslis(vandaag(0.0005, None, d), h, STRAT, "R").is_trade)   # filter zwak: ook R niet
        self.assertTrue(70 < richtingen.count(1) < 130)        # ongeveer de helft long
        self.assertEqual(richtingen, [willekeurige_richting(d, STRAT) for d in dagen])   # elke keer hetzelfde


class TestGatOverStop(unittest.TestCase):
    def test_fill_op_opening_bij_gat(self):
        b = bars_lijn(prijs=P)
        b["13:10"] = (P - 9.0, P - 8.0, P - 10.0, P - 9.0)     # opent al 9 punten lager; stop lag op 1994,1
        sim = simuleer_dag(b, 1, 6.0, 3, STRAT)
        self.assertEqual(sim.uitstapreden, "stop")
        self.assertAlmostEqual(sim.uitstap, P - 9.0 - 0.1)
        b = bars_lijn(prijs=P)
        b["13:10"] = (P + 9.0, P + 10.0, P + 8.0, P + 9.0)     # short: gat omhoog
        self.assertAlmostEqual(simuleer_dag(b, -1, 6.0, 3, STRAT).uitstap, P + 9.0 + 0.1)


class TestDagrapport(unittest.TestCase):
    def test_forward_oordeel(self):
        from bot_mgc.dagrapport import forward_oordeel
        start = dt.date(2027, 1, 1)

        def reeks(n, rs):
            return [{"datum": start + dt.timedelta(days=i), "netto": 160 * rs[i % len(rs)], "R": rs[i % len(rs)], "mae": 0}
                    for i in range(n)]
        trades = {"A": reeks(320, [1.0, -0.6]), "B": reeks(320, [0.5, -0.6]), "R": reeks(320, [0.4, -0.6])}
        status, lijst = forward_oordeel(trades, STRAT, "A")
        self.assertEqual(status, "GO", lijst)
        self.assertEqual(forward_oordeel(dict(trades, A=trades["A"][:299]), STRAT, "A")[0], "loopt")
        trades["A"] = reeks(320, [0.6, -0.6])               # expectancy 0: geen voorsprong
        self.assertEqual(forward_oordeel(trades, STRAT, "A")[0], "NO-GO")

    def test_dagrapport_geen_handelsdag(self):
        with TijdelijkeMap() as m:
            pad = schrijf_dagrapport(dt.date(2026, 11, 26), "mgc-paper", m, STRAT, FIRM, KAL)
            self.assertIn("beursfeestdag", pad.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
