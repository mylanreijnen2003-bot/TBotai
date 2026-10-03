"""reports/fronttest.html: de stand van alle strategieën in de dagelijkse fronttest."""
import csv
import datetime as dt
import html
import json
from pathlib import Path

from .journal_zn import live_trades
from .rapport import CSS
from .statistiek import fmt, stats

KLEUREN = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


def _e(x):
    return html.escape(str(x))


def _signalen(pad):
    if not Path(pad).exists():
        return []
    with open(pad, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _grafiek(reeksen, namen, breedte=900, hoogte=280):
    """Cumulatieve R per strategie (R maakt strategieën met andere stops vergelijkbaar)."""
    alle = [v for r in reeksen.values() for _, v in r]
    if not alle:
        return "<p class='muted'>Nog geen trades.</p>"
    n_max = max(len(r) for r in reeksen.values())
    lo, hi = min(0.0, min(alle)), max(0.0, max(alle))
    span = (hi - lo) or 1.0
    L, R, T, B = 48, 60, 10, 24
    w, h = breedte - L - R, hoogte - T - B

    def x(i):
        return L + w * i / max(1, n_max)

    def y(v):
        return T + h * (hi - v) / span

    s = ["<svg viewBox='0 0 %d %d' width='100%%' style='max-width:%dpx' role='img' aria-label='Cumulatieve R per strategie'>"
         % (breedte, hoogte, breedte)]
    for v in sorted({lo, 0.0, hi}):
        s.append("<line x1='%d' x2='%d' y1='%.1f' y2='%.1f' stroke='var(--rule)'/>" % (L, L + w, y(v), y(v)))
        s.append("<text x='%d' y='%.1f' text-anchor='end' font-size='12' fill='var(--fg2)'>%+.1fR</text>" % (L - 6, y(v) + 4, v))
    s.append("<text x='%d' y='%d' font-size='12' fill='var(--fg2)'>trade-nummer →</text>" % (L, hoogte - 6))
    for i, (sid, r) in enumerate(reeksen.items()):
        if not r:
            continue
        kleur = KLEUREN[i % len(KLEUREN)]
        pts = "%.1f,%.1f " % (x(0), y(0)) + " ".join("%.1f,%.1f" % (x(j + 1), y(v)) for j, (_, v) in enumerate(r))
        s.append("<polyline fill='none' stroke='%s' stroke-width='2' points='%s'/>" % (kleur, pts))
        s.append("<text x='%.1f' y='%.1f' font-size='12' fill='var(--fg)'>%s</text>" % (x(len(r)) + 4, y(r[-1][1]) + 4, _e(sid)))
    s.append("</svg>")
    legenda = "<div class='legend'>" + "".join(
        "<span><i style='background:%s'></i>%s</span>" % (KLEUREN[i % len(KLEUREN)], _e(namen[sid]))
        for i, sid in enumerate(reeksen)) + "</div>"
    return legenda + "".join(s)


def schrijf_fronttest_rapport(bot_map, alg):
    bot_map = Path(bot_map)
    journal = bot_map / "journal_bot.csv"
    signalen = _signalen(bot_map / "logs" / "fronttest_signalen.csv")
    status_pad = bot_map / "data" / "fronttest_status.json"
    status = json.loads(status_pad.read_text(encoding="utf-8")) if status_pad.exists() else {}
    namen = {sid: d["naam"] for sid, d in alg["strategieen"].items()}
    laatste_dag = max((r["datum"] for r in signalen), default=None)

    rijen, reeksen = [], {}
    for sid in alg["strategieen"]:
        tr = [{"datum": d, "netto": n, "mae": m, "R": r} for d, n, m, r in live_trades("zn-paper", journal, "ZN-" + sid)]
        m = stats(tr)
        sig = [r for r in signalen if r["strategie"] == sid]
        signaal_dagen = sum(1 for r in sig if r["status"] in ("gevuld", "niet_gevuld"))
        vandaag = next((r for r in sig if r["datum"] == laatste_dag), None)
        if vandaag is None:
            tekst = "–"
        elif vandaag["status"] == "gevuld":
            tekst = "%s %s ct: %s R (%s)" % (vandaag["richting"], vandaag["contracten"], vandaag["R"], vandaag["uitstapreden"])
        else:
            tekst = vandaag["reden"] or vandaag["status"]
        cum, reeks = 0.0, []
        for t in sorted(tr, key=lambda x: x["datum"]):
            cum += t["R"] or 0.0
            reeks.append((t["datum"], cum))
        reeksen[sid] = reeks
        rijen.append("<tr><td>%s</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td style='text-align:left'>%s</td></tr>" % (
            _e(namen[sid]), len(sig), signaal_dagen, _e(m.get("trades", 0)), _e(fmt("winrate", m.get("winrate"))),
            _e(fmt("expectancy_R", m.get("expectancy_R"))), _e(fmt("netto_totaal", m.get("netto_totaal"))), _e(tekst)))

    h = ["<!doctype html><html lang='nl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         "<title>ZN-fronttest</title><style>%s</style></head><body><main>" % CSS,
         "<h1>ZN-fronttest – alle strategieën</h1>",
         "<p class='sub'>Paper, geen orders. Gestart op %s, laatst bijgewerkt voor handelsdag %s (gemaakt %s). "
         "Elke strategie ziet van een dag alleen de koersen vóór zijn eigen beslismoment.</p>"
         % (_e(status.get("start", "–")), _e(laatste_dag or "–"), dt.datetime.now().strftime("%Y-%m-%d %H:%M")),
         "<div class='wrap'><table><thead><tr><th>Strategie</th><th>Dagen</th><th>Signalen</th><th>Trades</th><th>Winrate</th>"
         "<th>Gem. R per trade</th><th>Netto</th><th style='text-align:left'>Laatste dag</th></tr></thead><tbody>",
         "".join(rijen), "</tbody></table></div>",
         "<h2>Cumulatieve R per strategie</h2>", _grafiek(reeksen, namen),
         "<p class='muted'>R = winst of verlies gedeeld door het geplande risico. +1R = je risico gewonnen. "
         "Na enkele weken zegt dit nog weinig: pas na tientallen trades per strategie wordt het verschil betekenisvol.</p>",
         "</main></body></html>"]
    pad = bot_map / "reports" / "fronttest.html"
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text("".join(h), encoding="utf-8")
    return pad
