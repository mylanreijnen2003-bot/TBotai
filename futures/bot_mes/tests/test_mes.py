"""Tests MES-bot (plan-MES §10, voor zover van toepassing op de forward test) plus de extra strategieën. Geen netwerk."""
import copy
import datetime as dt
import json
import random
import shutil
import tempfile
import unittest
from pathlib import Path

from bot_mes.forward import ROOT, journal_trades, laad, lees_csv, run
from bot_mes.kalender import contract_code
from bot_mes.kern import contracten, simuleer_trade, vijf_minuten, vwap_reeks
from bot_mes.strategieen import Dag, Rekening, maak_dag, ruis_prijzen, ruis_uit, speel, strategie_a, willekeurige_richting
from bot_mes.yahoo import ticker

STRAT, KAL, FIRM = laad()
D = dt.date(2026, 10, 14)        # gewone woensdag


def minuten(van, tot):
    h, m = (int(x) for x in van.split(":"))
    t = h * 60 + m
    eind = int(tot[:2]) * 60 + int(tot[3:])
    while t <= eind:
        yield "%02d:%02d" % (t // 60, t % 60)
        t += 1


def dag_bars(basis, vijf=None, vol=100.0):
    """1-minuutbars 09:30-15:59. basis = [(van, tot, prijs)], vijf = {'HH:MM': (o, h, l, c)} voor 5-minuutbars:
    minuut 0 maakt het hoog, minuut 1 het laag, minuut 4 het slot."""
    bars = {}
    for van, tot, p in basis:
        for k in minuten(van, tot):
            bars[k] = (p, p, p, p, vol)
    for k5, (o, h, l, c) in (vijf or {}).items():
        ks = list(minuten(k5, k5[:3] + "%02d" % (int(k5[3:]) + 4)))
        bars[ks[0]] = (o, h, o, o, vol)
        bars[ks[1]] = (o, o, l, o, vol)
        bars[ks[2]] = (o, o, o, o, vol)
        bars[ks[3]] = (o, o, o, o, vol)
        bars[ks[4]] = (o, o, o, c, vol)
    return bars


def a_dag(pullback_laag=107.0, trigger_bar="14:55", na=112.0):
    """Long-bias-dag: OR 99-101, de rest rond 106, om 14:40 sluit hij op 110, daarna pullback en trigger."""
    vijf = {"09:30": (100.0, 101.0, 99.0, 100.0), "14:35": (106.0, 108.0, 106.0, 108.0),
            "14:40": (108.0, 110.0, 108.0, 110.0), "14:45": (110.0, 110.0, 108.0, 109.0),
            "14:50": (109.0, 109.0, pullback_laag, 108.5)}
    tb = trigger_bar
    vijf[tb] = (108.5, 111.0, 108.5, 111.0)
    na_trigger = "%s:%02d" % (tb[:2], int(tb[3:]) + 5) if int(tb[3:]) + 5 < 60 else "%02d:00" % (int(tb[:2]) + 1)
    basis = [("09:30", "14:34", 106.0), (na_trigger, "15:59", na)]
    if tb > "14:55":
        basis.append(("14:55", "%s:%02d" % (tb[:2], int(tb[3:]) - 1) if int(tb[3:]) else "14:59", 108.5))
    return dag_bars(basis, vijf)


class TestBouwstenen(unittest.TestCase):
    def test_vwap_or_vijf_minuten(self):
        bars = {"09:30": (10, 12, 9, 11, 100), "09:31": (11, 11, 10, 10, 300), "09:35": (10, 10, 10, 10, 0)}
        vw = vwap_reeks(bars)
        self.assertAlmostEqual(vw["09:30"], (12 + 9 + 11) / 3)
        self.assertAlmostEqual(vw["09:31"], ((32 / 3) * 100 + (31 / 3) * 300) / 400)
        b5 = vijf_minuten(bars)
        self.assertEqual(b5["09:30"], (10, 12, 9, 10, 400))
        self.assertEqual(b5["09:35"], (10, 10, 10, 10, 0))

    def test_contracten(self):
        self.assertEqual(contracten(8.0, STRAT)[0], 5)
        self.assertEqual(contracten(9.0, STRAT)[0], 4)
        self.assertEqual(contracten(50.0, STRAT), (0, "stop_te_groot"))
        self.assertEqual(contracten(9.0, STRAT, afstand_tot_bodem=500)[0], 2)

    def test_stop_en_doel_in_dezelfde_minuut_stop_telt(self):
        bars = {"15:00": (100, 100, 100, 100, 1), "15:01": (100, 106, 96, 100, 1), "15:55": (100, 100, 100, 100, 1)}
        t = simuleer_trade(bars, 1, "15:00", 100.25, 97.0, 105.0, "15:55", 1, STRAT)
        self.assertEqual((t["uitstapreden"], t["uitstap"]), ("stop", 96.75))

    def test_doel_pas_bij_doorbraak_van_1_tick(self):
        bars = {"15:00": (100, 100, 100, 100, 1), "15:01": (100, 105.0, 100, 100, 1), "15:02": (100, 105.25, 100, 100, 1),
                "15:55": (100, 100, 100, 100, 1)}
        t = simuleer_trade(bars, 1, "15:00", 100.0, 98.0, 105.0, "15:55", 1, STRAT)
        self.assertEqual((t["uitstapreden"], t["uitstap_minuut"], t["uitstap"]), ("doel", "15:02", 105.0))

    def test_kosten_en_r(self):
        bars = {"15:00": (100, 100, 100, 100, 1), "15:55": (104.25, 104.25, 104.25, 104.25, 1)}
        t = simuleer_trade(bars, 1, "15:00", 100.25, 96.25, None, "15:55", 2, STRAT)
        self.assertAlmostEqual(t["bruto"], (104.0 - 100.25) * 5 * 2)
        self.assertAlmostEqual(t["netto"], t["bruto"] - 2.44)
        self.assertAlmostEqual(t["R"], t["netto"] / 40.0)


class TestStrategieA(unittest.TestCase):
    def setUp(self):
        self.dag = lambda bars, d=D: maak_dag(d, "ESZ6", bars, 106.0, KAL)

    def test_pullback_en_trigger(self):
        trades, reden = strategie_a(self.dag(a_dag()), STRAT, Rekening(5000))
        self.assertEqual(len(trades), 1, reden)
        t = trades[0]
        self.assertEqual((t["richting"], t["instap_minuut"], t["instap"], t["stop"]), (1, "15:00", 112.25, 106.75))
        self.assertEqual(t["contracten"], 5)
        self.assertAlmostEqual(t["doel"], 112.25 + 2 * 5.5)
        self.assertEqual((t["uitstapreden"], t["uitstap_minuut"]), ("tijd", "15:55"))

    def test_geen_bias(self):
        bars = dag_bars([("09:30", "15:59", 100.0)], {"09:30": (100.0, 101.0, 99.0, 100.0)})
        self.assertEqual(strategie_a(self.dag(bars), STRAT, Rekening(5000)), ([], "geen_bias"))

    def test_pullback_te_ver_van_vwap(self):
        bars = a_dag(pullback_laag=109.0)                    # pullback blijft boven VWAP + 2 (VWAP ± 105,6)
        bars["14:46"] = (110.0, 110.0, 109.5, 110.0, 100.0)
        self.assertEqual(strategie_a(self.dag(bars), STRAT, Rekening(5000)), ([], "pullback_te_ver_van_vwap"))
        self.assertEqual(len(strategie_a(self.dag(a_dag(pullback_laag=103.0)), STRAT, Rekening(5000))[0]), 1)   # onder VWAP: geldig

    def test_stop_te_groot_en_te_klein(self):
        bars = a_dag(pullback_laag=107.0)
        bars["15:00"] = (125.0, 125.0, 125.0, 125.0, 100)   # instap 125,25 -> stop 18,5 punten
        self.assertEqual(strategie_a(self.dag(bars), STRAT, Rekening(5000))[1], "stop_te_groot")
        bars = a_dag(pullback_laag=107.0)
        bars["15:00"] = (108.0, 108.0, 108.0, 108.0, 100)   # instap 108,25 -> stop 1,5 punten
        self.assertEqual(strategie_a(self.dag(bars), STRAT, Rekening(5000))[1], "stop_te_klein")

    def test_geen_instap_na_1545(self):
        bars = a_dag(trigger_bar="15:45")
        self.assertEqual(strategie_a(self.dag(bars), STRAT, Rekening(5000)), ([], "geen_trigger"))
        bars = a_dag(trigger_bar="15:40")                    # instap 15:45 mag nog
        self.assertEqual(strategie_a(self.dag(bars), STRAT, Rekening(5000))[0][0]["instap_minuut"], "15:45")

    def test_max_twee_trades_en_dagstop(self):
        s = copy.deepcopy(STRAT)
        vijf = {"09:30": (100.0, 101.0, 99.0, 100.0), "14:35": (106.0, 108.0, 106.0, 108.0),
                "14:40": (108.0, 110.0, 108.0, 110.0)}
        # drie keer pullback + trigger, elke trade direct gestopt (verlies)
        for k, lo in (("14:45", 107.0), ("15:00", 107.0), ("15:15", 107.0)):
            m = int(k[3:])
            k2, k3 = "%s:%02d" % (k[:2], m + 5), "%s:%02d" % (k[:2], m + 10)
            vijf[k] = (110.0, 110.0, lo, 109.0)
            vijf[k2] = (109.0, 111.0, 109.0, 111.0)
            vijf[k3] = (111.0, 111.0, 100.0, 110.0)          # stop geraakt
        bars = dag_bars([("09:30", "14:34", 106.0), ("15:30", "15:59", 110.0)], vijf)
        trades, _ = strategie_a(maak_dag(D, "ESZ6", bars, 106.0, KAL), s, Rekening(5000))
        self.assertEqual(len(trades), 2)                      # dagstop na 2 verliezen (en max 2 trades)
        self.assertTrue(all(t["uitstapreden"] == "stop" for t in trades))


class TestAndereStrategieen(unittest.TestCase):
    def hist(self, n=60, rod=0.001, beweging=4.0):
        return [Dag(D - dt.timedelta(days=100 - i), "ESZ6", {}, 100.0, 100.0 * (1 + (rod if i % 2 else -rod)),
                    100.0 * (1 + (rod if i % 2 else -rod)) + beweging, 100.0) for i in range(n)]

    def test_b_eerste_half_uur(self):
        bars = dag_bars([("09:30", "09:59", 100.0), ("10:00", "15:59", 101.0)])
        bars["09:59"] = (101.0, 101.0, 101.0, 101.0, 1)
        trades, _ = speel("B", maak_dag(D, "ESZ6", bars, 99.0, KAL), [], STRAT, Rekening(5000))
        self.assertEqual((trades[0]["richting"], trades[0]["instap_minuut"], trades[0]["stop"]), (1, "15:30", 101.25 - 8.0))

    def test_c_d_e_r(self):
        bars = dag_bars([("09:30", "09:59", 99.0), ("10:00", "15:59", 101.0)])
        dag = maak_dag(D, "ESZ6", bars, 100.0, KAL)          # ROD +1%, r1000 -1%
        h = self.hist()
        c = speel("C", dag, h, STRAT, Rekening(5000))[0][0]
        self.assertEqual((c["richting"], c["instap_minuut"], c["uitstap_minuut"]), (1, "15:30", "15:59"))
        self.assertAlmostEqual(c["instap"] - c["stop"], 6.0)  # 1,5 x gem. beweging 4,0
        self.assertEqual(speel("D", dag, h, STRAT, Rekening(5000))[0][0]["richting"], 1)
        self.assertEqual(speel("E", dag, h, STRAT, Rekening(5000))[0][0]["richting"], -1)
        r = speel("R", dag, h, STRAT, Rekening(5000))[0][0]
        self.assertEqual(r["richting"], willekeurige_richting(D, STRAT))
        self.assertEqual(speel("D", dag, h[:59], STRAT, Rekening(5000))[1], "te_weinig_historie")
        klein = maak_dag(D, "ESZ6", dag_bars([("09:30", "15:59", 100.05)]), 100.0, KAL)
        self.assertEqual(speel("D", klein, h, STRAT, Rekening(5000))[1], "filter_zwak")
        self.assertEqual(speel("R", klein, h, STRAT, Rekening(5000))[1], "filter_zwak")

    def test_g_opening_range_breakout(self):
        bars = dag_bars([("09:30", "15:59", 101.0)], {"09:30": (100.0, 101.5, 98.0, 101.0)})
        g = speel("G", maak_dag(D, "ESZ6", bars, 100.0, KAL), [], STRAT, Rekening(5000))[0][0]
        self.assertEqual((g["richting"], g["instap_minuut"], g["stop"]), (1, "09:35", 97.75))
        self.assertAlmostEqual(g["doel"], 101.25 + 10 * 3.5)

    def test_niet_handeldagen_en_weekstop(self):
        bars = a_dag()
        for d in (dt.date(2026, 10, 28), dt.date(2026, 12, 28), dt.date(2026, 11, 27)):   # FOMC, kerst, vervroegd
            for v in STRAT["varianten"]:
                self.assertEqual(speel(v, maak_dag(d, "ESZ6", bars, 106.0, KAL), self.hist(), STRAT, Rekening(5000))[0], [])
        self.assertEqual(speel("A", maak_dag(D, "ESZ6", bars, 106.0, KAL), [], STRAT, Rekening(5000, week_pnl=-850))[1], "weekstop")


class TestKalender(unittest.TestCase):
    def test_roll(self):
        self.assertEqual(KAL.contract_voor(dt.date(2026, 12, 9)), (2026, 12))   # expiratie 18 dec, roll 10 dec
        self.assertEqual(KAL.contract_voor(dt.date(2026, 12, 10)), (2027, 3))
        self.assertEqual(ticker(2026, 12), "ESZ26.CME")
        self.assertEqual(contract_code(2027, 3), "ESH7")


# ---------------------------------------------------------------- forward test
def nepdata(van=dt.date(2026, 6, 1), tot=dt.date(2026, 11, 30), seed=4):
    rng, p, out, d = random.Random(seed), 6500.0, {}, van
    while d <= tot:
        if KAL.is_handelsdag(d):
            trend, bars = rng.gauss(0, 0.6), {}
            p += rng.gauss(0, 15)
            for k in minuten("09:25", "16:05"):
                c = round((p + trend + rng.gauss(0, 1.2)) * 4) / 4
                bars[k] = (p, max(p, c) + 0.25 * rng.randint(0, 2), min(p, c) - 0.25 * rng.randint(0, 2), c,
                           float(rng.randint(50, 500)))
                p = c
            out[d] = bars
        d += dt.timedelta(days=1)
    return out


def naar_5m(bars):
    out = {}
    for k in sorted(bars):
        s = "%s:%02d" % (k[:2], int(k[3:]) // 5 * 5)
        o, h, l, c, v = bars[k]
        out[s] = (out[s][0], max(out[s][1], h), min(out[s][2], l), c, out[s][4] + v) if s in out else (o, h, l, c, v)
    return out


class NepBron:
    def __init__(self, data, tot=None, symbolen=("ESZ26.CME",)):
        self.data, self.tot, self.symbolen = data, tot, symbolen

    def bars(self, sym, van, tot, interval="1m"):
        if sym not in self.symbolen:
            return {}
        return {d: (b if interval == "1m" else naar_5m(b)) for d, b in self.data.items()
                if van <= d <= tot and (self.tot is None or d <= self.tot)}


def utc(d, hhmm="21:30"):
    return dt.datetime(d.year, d.month, d.day, int(hhmm[:2]), int(hhmm[3:]), tzinfo=dt.timezone.utc)


class TestForward(unittest.TestCase):
    def setUp(self):
        self.map = Path(tempfile.mkdtemp(prefix="mes_"))
        self.strat = copy.deepcopy(STRAT)
        self.strat["forward"].update({"max_dagen_terug_1m": 60, "max_dagen_terug_5m": 200})

    def tearDown(self):
        shutil.rmtree(self.map, ignore_errors=True)

    def test_zelfde_als_dag_voor_dag_afspelen(self):
        """Forward (met opslag, accounts uit het journal) geeft dezelfde trades als alles in één lus afspelen."""
        data = nepdata()
        run(NepBron(data), self.map, nu=utc(dt.date(2026, 11, 20)), strat=self.strat, log=lambda *_: None)
        fw = journal_trades(self.map)
        self.assertGreater(len(fw), 40)
        from bot_mes.account import account_uit_trades
        start = dt.date.fromisoformat(self.strat["forward"]["startdatum"])
        verwacht, hist, vorig = [], [], None
        for d in sorted(data):
            dag = maak_dag(d, "ESZ6", data[d], vorig, KAL)
            dag.ruis = ruis_uit(*ruis_prijzen(data[d], self.strat["H"]["checkpunten"]))
            if d >= start and d <= dt.date(2026, 11, 20):
                for v in self.strat["varianten"]:
                    eerder = [t for t in verwacht if t["strategie"] == v]
                    acc = account_uit_trades(FIRM, [(t["datum"], t["netto"], t["mae"]) for t in eerder])
                    wk = sum(t["netto"] for t in eerder if t["datum"].isocalendar()[:2] == d.isocalendar()[:2])
                    trades, _ = speel(v, dag, hist, self.strat, Rekening(acc.afstand_tot_bodem(), wk))
                    verwacht += [dict(t, datum=d) for t in trades]
            if dag.geldig:
                hist.append(dag)
            vorig = dag.p1600
        sleutel = lambda t: (t["datum"], t["strategie"], t["instap_minuut"])  # noqa: E731
        self.assertEqual(sorted(sleutel(t) for t in fw), sorted(sleutel(t) for t in verwacht))
        per = {sleutel(t): t for t in verwacht}
        for t in fw:
            self.assertAlmostEqual(t["netto"], per[sleutel(t)]["netto"], places=2)
        self.assertEqual({t["strategie"] for t in fw}, set(self.strat["varianten"]))

    def test_niet_dubbel_inhalen_en_rapport(self):
        data = nepdata()
        run(NepBron(data), self.map, nu=utc(dt.date(2026, 10, 3), "12:00"), strat=self.strat, log=lambda *_: None)
        self.assertEqual(lees_csv(self.map / "verwerkt.csv"), [])            # zaterdag vóór de start
        self.assertTrue(lees_csv(self.map / "koersen" / "dagen.csv"))         # wel opgewarmd
        run(NepBron(data), self.map, nu=utc(dt.date(2026, 10, 7)), strat=self.strat, log=lambda *_: None)
        run(NepBron(data), self.map, nu=utc(dt.date(2026, 10, 7)), strat=self.strat, log=lambda *_: None)
        self.assertEqual([r["datum"] for r in lees_csv(self.map / "verwerkt.csv")], ["2026-10-05", "2026-10-06", "2026-10-07"])
        self.assertEqual(len(lees_csv(self.map / "signalen.csv")), 3 * len(self.strat["varianten"]))
        md = (self.map / "DAGRAPPORT.md").read_text(encoding="utf-8")
        for stuk in ("dagrapport 07-10-2026", "## Laatste handelsdag", "## Sinds de start", "A – laatste-uur"):
            self.assertIn(stuk, md)

    def test_vandaag_pas_na_het_slot_en_wachten_op_data(self):
        data = nepdata()
        run(NepBron(data), self.map, nu=utc(dt.date(2026, 10, 5), "19:00"), strat=self.strat, log=lambda *_: None)
        self.assertEqual(lees_csv(self.map / "verwerkt.csv"), [])            # 15:00 ET: nog niet klaar
        run(NepBron(data, tot=dt.date(2026, 10, 5)), self.map, nu=utc(dt.date(2026, 10, 6)), strat=self.strat,
            log=lambda *_: None)
        self.assertEqual([r["datum"] for r in lees_csv(self.map / "verwerkt.csv")], ["2026-10-05"])   # 6 okt: later opnieuw

    def test_noodstop(self):
        (self.map / "STOP").parent.mkdir(parents=True, exist_ok=True)
        (self.map / "STOP").write_text("")
        self.assertIsNone(run(NepBron(nepdata()), self.map, nu=utc(dt.date(2026, 10, 7)), strat=self.strat,
                              log=lambda *_: None))


class TestConfig(unittest.TestCase):
    def test_strategy_json(self):
        with open(ROOT / "bot_mes" / "strategy.json", encoding="utf-8") as f:
            s = json.load(f)
        self.assertEqual(sorted(s["varianten"]), list("ABCDEGHR"))


if __name__ == "__main__":
    unittest.main()


class TestNoiseAreaH(unittest.TestCase):
    """Strategie H (toegevoegd 5 okt 2026)."""
    CPS = STRAT["H"]["checkpunten"]

    def hist(self, ruis=0.002, n=14):
        return [Dag(D - dt.timedelta(days=i + 1), "ESZ6", {}, 100, 100, 100, 100, [], {cp: ruis for cp in self.CPS})
                for i in range(n)][::-1]

    def test_te_weinig_historie(self):
        from bot_mes.strategieen import strategie_h
        dag = maak_dag(D, "ESZ6", dag_bars([("09:30", "15:59", 6000.0)]), 6000.0, KAL)
        self.assertEqual(strategie_h(dag, self.hist(n=13), STRAT, Rekening(5000))[1], "te_weinig_historie")

    def test_binnen_band_geen_trade(self):
        from bot_mes.strategieen import strategie_h
        dag = maak_dag(D, "ESZ6", dag_bars([("09:30", "15:59", 6000.0)]), 6000.0, KAL)
        self.assertEqual(strategie_h(dag, self.hist(), STRAT, Rekening(5000)), ([], "geen_uitbraak"))

    def test_uitbraak_long_tot_slot(self):
        """σ = 0,2% → band 6012; om 10:30 staat hij op 6020 → long op de opening van 10:30, harde stop 12 punten, uit 15:59."""
        from bot_mes.strategieen import strategie_h
        bars = dag_bars([("09:30", "10:14", 6000.0), ("10:15", "15:59", 6020.0)])
        dag = maak_dag(D, "ESZ6", bars, 6000.0, KAL)
        trades, reden = strategie_h(dag, self.hist(), STRAT, Rekening(5000))
        self.assertEqual(reden, "")
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual((t["richting"], t["instap_minuut"], t["uitstapreden"]), (1, "10:30", "tijd"))
        self.assertAlmostEqual(t["instap"], 6020.25)
        self.assertAlmostEqual(t["stop"], 6020.25 - 12.0)
        self.assertEqual(t["contracten"], 3)          # floor(200 / (12 × 5))

    def test_trailing_uitstap_onder_band(self):
        """Long vanaf 10:30; om 12:00 terug op 6010 (< band 6012, boven de harde stop) → trailing-uitstap op de opening van 12:00."""
        from bot_mes.strategieen import strategie_h
        bars = dag_bars([("09:30", "10:14", 6000.0), ("10:15", "11:49", 6020.0), ("11:50", "15:59", 6010.0)])
        dag = maak_dag(D, "ESZ6", bars, 6000.0, KAL)
        trades, _ = strategie_h(dag, self.hist(), STRAT, Rekening(5000))
        self.assertEqual(trades[0]["uitstapreden"], "trailing")
        self.assertEqual(trades[0]["uitstap_minuut"], "12:00")
        self.assertEqual(len(trades), 1)              # geen herinstap long op hetzelfde controlepunt

    def test_harde_stop(self):
        from bot_mes.strategieen import strategie_h
        bars = dag_bars([("09:30", "10:14", 6000.0), ("10:15", "10:44", 6020.0), ("10:45", "15:59", 6005.0)])
        dag = maak_dag(D, "ESZ6", bars, 6000.0, KAL)
        trades, _ = strategie_h(dag, self.hist(), STRAT, Rekening(5000))
        self.assertEqual(trades[0]["uitstapreden"], "stop")
        self.assertEqual(trades[0]["uitstap_minuut"], "10:45")

    def test_cache_bewaart_halfuurprijzen(self):
        from bot_mes.forward import Cache
        tmp = Path(tempfile.mkdtemp())
        try:
            c = Cache(tmp / "dagen.csv", self.CPS)
            c.zet(D, "ESZ6", dag_bars([("09:30", "15:59", 6000.0)]), "1m")
            c.bewaar()
            c2 = Cache(tmp / "dagen.csv", self.CPS)
            self.assertEqual(c2.ruis(D, "ESZ6"), {cp: 0.0 for cp in self.CPS})
        finally:
            shutil.rmtree(tmp)
