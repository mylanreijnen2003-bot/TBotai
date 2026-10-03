"""Logging naar bot_mgc/logs/. Maskeert alles wat op een key of token lijkt."""
import csv
import datetime as dt
import re
from pathlib import Path

from .instellingen import BOT
from .tijd import ET, NL

LOGS = BOT / "logs"
_GEHEIM = re.compile(r'(?i)("?(?:apikey|api_key|token|newToken|password|authorization)"?\s*[:=]\s*"?)([^",\s}]+)')

SIGNAAL_KOLOMMEN = ["datum", "account", "variant", "rod", "onfh", "mediaan", "filter", "signaal", "richting",
                    "stop_punten", "contracten", "status", "reden", "instap", "uitstap", "uitstapreden", "netto", "R",
                    "slippage_ticks", "tijd_et", "tijd_nl"]


def maskeer(tekst):
    return _GEHEIM.sub(lambda m: m.group(1) + "***", str(tekst))


class Logboek:
    def __init__(self, naam, map_=None, echo=True, klok=None):
        self.map = Path(map_ or LOGS)
        self.map.mkdir(parents=True, exist_ok=True)
        self.naam = naam
        self.echo = echo
        self.klok = klok or (lambda: dt.datetime.now(ET))
        self.regels = []   # ook in het geheugen (handig voor tests)

    def _pad(self):
        return self.map / ("%s_%s.log" % (self.naam, self.klok().date().isoformat()))

    def _schrijf(self, niveau, tekst):
        t = self.klok()
        regel = "%s ET (%s NL) [%s] %s" % (t.strftime("%Y-%m-%d %H:%M:%S"), t.astimezone(NL).strftime("%H:%M:%S"),
                                          niveau, maskeer(tekst))
        self.regels.append(regel)
        with open(self._pad(), "a", encoding="utf-8") as f:
            f.write(regel + "\n")
        if self.echo:
            try:
                print(regel)
            except UnicodeEncodeError:  # pragma: no cover
                print(regel.encode("ascii", "replace").decode())

    def info(self, tekst):
        self._schrijf("INFO", tekst)

    def waarschuwing(self, tekst):
        self._schrijf("LET OP", tekst)

    def alarm(self, tekst):
        self._schrijf("ALARM", tekst)

    def signaal(self, rij):
        """Eén regel per dag in logs/signalen.csv (ROD, filter, signaal, order, gevuld of niet, reden)."""
        pad = self.map / "signalen.csv"
        if pad.exists():   # oud bestand met andere kolommen: apart zetten in plaats van rijen te verschuiven
            with open(pad, encoding="utf-8") as f:
                kop = f.readline().strip()
            if kop and kop != ",".join(SIGNAAL_KOLOMMEN):
                pad.rename(self.map / ("signalen_oud_%s.csv" % self.klok().strftime("%Y%m%d%H%M%S")))
        nieuw = not pad.exists()
        with open(pad, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SIGNAAL_KOLOMMEN, extrasaction="ignore")
            if nieuw:
                w.writeheader()
            w.writerow({k: ("" if rij.get(k) is None else rij.get(k)) for k in SIGNAAL_KOLOMMEN})


def lees_signalen(map_=None, account=None):
    pad = Path(map_ or LOGS) / "signalen.csv"
    if not pad.exists():
        return []
    with open(pad, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if account is None or r.get("account") == account]
