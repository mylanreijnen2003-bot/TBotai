"""GitHub-versie: Yahoo-adapter, start op 5 okt, inhalen, rapport en aanvulling van de veilingkalender (geen netwerk)."""
import csv
import datetime as dt
import io
import json
import unittest

import pandas as pd

from bot_zn.tests.hulp import TijdelijkeMap
from bot_zn.tests.test_fronttest import nep_bars
from bot_zn.github import run, veilingen_online
from bot_zn.journal_zn import lees
from bot_zn.tijd import ET
from bot_zn.yahoo import YahooBroker, ticker

DATA = nep_bars(dt.date(2026, 5, 1), dt.date(2026, 12, 31), seed=5)


def nep_history(symbolen=("ZNZ26.CBT",), data=DATA, log=None):
    def history(sym, start, eind, interval):
        if log is not None:
            log.append((sym, start, eind, interval))
        if sym not in symbolen:
            return None
        a, b = dt.date.fromisoformat(start), dt.date.fromisoformat(eind)
        rijen = []
        for d, bars in data.items():
            if not (a <= d < b):
                continue
            groep = {}
            for t, (o, h, l, c) in sorted(bars.items()):
                hh, mm = (int(x) for x in t.split(":"))
                if interval == "5m":
                    mm = mm // 5 * 5
                k = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET)
                if k in groep:
                    o0, h0, l0, _ = groep[k]
                    groep[k] = (o0, max(h0, h), min(l0, l), c)
                else:
                    groep[k] = (o, h, l, c)
            rijen += [(k, *v) for k, v in groep.items()]
        if not rijen:
            return None
        df = pd.DataFrame(rijen, columns=["t", "Open", "High", "Low", "Close"]).set_index("t")
        df.index = pd.DatetimeIndex(df.index).tz_convert("America/New_York")
        return df
    return history


def nu(d, hm="16:40"):
    h, m = (int(x) for x in hm.split(":"))
    return dt.datetime(d.year, d.month, d.day, h, m, tzinfo=ET)


class TestYahoo(unittest.TestCase):
    def test_ticker(self):
        self.assertEqual(ticker(2026, 12), "ZNZ26.CBT")
        self.assertEqual(ticker(2027, 3), "ZNH27.CBT")

    def test_1m_recent_5m_ouder_niets_daarvoor(self):
        log = []
        b = YahooBroker(vandaag=dt.date(2026, 10, 16), history=nep_history(log=log))
        bars = b.bars("ZNZ26.CBT", dt.datetime(2026, 7, 1, tzinfo=ET), dt.datetime(2026, 10, 17, tzinfo=ET))
        self.assertEqual({x[3] for x in log}, {"1m", "5m"})
        dagen = {x["t"].astimezone(ET).date() for x in bars}
        self.assertEqual(min(dagen), dt.date(2026, 8, 19))            # 58 dagen terug: ouder levert Yahoo niet
        per_dag = {}
        for x in bars:
            per_dag.setdefault(x["t"].astimezone(ET).date(), 0)
            per_dag[x["t"].astimezone(ET).date()] += 1
        self.assertLess(per_dag[dt.date(2026, 9, 1)], 100)            # 5-minuut
        self.assertGreater(per_dag[dt.date(2026, 10, 15)], 400)       # 1-minuut

    def test_1m_in_blokken_van_max_7_dagen(self):
        """Yahoo weigert meer dan 8 dagen 1-minuutdata per verzoek (zo liep de ZN-run van 5-7 okt 2026 vast)."""
        log = []
        geschiedenis = nep_history(log=log)

        def streng(sym, start, eind, interval):
            if interval == "1m" and (dt.date.fromisoformat(eind) - dt.date.fromisoformat(start)).days > 8:
                raise RuntimeError("Only 8 days worth of 1m granularity data are allowed to be fetched per request.")
            return geschiedenis(sym, start, eind, interval)

        b = YahooBroker(vandaag=dt.date(2026, 10, 16), history=streng)
        bars = b.bars("ZNZ26.CBT", dt.datetime(2026, 9, 20, tzinfo=ET), dt.datetime(2026, 10, 17, tzinfo=ET))
        dagen = {x["t"].astimezone(ET).date() for x in bars}
        self.assertIn(dt.date(2026, 9, 21), dagen)
        self.assertIn(dt.date(2026, 10, 15), dagen)
        for sym, start, eind, iv in log:
            if iv == "1m":
                self.assertLessEqual((dt.date.fromisoformat(eind) - dt.date.fromisoformat(start)).days, 8)

    def test_terugval(self):
        b = YahooBroker(vandaag=dt.date(2026, 10, 16), history=nep_history(symbolen=("ZN=F",)))
        bars = b.bars("ZNZ26.CBT", dt.datetime(2026, 10, 12, tzinfo=ET), dt.datetime(2026, 10, 17, tzinfo=ET))
        self.assertTrue(bars)
        self.assertEqual(b.terugval["ZNZ26.CBT"], "ZN=F")


class TestGithubRun(unittest.TestCase):
    def test_start_5_okt_inhalen_en_rapport(self):
        with TijdelijkeMap() as m:
            geen = lambda *a: {}  # noqa: E731
            r = run(YahooBroker(vandaag=dt.date(2026, 10, 3), history=nep_history()), m, nu=nu(dt.date(2026, 10, 3)),
                    veilingen_bron=geen, log=lambda *_: None)
            self.assertEqual(r["dagen"], [])                          # zaterdag 3 okt: nog niets
            r = run(YahooBroker(vandaag=dt.date(2026, 10, 9), history=nep_history()), m, nu=nu(dt.date(2026, 10, 9)),
                    veilingen_bron=geen, log=lambda *_: None)
            self.assertEqual([str(d) for d in r["dagen"]], ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"])
            with open(m / "logs" / "fronttest_signalen.csv", newline="", encoding="utf-8") as f:
                rijen = list(csv.DictReader(f))
            self.assertEqual(min(x["datum"] for x in rijen), "2026-10-05")
            self.assertTrue(all(x["setup"].startswith("ZN-") for x in lees(m / "journal_bot.csv")))
            md = (m / "DAGRAPPORT.md").read_text(encoding="utf-8")
            for stuk in ("dagrapport 09-10-2026", "## Laatste handelsdag", "## Sinds de start", "A – "):
                self.assertIn(stuk, md)
            self.assertTrue((m / "reports" / "fronttest.html").exists())

    def test_veilingkalender_aangevuld(self):
        with TijdelijkeMap() as m:
            extra = {dt.date(2027, 1, 12): "10-Year Note"}
            r = run(YahooBroker(vandaag=dt.date(2026, 12, 20), history=nep_history()), m, nu=nu(dt.date(2026, 12, 20)),
                    veilingen_bron=lambda a, b: extra, log=lambda *_: None)
            self.assertEqual(r["ft"].veilingen[dt.date(2027, 1, 12)], "10-Year Note")

    def test_fiscaldata_lezen(self):
        data = {"data": [
            {"auction_date": "2027-01-12", "security_type": "Note", "original_security_term": "10-Year",
             "closing_time_comp": "01:00 PM", "inflation_index_security": "No"},
            {"auction_date": "2027-01-13", "security_type": "Bond", "original_security_term": "30-Year",
             "closing_time_comp": "01:00 PM", "inflation_index_security": "No"},
            {"auction_date": "2027-01-14", "security_type": "Bill", "original_security_term": "26-Week",
             "closing_time_comp": "11:30 AM", "inflation_index_security": "No"},
            {"auction_date": "2027-01-15", "security_type": "Note", "original_security_term": "10-Year",
             "closing_time_comp": "01:00 PM", "inflation_index_security": "Yes"}]}

        class Antwoord(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        uit = veilingen_online(dt.date(2027, 1, 1), dt.date(2027, 1, 31),
                               open_url=lambda url, timeout: Antwoord(json.dumps(data).encode()))
        self.assertEqual(uit, {dt.date(2027, 1, 12): "10-Year Note", dt.date(2027, 1, 13): "30-Year Bond"})
        self.assertEqual(veilingen_online(dt.date(2027, 1, 1), dt.date(2027, 1, 31),
                                          open_url=lambda url, timeout: (_ for _ in ()).throw(OSError("geen netwerk"))), {})


if __name__ == "__main__":
    unittest.main()
