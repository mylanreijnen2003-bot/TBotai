"""De hele backtest-keten (analyse, criteria, HTML/CSV-rapport, journal) op nepdata, in een tijdelijke map."""
import csv
import datetime as dt
import random
import unittest

from bot_zn.tests.hulp import FIRM, KAL, STRAT, TijdelijkeMap
from bot_zn.backtest import analyseer
from bot_zn.data import lees_data, v0_rolls
from bot_zn.journal_zn import lees, schrijf_backtest_journal
from bot_zn.rapport import schrijf_backtest_rapport
from bot_zn.strategie import bouw_dagen
from bot_zn.tijd import TICK


def nepdata(pad, van=dt.date(2019, 6, 3), tot=dt.date(2022, 3, 31)):
    rng = random.Random(7)
    p, d, rijen = 120.0, van, []
    while d <= tot:
        if KAL.is_handelsdag(d):
            cid = "%d%02d" % KAL.contract_voor(d)
            for i in range(71):
                t = "%02d:%02d" % (14 + i // 60, i % 60)
                c = round((p + rng.gauss(0, 0.7) * TICK) / TICK) * TICK
                rijen.append([d.isoformat(), t, p, max(p, c) + TICK, min(p, c) - TICK, c, 10, cid, "ZN"])
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
            self.assertGreater(len(rolls), 5)
            dagen = bouw_dagen(ruwe, KAL, STRAT, roll_dagen=set(rolls))
            res = analyseer(dagen, STRAT, FIRM, log=lambda *_: None)
            res["rolls"], res["roll_afwijkingen"] = rolls, []
            self.assertIn(res["oordeel"]["oordeel"], ("GO", "NO-GO"))
            self.assertEqual(len(res["oordeel"]["criteria"]), 9)
            pad = schrijf_backtest_rapport(res, STRAT, m / "reports")
            html = pad.read_text(encoding="utf-8")
            for stuk in ("Eindoordeel", "Gevoeligheidstabel", "Vulgraad", "Topstep-regelsimulator", "<svg"):
                self.assertIn(stuk, html)
            for f in ("samenvatting.csv", "trades_A.csv", "trades_D.csv", "gevoeligheid.csv", "criteria.json", "dag_pnl_A.csv"):
                self.assertTrue((m / "reports" / f).exists(), f)
            n = schrijf_backtest_journal({v: res[v]["trades"] for v in "ABCD"}, STRAT, pad=m / "journal_bot.csv")
            rows = lees(m / "journal_bot.csv")
            self.assertEqual(len(rows), n)
            self.assertTrue(all(r["account"] == "zn-backtest" and r["setup"] in ("T-A", "T-B", "T-C", "T-D") for r in rows))
            # opnieuw schrijven vervangt de backtest-rijen (geen dubbele)
            schrijf_backtest_journal({v: res[v]["trades"] for v in "ABCD"}, STRAT, pad=m / "journal_bot.csv")
            self.assertEqual(len(lees(m / "journal_bot.csv")), n)


if __name__ == "__main__":
    unittest.main()
