"""De hele backtest-keten (analyse, Monte Carlo, criteria, rapport, journal) op nepdata."""
import csv
import datetime as dt
import random
import unittest

from bot_mgc.tests.hulp import FIRM, KAL, RULES, STRAT, TijdelijkeMap
from bot_mgc.backtest import analyseer
from bot_mgc.data import lees_data, v0_rolls
from bot_mgc.journal_mgc import lees, schrijf_backtest_journal
from bot_mgc.rapport import schrijf_backtest_rapport
from bot_mgc.strategie import bouw_dagen


def nepdata(pad, van=dt.date(2019, 6, 3), tot=dt.date(2022, 3, 31)):
    rng = random.Random(11)
    p, d, rijen = 1500.0, van, []
    while d <= tot:
        if KAL.is_handelsdag(d):
            cid = "%d%02d" % KAL.contract_voor(d)
            for mm in range(15, 56):          # ochtendvenster 08:15-08:55 (signaal D/E)
                c = round(p + rng.gauss(0, 0.6), 1)
                rijen.append([d.isoformat(), "08:%02d" % mm, p, round(max(p, c) + 0.2, 1), round(min(p, c) - 0.2, 1), c, 10, cid, "GC"])
                p = c
            for i in range(71):
                mm = 30 + i
                t = "%02d:%02d" % (12 + mm // 60, mm % 60)
                c = round(p + rng.gauss(0, 0.6), 1)
                rijen.append([d.isoformat(), t, p, round(max(p, c) + 0.2, 1), round(min(p, c) - 0.2, 1), c, 10, cid, "GC"])
                p = c
        d += dt.timedelta(days=1)
    with open(pad, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["datum", "tijd_et", "open", "high", "low", "close", "volume", "instrument_id", "symbool"])
        w.writerows(rijen)


class TestBacktestKeten(unittest.TestCase):
    def test_rapport_en_journal(self):
        with TijdelijkeMap() as m:
            nepdata(m / "data" / "nep.csv")
            ruwe = lees_data(m / "data" / "nep.csv")
            rolls = v0_rolls(ruwe)
            dagen = bouw_dagen(ruwe, KAL, STRAT, roll_dagen=set(rolls))
            res = analyseer(dagen, STRAT, FIRM, RULES, log=lambda *_: None, mc_runs=200)
            res["rolls"], res["roll_afwijkingen"] = rolls, []
            self.assertEqual(len(res["oordeel"]["criteria"]), 11)
            self.assertEqual(set(res["oordelen"]), {"A", "C", "D", "E"})
            self.assertIn("ok", res["controle_r"])
            self.assertIsNotNone(res["monte_carlo"])
            html = schrijf_backtest_rapport(res, STRAT, m / "reports").read_text(encoding="utf-8")
            for stuk in ("Overzicht", "Monte Carlo", "FOMC-dag", "Gevoeligheidstabel", "<svg", "Controle R", "Marktstatistiek",
                         "D – ochtendsignaal", "2015–2019", "alleen short"):
                self.assertIn(stuk, html)
            for f in ("samenvatting.csv", "trades_A.csv", "trades_C.csv", "trades_D.csv", "trades_E.csv", "trades_R.csv",
                      "criteria.json", "dag_pnl_A.csv"):
                self.assertTrue((m / "reports" / f).exists(), f)
            n = schrijf_backtest_journal({v: res[v]["trades"] for v in res["varianten"]}, pad=m / "journal_bot.csv")
            rows = lees(m / "journal_bot.csv")
            self.assertEqual(len(rows), n)
            self.assertTrue(all(r["account"] == "mgc-backtest" and r["instrument"] == "MGC" for r in rows))
            self.assertEqual({r["setup"] for r in rows} - {"G-A", "G-B", "G-C", "G-D", "G-E", "G-R"}, set())


if __name__ == "__main__":
    unittest.main()
