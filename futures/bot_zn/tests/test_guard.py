"""Guard weigert elke foute order uit plan §7 (test 13)."""
import datetime as dt
import unittest

from bot_zn.tests.hulp import STRAT, TijdelijkeMap, et_tijd, logboek
from bot_zn.broker import KOOP, LIMIT, MARKET, STOP, VERKOOP
from bot_zn.guard import Guard

D = dt.date(2026, 10, 14)
CFG = {"modus": "sim", "account_id": 555}
MES, MGC = 111, 222


def order(**kw):
    o = {"soort": "instap", "type": LIMIT, "side": KOOP, "size": 2, "symbool": "ZN", "account_id": 555,
         "tijd_et": et_tijd(D, "14:30:00")}
    o.update(kw)
    return o


def toestand(**kw):
    t = {"modus": "sim", "positie": 0, "open_instap_orders": 0, "dag_redenen": [], "no_go": False,
         "dag_gestopt": False, "trades_vandaag": 0}
    t.update(kw)
    return t


class Test13Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = TijdelijkeMap()
        self.map = self.tmp.__enter__()
        self.g = Guard(STRAT, CFG, [MES, MGC], logboek(self.map), self.map)

    def tearDown(self):
        self.tmp.__exit__()

    def ok(self, o, t=None):
        return self.g.controleer(o, t or toestand())[0]

    def test_goede_instap_mag(self):
        self.assertTrue(self.ok(order()))
        self.assertTrue(self.ok(order(tijd_et=et_tijd(D, "14:34:59"))))

    def test_foute_orders(self):
        fout = {
            "market-instap": order(type=MARKET),
            "stop als instap": order(type=STOP),
            "4 contracten": order(size=4),
            "0 contracten": order(size=0),
            "fout symbool": order(symbool="ES"),
            "account MES": order(account_id=MES),
            "account MGC": order(account_id=MGC),
            "onbekend account": order(account_id=999),
            "te vroeg": order(tijd_et=et_tijd(D, "14:29:59")),
            "te laat": order(tijd_et=et_tijd(D, "14:35:00")),
            "na 16:10": order(tijd_et=et_tijd(D, "16:15:00")),
        }
        for naam, o in fout.items():
            self.assertFalse(self.ok(o), naam)

    def test_foute_toestand(self):
        for naam, t in {"al positie": toestand(positie=1), "al instaporder": toestand(open_instap_orders=1),
                        "FOMC-dag": toestand(dag_redenen=["fomc"]), "NO-GO": toestand(no_go=True),
                        "dag gestopt": toestand(dag_gestopt=True), "tweede trade": toestand(trades_vandaag=1),
                        "paper": toestand(modus="paper")}.items():
            self.assertFalse(self.ok(order(), t), naam)

    def test_mes_mgc_account_ook_als_config_dat_zegt(self):
        g = Guard(STRAT, {"modus": "sim", "account_id": MES}, [MES, MGC], logboek(self.map), self.map)
        self.assertFalse(g.controleer(order(account_id=MES), toestand())[0])

    def test_kill_switch(self):
        (self.map / "STOP").write_text("")
        self.assertFalse(self.ok(order()))

    def test_stop_order(self):
        stop = order(soort="stop", type=STOP, side=VERKOOP, size=2, tijd_et=et_tijd(D, "14:31:00"))
        self.assertTrue(self.ok(stop, toestand(positie=2)))
        self.assertFalse(self.ok(stop, toestand(positie=0)))                 # zonder positie
        self.assertFalse(self.ok(dict(stop, side=KOOP), toestand(positie=2)))  # verkeerde kant
        self.assertFalse(self.ok(dict(stop, size=1), toestand(positie=2)))     # verkeerde grootte
        self.assertFalse(self.ok(dict(stop, type=LIMIT), toestand(positie=2)))

    def test_sluiten_mag_altijd(self):
        sluit = order(soort="sluit", type=MARKET, side=VERKOOP, size=2, tijd_et=et_tijd(D, "16:30:00"))
        self.assertTrue(self.ok(sluit, toestand(positie=2)))
        self.assertFalse(self.ok(sluit, toestand(positie=0)))
        self.assertFalse(self.ok(dict(sluit, size=3), toestand(positie=2)))

    def test_weigering_wordt_gelogd(self):
        self.ok(order(type=MARKET))
        self.assertTrue(any("GUARD WEIGERT" in r for r in self.g.log.regels))


if __name__ == "__main__":
    unittest.main()
