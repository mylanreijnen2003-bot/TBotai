"""Dagelijkse fronttest met alle strategieën, tegen de nep-broker (nooit orders)."""
import csv
import datetime as dt
import json
import random
import unittest

from bot_zn.tests.hulp import KAL, STRAT, TijdelijkeMap
from bot_zn.dagelijks import Fronttest
from bot_zn.fills import simuleer_dag
from bot_zn.journal_zn import lees
from bot_zn.multi import (Geen, MDag, Signaal, bouw_mdagen, load_strategieen, maak_strategie, simuleer, speel_dag)
from bot_zn.nepbroker import NepBroker
from bot_zn.strategie import beslis, bouw_dagen, contracten
from bot_zn.tijd import ET, TICK

ALG = load_strategieen()
CID = "CON.F.US.TYA.Z26"


def nep_bars(van, tot, seed=3):
    """{datum: {'HH:MM': (o,h,l,c)}} 08:00-15:15 ET, willekeurige wandeling met wat trend in het laatste half uur."""
    rng = random.Random(seed)
    p, out, d = 112.0, {}, van
    while d <= tot:
        if KAL.is_handelsdag(d):
            trend = rng.gauss(0, 1)
            bars = {}
            for i in range(0, 7 * 60 + 16):
                t = "%02d:%02d" % (8 + i // 60, i % 60)
                drift = 0.4 * trend * TICK if t >= "14:30" else 0.0
                c = round((p + drift + rng.gauss(0, 0.8) * TICK) / TICK) * TICK
                bars[t] = (p, max(p, c) + rng.randint(0, 1) * TICK, min(p, c) - rng.randint(0, 1) * TICK, c)
                p = c
            out[d] = bars
            p += rng.gauss(0, 6) * TICK
        d += dt.timedelta(days=1)
    return out


def broker_met(bars_per_dag):
    b = NepBroker(faal_bij_order=True)
    alle = {}
    for d, bars in bars_per_dag.items():
        for t, v in bars.items():
            h, m = (int(x) for x in t.split(":"))
            alle[dt.datetime(d.year, d.month, d.day, h, m, tzinfo=ET)] = v
    b.zet_bars(CID, alle)
    return b


def nu(d, hms="21:00:00"):
    h, m, s = (int(x) for x in hms.split(":"))
    return dt.datetime(d.year, d.month, d.day, h, m, s, tzinfo=ET)


class TestFronttest(unittest.TestCase):
    def test_eerste_run_alleen_laatste_dag_en_geen_orders(self):
        data = nep_bars(dt.date(2026, 5, 1), dt.date(2026, 10, 16))
        with TijdelijkeMap() as m:
            b = broker_met(data)
            ft = Fronttest(b, m, {"data_live": False}, log=lambda *_: None)
            pad = ft.draai(nu=nu(dt.date(2026, 10, 16)))
            self.assertEqual(b.order_aanroepen, 0)
            with open(m / "logs" / "fronttest_signalen.csv", newline="", encoding="utf-8") as f:
                rijen = list(csv.DictReader(f))
            self.assertEqual({r["strategie"] for r in rijen}, set(ALG["strategieen"]))
            self.assertEqual({r["datum"] for r in rijen}, {"2026-10-16"})
            self.assertTrue(pad.exists())
            self.assertIn("ZN-fronttest", pad.read_text(encoding="utf-8"))
            status = json.loads((m / "data" / "fronttest_status.json").read_text())
            self.assertEqual(status["laatst_verwerkt"], "2026-10-16")

    def test_inhalen_en_niet_dubbel(self):
        data = nep_bars(dt.date(2026, 4, 1), dt.date(2026, 10, 30))
        with TijdelijkeMap() as m:
            b = broker_met(data)
            ft = Fronttest(b, m, {}, log=lambda *_: None)
            ft.draai(nu=nu(dt.date(2026, 10, 14)))
            # pc een week uit: de volgende run haalt alles in
            ft = Fronttest(b, m, {}, log=lambda *_: None)
            ft.draai(nu=nu(dt.date(2026, 10, 23)))
            ft.draai(nu=nu(dt.date(2026, 10, 23)))        # nog een keer: niets dubbel
            with open(m / "logs" / "fronttest_signalen.csv", newline="", encoding="utf-8") as f:
                rijen = list(csv.DictReader(f))
            dagen = sorted({r["datum"] for r in rijen})
            self.assertEqual(dagen, ["2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20",
                                     "2026-10-21", "2026-10-22", "2026-10-23"])
            self.assertEqual(len(rijen), len(dagen) * len(ALG["strategieen"]))
            trades = [r for r in lees(m / "journal_bot.csv") if r["account"] == "zn-paper"]
            self.assertEqual(len(trades), sum(1 for r in rijen if r["status"] == "gevuld"))
            self.assertTrue(all(r["setup"].startswith("ZN-") for r in trades))

    def test_voor_het_slot_nog_gisteren(self):
        with TijdelijkeMap() as m:
            ft = Fronttest(NepBroker(faal_bij_order=True), m, {}, log=lambda *_: None)
            self.assertEqual(ft.laatste_complete_dag(nu(dt.date(2026, 10, 16), "15:00:00")), dt.date(2026, 10, 15))
            self.assertEqual(ft.laatste_complete_dag(nu(dt.date(2026, 10, 16), "15:30:00")), dt.date(2026, 10, 16))
            self.assertEqual(ft.laatste_complete_dag(nu(dt.date(2026, 10, 18), "12:00:00")), dt.date(2026, 10, 16))


class TestZelfdeAlsStrategieA(unittest.TestCase):
    def test_multi_A_geeft_dezelfde_trades(self):
        data = nep_bars(dt.date(2025, 1, 2), dt.date(2026, 9, 30), seed=9)
        ruwe = [(d, "Z", b) for d, b in sorted(data.items())]
        oud = bouw_dagen(ruwe, KAL, STRAT, roll_dagen=set())
        nieuw = bouw_mdagen(ruwe, KAL, roll_dagen=set())
        s = maak_strategie("A", ALG, KAL)
        hist, gelijk, trades = [], 0, 0
        for do, dn in zip(oud, nieuw):
            b = beslis(do, hist, STRAT, "A")
            u = speel_dag(s, dn, ALG)
            if b.is_trade:
                n, _ = contracten(b.stop_ticks, STRAT)
                if n:
                    sim = simuleer_dag(do.bars, b.richting, b.limiet, b.stop_ticks, n, STRAT)
                    if sim.gevuld:
                        trades += 1
                        self.assertIsNotNone(u["trade"], do.datum)
                        self.assertAlmostEqual(u["trade"]["instap"], sim.instap)
                        self.assertAlmostEqual(u["trade"]["uitstap"], sim.uitstap)
                        self.assertAlmostEqual(u["trade"]["netto"], sim.resultaat(3.62)["netto"])
                        gelijk += 1
                        continue
            self.assertIsNone(u["trade"], do.datum)
            if do.geldig:
                hist.append(do)
            s.na_dag(dn)
        self.assertGreater(trades, 20)
        self.assertEqual(gelijk, trades)


def dag_met(bars, datum=dt.date(2026, 10, 14), veiling="", release="", vorige=None):
    return MDag(datum=datum, contract="Z", bars=bars, veiling=veiling, release=release, vorige=vorige)


def vlak(prijs=112.0, van="08:00", tot="15:15"):
    out, t = {}, dt.datetime(2000, 1, 1, int(van[:2]), int(van[3:]))
    while t.strftime("%H:%M") <= tot:
        out[t.strftime("%H:%M")] = (prijs,) * 4
        t += dt.timedelta(minutes=1)
    return out


class TestStrategieen(unittest.TestCase):
    def test_veiling_D(self):
        s = maak_strategie("D", ALG, KAL)
        b = vlak()
        b["14:00"] = (112.0, 112.2, 112.0, 112.2)
        b["14:25"] = (112.1875,) * 4
        u = speel_dag(s, dag_met(b, veiling="10-Year Note"), ALG)
        self.assertEqual((u["trade"]["richting"], u["trade"]["instap_bar"], u["trade"]["uitstap_bar"]), (1, "13:01", "14:25"))
        self.assertEqual(speel_dag(s, dag_met(vlak(), veiling="2-Year Note"), ALG)["reden"], "geen_veiling")
        self.assertEqual(speel_dag(s, dag_met(vlak()), ALG)["reden"], "geen_veiling")

    def test_maandeinde_C(self):
        s = maak_strategie("C", ALG, KAL)
        self.assertEqual(speel_dag(s, dag_met(vlak(), datum=dt.date(2026, 10, 30)), ALG)["status"], "gevuld")   # laatste werkdag okt
        self.assertEqual(speel_dag(s, dag_met(vlak(), datum=dt.date(2026, 10, 28)), ALG)["status"], "gevuld")   # 3e laatste
        self.assertEqual(speel_dag(s, dag_met(vlak(), datum=dt.date(2026, 10, 27)), ALG)["reden"], "geen_maandeinde")

    def test_drift_E_alleen_op_releasedag(self):
        s = maak_strategie("E", ALG, KAL)
        for i in range(20):
            s.hist.append(0.0001)
        b = vlak()
        for k in ("09:30", "09:40", "09:50", "09:58"):
            b[k] = (112.0, 112.1, 112.0, 112.1)
        self.assertEqual(speel_dag(s, dag_met(b), ALG)["reden"], "geen_release")
        u = speel_dag(s, dag_met(b, release="ISM Services"), ALG)
        self.assertEqual((u["trade"]["richting"], u["trade"]["instap_bar"], u["trade"]["uitstap_bar"]), (1, "09:59", "10:02"))

    def test_orb_G_breakout_en_beide_kanten(self):
        s = maak_strategie("G", ALG, KAL)
        b = vlak()
        b["08:30"] = (112.0, 112.05, 111.97, 112.0)           # range 111,97 - 112,05
        b["09:10"] = (112.0, 112.1, 112.0, 112.1)             # breakout omhoog
        u = speel_dag(s, dag_met(b), ALG)
        self.assertEqual(u["trade"]["richting"], 1)
        b["09:10"] = (112.0, 112.1, 111.9, 112.0)             # beide kanten in één bar: conservatief verlies
        u = speel_dag(s, dag_met(b), ALG)
        self.assertEqual(u["trade"]["uitstapreden"], "stop")

    def test_reversal_H(self):
        s = maak_strategie("H", ALG, KAL)
        for i in range(61):
            s.hist.append(0.0002)
        gisteren = dag_met(vlak(), datum=dt.date(2026, 10, 13))
        gisteren.r_lh = 0.002                                   # gisteren sterk omhoog in het laatste half uur
        u = speel_dag(s, dag_met(vlak(), vorige=gisteren), ALG)
        self.assertEqual((u["trade"]["richting"], u["trade"]["instap_bar"], u["trade"]["uitstap_bar"]), (-1, "08:20", "10:00"))

    def test_geen_vooruitkijken(self):
        """Een strategie krijgt alleen bars vóór zijn beslismoment."""
        gezien = {}

        class Spion(type(maak_strategie("C", ALG, KAL))):
            def signaal(self, dag, bars_tot):
                gezien["max"] = max(bars_tot)
                raise Geen("test")
        s = Spion("C", ALG["strategieen"]["C"], dict(ALG["strategieen"]["C"]["standaard"]), ALG, KAL)
        speel_dag(s, dag_met(vlak()), ALG)
        self.assertEqual(gezien["max"], "08:19")

    def test_fill_limiet_doorbraak(self):
        b = vlak()
        b["14:31"] = (112.0, 112.0, 112.0 - TICK, 112.0)
        sig = Signaal(1, "limiet", "14:30", "14:34", "14:59", 6, prijs=112.0)
        self.assertIsNotNone(simuleer(sig, b, 1, ALG))
        b["14:31"] = (112.0,) * 4
        self.assertIsNone(simuleer(sig, b, 1, ALG))


if __name__ == "__main__":
    unittest.main()
