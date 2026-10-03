"""De live-bot tegen de nep-broker: paper zonder orders, sim met orders, herstel, kill switch, bewaking, config.
(plan §11 tests 6 (annuleren), 14, 15, 16, 17, 18)"""
import datetime as dt
import json
import unittest

from bot_zn.tests.hulp import FIRM, KAL, STRAT, TijdelijkeMap, bars_lijn, dag_bars, draai, et_tijd, logboek, vul_cache
from bot_zn import bewaking
from bot_zn.broker import LIMIT, ORDER_GEANNULEERD, STOP
from bot_zn.instellingen import ConfigFout, valideer_config
from bot_zn.journal_zn import lees
from bot_zn.live import ZNRunner
from bot_zn.nepbroker import NepBroker
from bot_zn.tijd import TICK

D = dt.date(2026, 10, 14)        # gewone woensdag, contract dec 2026
CID = "CON.F.US.TYA.Z26"


def opzet(map_, modus="sim", faal_bij_order=False, pad=None, account=555):
    slots = vul_cache(map_, D)
    gisteren = KAL.vorige_handelsdag(D)
    signaal = slots[gisteren] + 20 * TICK          # grote positieve ROD -> long
    broker = NepBroker(account_id=account, faal_bij_order=faal_bij_order)
    if pad is None:
        pad = bars_lijn("14:30", "15:00", signaal + 3 * TICK)
    broker.zet_bars(CID, dag_bars(D, signaal, pad))
    cfg = {"modus": modus, "account_id": account if modus == "sim" else None, "data_live": False}
    lg = logboek(map_, klok=lambda: broker.nu or et_tijd(D, "14:00:00"))
    runner = ZNRunner(broker, STRAT, cfg, KAL, FIRM, lg, map_, andere_ids=[111, 222])
    return runner, broker, signaal


class Test16PaperNooitOrders(unittest.TestCase):
    def test_paper_volledige_dag(self):
        with TijdelijkeMap() as m:
            sig = None
            runner, broker, sig = opzet(m, "paper", faal_bij_order=True)
            pad = bars_lijn("14:30", "15:00", sig + 2 * TICK)
            pad["14:31"] = (sig, sig, sig - TICK, sig)                         # limiet gevuld
            pad["14:59"] = (sig + 10 * TICK, sig + 10 * TICK, sig + 9 * TICK, sig + 10 * TICK)
            broker.zet_bars(CID, dag_bars(D, sig, pad))
            self.assertTrue(runner.start())
            draai(runner, broker, D)
            self.assertEqual(broker.order_aanroepen, 0)
            rows = [r for r in lees(m / "journal_bot.csv") if r["account"] == "zn-paper"]
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]["richting"], rows[0]["uitstapreden"], rows[0]["contracten"]), ("long", "tijd", "2"))
            self.assertAlmostEqual(float(rows[0]["uitstapprijs"]), sig + 9 * TICK)


class Test06SimNietGevuldGeannuleerd(unittest.TestCase):
    def test_limiet_niet_gevuld_wordt_geannuleerd(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "sim")
            self.assertTrue(runner.start())
            draai(runner, broker, D)
            limieten = [o for o in broker.orders.values() if o["type"] == LIMIT]
            self.assertEqual(len(limieten), 1)
            self.assertEqual(limieten[0]["status"], ORDER_GEANNULEERD)
            self.assertAlmostEqual(limieten[0]["limitPrice"], sig)
            self.assertTrue(any("niet_gevuld" in r for r in runner.log.regels))


class TestSimVolledigeTrade(unittest.TestCase):
    def test_fill_stop_order_en_uitstap(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "sim")
            runner.start()

            def vul(t):
                if t == et_tijd(D, "14:31:10"):
                    oid = [o for o in broker.orders.values() if o["type"] == LIMIT][0]["id"]
                    broker.vul_order(oid, sig)
            draai(runner, broker, D, na_tick=vul)
            stops = [o for o in broker.orders.values() if o["type"] == STOP]
            self.assertEqual(len(stops), 1)
            self.assertAlmostEqual(stops[0]["stopPrice"], sig - 6 * TICK)
            self.assertEqual(stops[0]["status"], ORDER_GEANNULEERD)    # bij de tijdsuitstap geannuleerd
            self.assertEqual(broker.posities_, {})
            rows = [r for r in lees(m / "journal_bot.csv") if r["account"] == "zn-sim"]
            self.assertEqual([r["uitstapreden"] for r in rows], ["tijd"])

    def test_stop_order_mislukt_positie_dicht(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "sim")
            broker.weiger_stop = True
            runner.start()

            def vul(t):
                if t == et_tijd(D, "14:31:10"):
                    oid = [o for o in broker.orders.values() if o["type"] == LIMIT][0]["id"]
                    broker.vul_order(oid, sig)
            draai(runner, broker, D, na_tick=vul)
            self.assertEqual(broker.posities_, {})
            self.assertTrue(runner.dag_gestopt)

    def test_firmabeperking_niet_opnieuw(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "sim")
            broker.weiger_instap = "Max position size exceeded"
            runner.start()
            draai(runner, broker, D)
            self.assertEqual(broker.order_aanroepen, 1)
            self.assertTrue(runner.dag_gestopt)
            self.assertTrue(any("firma_beperking" in r or "weigert" in r for r in runner.log.regels))


class Test14Herstel(unittest.TestCase):
    def test_geen_dubbele_order_na_time_out(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "sim")
            runner.start()
            broker.time_out_na_plaatsen = True     # order komt wél aan, maar het antwoord gaat verloren
            draai(runner, broker, D, tot="14:30:20")
            self.assertEqual(len([o for o in broker.orders.values() if o["type"] == LIMIT]), 1)
            self.assertFalse(runner.verbinding_verloren)
            self.assertEqual(runner.fase, "instap_open")
            draai(runner, broker, D, van="14:30:21")
            self.assertEqual(len([o for o in broker.orders.values() if o["type"] == LIMIT]), 1)

    def test_onbekende_positie_na_herstel_wordt_gesloten(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "sim")
            runner.start()
            draai(runner, broker, D, tot="14:25:00")
            broker.verbinding_weg = True
            draai(runner, broker, D, van="14:25:01", tot="14:25:05")
            # terwijl de verbinding weg was, is er (onbekend) een positie ontstaan
            broker.posities_[CID] = {"contractId": CID, "size": 1, "type": 1, "averagePrice": sig}
            runner.verbinding_verloren = True
            broker.verbinding_weg = False
            draai(runner, broker, D, van="14:25:06", tot="14:25:10")
            self.assertEqual(broker.posities_, {})
            self.assertTrue(runner.dag_gestopt)
            self.assertTrue(any("ONBEKEND" in r for r in runner.log.regels))

    def test_opstartcheck_onbekende_positie(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "sim")
            broker.posities_[CID] = {"contractId": CID, "size": 1, "type": 1, "averagePrice": 110.0}
            self.assertFalse(runner.start())
            self.assertTrue(runner.gestopt)
            self.assertEqual(broker.order_aanroepen, 0)   # niets doen


class Test15KillSwitch(unittest.TestCase):
    def test_stop_bestand_sluit_alles(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "sim")
            runner.start()

            def actie(t):
                if t == et_tijd(D, "14:31:10"):
                    oid = [o for o in broker.orders.values() if o["type"] == LIMIT][0]["id"]
                    broker.vul_order(oid, sig)
                if t == et_tijd(D, "14:40:00"):
                    (m / "STOP").write_text("")
            draai(runner, broker, D, na_tick=actie)
            self.assertTrue(runner.gestopt)
            self.assertEqual(broker.posities_, {})
            self.assertEqual(broker.open_orders(555), [])
            self.assertTrue(any("KILL SWITCH" in r for r in runner.log.regels))

    def test_start_geweigerd_met_stop_bestand(self):
        with TijdelijkeMap() as m:
            runner, broker, sig = opzet(m, "paper")
            (m / "STOP").write_text("")
            self.assertFalse(runner.start())


class Test17Bewaking(unittest.TestCase):
    def test_60_verliezers_no_go_en_geen_orders(self):
        with TijdelijkeMap() as m:
            rs = [-1.0 + 0.01 * (i % 5) for i in range(60)]
            res = bewaking.bijwerken("zn-sim", rs, 70, 60, [0.0] * 60, STRAT, status_pad=m / "status.json",
                                     rapport_pad=m / "reports" / "live.html", backtest_pad=m / "reports" / "x.json")
            self.assertTrue(res["no_go"])
            self.assertEqual(json.loads((m / "status.json").read_text())["status"], "NO-GO")
            self.assertTrue((m / "reports" / "live.html").exists())
            # daarna: modus sim, maar de bot plaatst geen orders meer en logt alleen in paper
            runner, broker, sig = opzet(m, "sim", faal_bij_order=True)
            self.assertTrue(runner.start())
            draai(runner, broker, D)
            self.assertEqual(broker.order_aanroepen, 0)
            self.assertEqual(runner.account, "zn-paper")

    def test_59_verliezers_nog_geen_no_go(self):
        res = bewaking.evalueer([-1.0 + 0.01 * (i % 5) for i in range(59)], 59, 59, [], STRAT)
        self.assertFalse(res["no_go"])

    def test_slippage_melding(self):
        res = bewaking.evalueer([0.1, 0.2], 2, 2, [1.5, 1.2], STRAT)
        self.assertTrue(any("Slippage" in x for x in res["meldingen"]))


class Test18GeenCombineModus(unittest.TestCase):
    def test_combine_geweigerd(self):
        for modus in ("combine", "Combine", "live", "funded"):
            with self.assertRaises(ConfigFout):
                valideer_config({"modus": modus, "account_id": 555})

    def test_sim_zonder_account_of_met_mes_account(self):
        with self.assertRaises(ConfigFout):
            valideer_config({"modus": "sim", "account_id": None})
        with self.assertRaises(ConfigFout):
            valideer_config({"modus": "sim", "account_id": 111, "andere_bots_account_ids": [111]})
        self.assertEqual(valideer_config({"modus": "paper"})["modus"], "paper")


if __name__ == "__main__":
    unittest.main()
