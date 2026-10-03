"""HTML- en CSV-rapporten (backtest en live vs. backtest). Geen externe bibliotheken nodig."""
import csv
import datetime as dt
import html
import json
from collections import Counter
from pathlib import Path

import math

from .statistiek import LABELS, fmt, geld, in_periode, per_jaar, per_weekdag, stats
from .strategie import variant_naam

KLEUREN = {"A": "var(--s1)", "B": "var(--s2)", "C": "var(--s3)", "D": "var(--s4)", "E": "var(--s5)", "R": "var(--s6)"}

CSS = """
:root{--bg:#fcfcfb;--fg:#0b0b0b;--fg2:#52514e;--rule:#e4e3df;--card:#ffffff;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#8f5bd6;--s6:#8a8984;--good:#0ca30c;--bad:#d93a3a}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#1a1a19;--fg:#fff;--fg2:#c3c2b7;
--rule:#3a3a37;--card:#232321;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#a77ee8;--s6:#9a9990;--good:#3fbf3f;--bad:#ef6b6b}}
:root[data-theme="dark"]{--bg:#1a1a19;--fg:#fff;--fg2:#c3c2b7;--rule:#3a3a37;--card:#232321;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#a77ee8;--s6:#9a9990;--good:#3fbf3f;--bad:#ef6b6b}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,Arial,sans-serif;margin:0;padding:24px 16px}
main{max-width:1100px;margin:0 auto}
h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:32px 0 8px;border-bottom:1px solid var(--rule);padding-bottom:4px}
h3{font-size:16px;margin:18px 0 6px} p.sub{color:var(--fg2);margin:0 0 16px}
.wrap{overflow-x:auto} table{border-collapse:collapse;margin:6px 0 12px;font-variant-numeric:tabular-nums;font-size:14px}
th,td{padding:4px 10px;border-bottom:1px solid var(--rule);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left} th{color:var(--fg2);font-weight:600}
.go{color:var(--good);font-weight:700} .nogo{color:var(--bad);font-weight:700}
.badge{display:inline-block;padding:6px 14px;border-radius:6px;font-size:22px;font-weight:700;border:2px solid currentColor}
.legend span{display:inline-flex;align-items:center;margin-right:16px;color:var(--fg2)}
.legend i{display:inline-block;width:14px;height:3px;margin-right:6px;border-radius:2px}
.chart{position:relative} .tip{position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--rule);
padding:6px 8px;border-radius:6px;font-size:13px;display:none;white-space:nowrap}
small,.muted{color:var(--fg2)}
"""


def _e(x):
    return html.escape(str(x))


def tabel(koppen, rijen):
    h = "<div class='wrap'><table><thead><tr>" + "".join("<th>%s</th>" % _e(k) for k in koppen) + "</tr></thead><tbody>"
    for r in rijen:
        h += "<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>"
    return h + "</tbody></table></div>"


def metric_rij(label, m, extra=()):
    return [_e(label)] + [_e(fmt(k, m.get(k))) for k in LABELS] + list(extra)


def ok_tekst(ok):
    return "<span class='go'>groen</span>" if ok else "<span class='nogo'>rood</span>"


def equity_svg(reeksen, oos_start, breedte=1000, hoogte=320, namen=None):
    """reeksen = {'A': [(datum, cumulatief), ...], ...}. Eén y-as in dollars."""
    alle = [p for r in reeksen.values() for p in r]
    if not alle:
        return "<p class='muted'>Geen trades.</p>"
    d0 = min(p[0] for p in alle)
    d1 = max(p[0] for p in alle)
    lo = min(0.0, min(p[1] for p in alle))
    hi = max(0.0, max(p[1] for p in alle))
    span_d = max(1, (d1 - d0).days)
    span_y = (hi - lo) or 1.0
    L, R, T, B = 64, 16, 12, 28
    w, h = breedte - L - R, hoogte - T - B

    def x(d):
        return L + w * (d - d0).days / span_d

    def y(v):
        return T + h * (hi - v) / span_y

    s = ["<svg viewBox='0 0 %d %d' width='100%%' role='img' aria-label='Equity-grafiek' "
         "style='max-width:%dpx;display:block'>" % (breedte, hoogte, breedte)]
    stap = _mooie_stap(span_y / 5)
    v = math.ceil(lo / stap) * stap
    while v <= hi + 1e-9:
        s.append("<line x1='%d' x2='%d' y1='%.1f' y2='%.1f' stroke='var(--rule)' stroke-width='1'/>" % (L, L + w, y(v), y(v)))
        s.append("<text x='%d' y='%.1f' text-anchor='end' font-size='12' fill='var(--fg2)'>%s</text>" % (L - 6, y(v) + 4, geld(v)))
        v += stap
    if span_d >= 400:
        for jaar in range(d0.year + 1, d1.year + 1):
            xd = x(dt.date(jaar, 1, 1))
            s.append("<text x='%.1f' y='%d' text-anchor='middle' font-size='12' fill='var(--fg2)'>%d</text>" % (xd, hoogte - 8, jaar))
    else:   # korte periode (paper): maanden
        maanden = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
        m = dt.date(d0.year + (d0.month == 12), d0.month % 12 + 1, 1)
        while m <= d1:
            s.append("<text x='%.1f' y='%d' text-anchor='middle' font-size='12' fill='var(--fg2)'>%s</text>"
                     % (x(m), hoogte - 8, maanden[m.month - 1]))
            m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    if oos_start is not None and d0 <= oos_start <= d1:
        xo = x(oos_start)
        s.append("<line x1='%.1f' x2='%.1f' y1='%d' y2='%d' stroke='var(--fg2)' stroke-dasharray='4 4'/>" % (xo, xo, T, T + h))
        s.append("<text x='%.1f' y='%d' font-size='12' fill='var(--fg2)'> out-of-sample →</text>" % (xo + 4, T + 12))
    for naam, r in reeksen.items():
        if not r:
            continue
        pts = " ".join("%.1f,%.1f" % (x(d), y(v)) for d, v in r)
        s.append("<polyline fill='none' stroke='%s' stroke-width='2' stroke-linejoin='round' points='%s'/>" % (KLEUREN.get(naam, "var(--fg2)"), pts))
        d, v = r[-1]
        s.append("<text x='%.1f' y='%.1f' font-size='12' fill='var(--fg)' text-anchor='end'>%s</text>" % (x(d) - 2, y(v) - 6, naam))
    s.append("<rect x='%d' y='%d' width='%d' height='%d' fill='transparent' class='hit'/>" % (L, T, w, h))
    s.append("</svg>")
    data = {n: [[d.isoformat(), round(v, 2)] for d, v in r] for n, r in reeksen.items()}
    namen = namen or {n: variant_naam(n) for n in reeksen}
    legend = "<div class='legend'>" + "".join("<span><i style='background:%s'></i>%s</span>" % (KLEUREN.get(n, "var(--fg2)"), _e(namen.get(n, n)))
                                               for n in reeksen) + "</div>"
    js = """<script>(function(){var c=document.currentScript.previousElementSibling;var svg=c.querySelector('svg');
var tip=c.querySelector('.tip');var D=%s;var d0=new Date('%s'),d1=new Date('%s');var L=%d,W=%d,BW=%d;
svg.addEventListener('mousemove',function(e){var r=svg.getBoundingClientRect();var px=(e.clientX-r.left)*BW/r.width;
var f=Math.max(0,Math.min(1,(px-L)/W));var t=new Date(d0.getTime()+f*(d1-d0));var s='';
for(var k in D){var a=D[k],best=null;for(var i=0;i<a.length;i++){if(new Date(a[i][0])<=t)best=a[i];else break;}
if(best)s+=k+': '+(best[1]<0?'−$':'$')+Math.abs(Math.round(best[1])).toLocaleString('nl-NL')+'<br>';}
tip.innerHTML=t.toISOString().slice(0,10)+'<br>'+s;tip.style.display='block';
tip.style.left=Math.min(r.width-160,e.clientX-r.left+12)+'px';tip.style.top='8px';});
svg.addEventListener('mouseleave',function(){tip.style.display='none';});})();</script>""" % (
        json.dumps(data), d0.isoformat(), d1.isoformat(), L, w, breedte)
    return legend + "<div class='chart'>" + "".join(s) + "<div class='tip'></div></div>" + js


def _mooie_stap(ruw):
    macht = 10 ** math.floor(math.log10(ruw)) if ruw > 0 else 1
    for f in (1, 2, 2.5, 5, 10):
        if f * macht >= ruw:
            return f * macht
    return 10 * macht


def cumulatief(trades):
    eq, out = 0.0, []
    for t in sorted(trades, key=lambda x: x["datum"]):
        eq += t["netto"]
        out.append((t["datum"], eq))
    return out


def schrijf_csv(pad, koppen, rijen):
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(koppen)
        w.writerows(rijen)


TRADE_KOLOMMEN = ["datum", "variant", "richting", "contracten", "signaal", "instap", "stop", "stop_afstand", "uitstap",
                  "uitstapreden", "instap_bar", "uitstap_bar", "bruto", "kosten", "netto", "risico", "R", "mae", "mfe", "fomc"]


def trade_csv(pad, trades):
    rijen = []
    for t in sorted(trades, key=lambda x: x["datum"]):
        rijen.append([t["datum"], t["variant"], "long" if t["richting"] > 0 else "short", t["contracten"],
                      "%.1f" % t["signaal"], "%.1f" % t["instap"], "%.1f" % t["stop"], "%.1f" % t["stop_afstand"],
                      "%.1f" % t["uitstap"], t["uitstapreden"], t["instap_bar"], t["uitstap_bar"], "%.2f" % t["bruto"],
                      "%.2f" % t["kosten"], "%.2f" % t["netto"], "%.2f" % t["risico"], "%.4f" % t["R"],
                      "%.2f" % t["mae"], "%.2f" % t["mfe"], "ja" if t["fomc"] else "nee"])
    schrijf_csv(pad, TRADE_KOLOMMEN, rijen)


def _oordeel_badge(o):
    return "<span class='%s'>%s</span>" % ("go" if o == "GO" else "nogo", _e(o))


def schrijf_backtest_rapport(res, strat, map_):
    map_ = Path(map_)
    map_.mkdir(parents=True, exist_ok=True)
    (is_van, is_tot) = res["periodes"]["in_sample"]
    (oos_van, laatste) = res["periodes"]["out_of_sample"]
    vs = res.get("varianten", list("ABC"))
    oordelen = res.get("oordelen", {"A": res["oordeel"]})
    o = res["oordeel"]
    naam = lambda v: variant_naam(v, strat)  # noqa: E731
    eerste = res["A"]["uitkomsten"][0]["datum"] if res["A"]["uitkomsten"] else "–"
    h = ["<!doctype html><html lang='nl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         "<title>MGC-backtest</title><style>%s</style></head><body><main>" % CSS]
    h.append("<h1>MGC-backtest – strategieën naast elkaar</h1>")
    h.append("<p class='sub'>Gemaakt op %s. Data %s t/m %s (Databento GC.v.0, 1-minuutbars; gerekend met MGC: $10 per punt). "
             "In-sample %s t/m %s, out-of-sample %s t/m %s. Alle varianten handelen 13:00–13:29 New York-tijd (ET) met "
             "dezelfde stop en positiegrootte; alleen het signaal verschilt. Zie HYPOTHESIS.md.</p>"
             % (dt.date.today(), eerste, laatste, is_van, is_tot, oos_van, laatste))

    h.append("<h2>Overzicht (out-of-sample, normale kosten)</h2>")
    rijen = []
    for v in vs:
        m = res[v]["oos"]
        oo = oordelen.get(v)
        rijen.append(["<i style='display:inline-block;width:10px;height:10px;border-radius:2px;background:%s;margin-right:6px'></i>%s"
                      % (KLEUREN.get(v, "var(--fg2)"), _e(naam(v))),
                      _e(m.get("trades", 0)), _e(fmt("expectancy_R", m.get("expectancy_R"))), _e(fmt("t_stat", m.get("t_stat"))),
                      _e(fmt("profit_factor", m.get("profit_factor"))), _e(fmt("netto_totaal", m.get("netto_totaal"))),
                      _oordeel_badge(oo["oordeel"]) if oo else "<span class='muted'>benchmark</span>",
                      _e("; ".join(x.split(".")[0] for x in oo["ontbreekt"])) if oo and oo["ontbreekt"] else ""])
    h.append(tabel(["Variant", "Trades", "Expectancy (R)", "t-stat", "Profit factor", "Netto", "Oordeel", "Niet gehaald (nrs)"], rijen))
    cr = res.get("controle_r")
    if cr:
        h.append("<p><b>Controle R</b> (willekeurige richting op de dagen van A): %s%s</p>" % (
            "<span class='go'>in orde</span>" if cr.get("ok") else ("<span class='nogo'>AFWIJKING</span>" if cr.get("ok") is False else "–"),
            _e(" — expectancy %+.3fR, verwacht ≈ %+.3fR (alleen kosten), z = %.2f.%s" % (
                cr["expectancy_R"], cr["verwacht_R"], cr["z"] or 0, "" if cr["ok"] else " " + cr["uitleg"])) if cr.get("ok") is not None else _e(" — " + cr["uitleg"])))
    h.append("<p class='muted'>GO vraagt alle 11 criteria: de 9 uit het plan plus t-stat ≥ %.2f (omdat er %d varianten getest worden) "
             "en beter dan R. Verwacht eerlijk gezegd dat geen enkele variant dat haalt; dan is het beste besluit parkeren, "
             "niet nieuwe varianten proberen.</p>" % (strat.get("min_t_stat_gecorrigeerd", 2.5), len(oordelen)))

    for v, oo in oordelen.items():
        h.append("<h2>Criteria %s</h2><p><span class='badge %s'>%s</span></p>" % (_e(naam(v)), "go" if oo["oordeel"] == "GO" else "nogo", oo["oordeel"]))
        h.append(tabel(["Criterium", "Uitkomst", "Status"], [[_e(n_), _e(d), ok_tekst(ok)] for n_, ok, d in oo["criteria"]]))
        if oo["ontbreekt"]:
            h.append("<p><b>Reden NO-GO:</b> niet gehaald: %s. De regels worden niet aangepast om alsnog te slagen.</p>"
                     % _e("; ".join(oo["ontbreekt"])))

    h.append("<h2>Aannames</h2><ul>"
             "<li>Kosten $%.2f per contract per round-turn (ruim; TopstepX rekent $1,92 voor MGC). Risico $%d per trade, max %d contracten.</li>"
             "<li>Market-instap op de opening van de 13:00-bar + %d tick; stop en tijdsuitstap met %d tick slippage; opent een bar al "
             "voorbij de stop, dan fill op die opening. Stress: %d ticks per kant.</li>"
             "<li>1 tick = 0,1 punt = $1. R = netto P&amp;L ÷ gepland risico (stop in punten × $10 × contracten). Stop &lt; %.1f punten: overslaan.</li>"
             "<li>ROD = prijs 13:00 ÷ slot gisteren (13:30) − 1. Ochtendsignaal (D, E) = prijs 08:50 ÷ slot gisteren − 1. "
             "Nooit over een contractwissel heen.</li>"
             "<li>FOMC-dagen worden wél gehandeld (besluit om 14:00 ET, na het venster) en apart getoond.</li>"
             "</ul>" % (strat["kosten_per_contract_rt"], strat["risico_per_trade"], strat["max_contracten"],
                         strat["fill"]["market_instap_slippage_ticks"], strat["fill"]["slippage_ticks"],
                         strat["stress"]["slippage_ticks"], strat["min_stop_punten"]))

    h.append("<h2>Equity-grafiek (normale kosten, cumulatief netto in $)</h2>")
    h.append(equity_svg({v: cumulatief(res[v]["trades"]) for v in vs}, oos_van, namen={v: naam(v) for v in vs}))

    h.append("<h2>Resultaten per strategie</h2>")
    koppen = ["Periode"] + list(LABELS.values())
    samen = []
    for var in vs:
        h.append("<h3>%s</h3>" % _e(naam(var)))
        rijen = []
        for kosten, sleutel in (("normaal", var), ("stress", var + "_stress")):
            r = res[sleutel]
            for label, m in (("In-sample", r["is"]), ("Out-of-sample", r["oos"])):
                rijen.append(metric_rij("%s (%s)" % (label, kosten), m))
                samen.append([var, kosten, label] + [m.get(k) for k in LABELS])
        for label, m in res[var].get("is_delen", []):
            rijen.append(metric_rij("In-sample %s" % label, m))
        for label, m in res[var].get("oos_richting", []):
            rijen.append(metric_rij("Out-of-sample, alleen %s" % label, m))
        h.append(tabel(koppen, rijen))
    schrijf_csv(map_ / "samenvatting.csv", ["variant", "kosten", "periode"] + list(LABELS), samen)
    h.append("<p class='muted'>In-sample is gesplitst in 2010–2014 (nog pithandel) en 2015–2019 (volledig elektronisch). "
             "Komt bijna alle winst uit de longs, dan is het waarschijnlijk de stijging van goud en geen momentum.</p>")

    a_tr, a_s = res["A"]["trades"], res["A_stress"]["trades"]
    h.append("<h2>Uitsplitsing strategie A</h2><h3>Per jaar (normale en stresskosten)</h3>")
    stress_jaar = dict(per_jaar(a_s))
    rijen = []
    for jaar, m in per_jaar(a_tr):
        ms = stress_jaar.get(jaar, {})
        rijen.append([_e(jaar), _e(m["trades"]), _e(fmt("winrate", m.get("winrate"))), _e(fmt("expectancy_R", m.get("expectancy_R"))),
                      _e(fmt("profit_factor", m.get("profit_factor"))), _e(fmt("netto_totaal", m.get("netto_totaal"))),
                      _e(fmt("expectancy_R", ms.get("expectancy_R"))), _e(fmt("netto_totaal", ms.get("netto_totaal")))])
    h.append(tabel(["Jaar", "Trades", "Winrate", "Expectancy", "Profit factor", "Netto", "Expectancy (stress)", "Netto (stress)"], rijen))
    h.append("<h3>Expectancy per jaar, alle varianten (normale kosten)</h3>")
    jaren = sorted({t["datum"].year for v in vs for t in res[v]["trades"]})
    pj = {v: dict(per_jaar(res[v]["trades"])) for v in vs}
    h.append(tabel(["Jaar"] + vs, [[_e(j)] + [_e(fmt("expectancy_R", pj[v].get(j, {}).get("expectancy_R"))) for v in vs] for j in jaren]))
    h.append("<h3>Per weekdag (out-of-sample)</h3>")
    h.append(tabel(koppen, [metric_rij(d, m) for d, m in per_weekdag(in_periode(a_tr, oos_van))]))
    h.append("<h3>FOMC-dag ja/nee</h3>")
    rijen = []
    for label, van, tot in (("In-sample", is_van, is_tot), ("Out-of-sample", oos_van, None)):
        sel = in_periode(a_tr, van, tot)
        rijen.append(metric_rij("%s, FOMC-dag" % label, stats([t for t in sel if t["fomc"]])))
        rijen.append(metric_rij("%s, geen FOMC" % label, stats([t for t in sel if not t["fomc"]])))
    h.append(tabel(koppen, rijen))

    h.append("<h2>Topstep-regelsimulator en Monte Carlo (bestaande sim/)</h2>")
    h.append("<p>Regelsimulator op de echte volgorde van de trades van A:</p>")
    h.append(tabel(["Start", "Status", "Einddatum", "Reden"],
                   [[_e(x["start"]), _e(x["status"]), _e(x["einde"] or "–"), _e(x["reden"] or "nog bezig aan het eind van de data")]
                    for x in res["topstep"]]))
    mcs = res["monte_carlo"] if "pass_pct" not in (res["monte_carlo"] or {"pass_pct": 0}) else {"A": res["monte_carlo"]}
    rijen = []
    for v, mc in mcs.items():
        if mc:
            rijen.append([_e(naam(v)), _e(mc["runs"]), "<b>%.1f%%</b>" % mc["pass_pct"], "%.1f%%" % mc["fail_pct"],
                          "%.1f%%" % mc["timeout_pct"], _e(mc["median_days_to_pass"])])
        else:
            rijen.append([_e(naam(v)), "–", "–", "–", "–", "geen out-of-sample trades"])
    h.append("<p>Monte Carlo (hele dagen uit de out-of-sample trades, met je persoonlijke regels):</p>")
    h.append(tabel(["Variant", "Runs", "Geslaagd", "Gezakt", "Onbeslist (120 dagen)", "Mediaan dagen tot slagen"], rijen))
    h.append("<p class='muted'>Virtueel 50K-account (strategie A): %d keer opnieuw begonnen, waarvan %d keer omdat halveren "
             "0 contracten gaf (vastgelopen).</p>" % (res["A"].get("herstarts", 0), res["A"].get("vastgelopen", 0)))

    gvs = res["gevoeligheid"] if "tabel" not in res["gevoeligheid"] else {"A": res["gevoeligheid"]}
    h.append("<h2>Gevoeligheidstabellen (alleen tonen; out-of-sample expectancy)</h2>"
             "<p class='muted'>De bot kiest nooit automatisch de beste instelling. Tussen haakjes het aantal trades.</p>")
    gcsv = []
    for v, g in gvs.items():
        h.append("<h3>%s</h3>" % _e(naam(v)))
        rijen = []
        for fd, rij, nr in zip(g["filter_dagen"], g["tabel"], g["aantallen"]):
            label = "n.v.t. (geen filter)" if fd is None else ("geen filter" if fd == 0 else "filter %d dagen" % fd)
            rijen.append([_e(label)] + ["%s <small>(%d)</small>" % (_e(fmt("expectancy_R", x)), n_) for x, n_ in zip(rij, nr)])
            gcsv.append([v, "" if fd is None else fd] + ["" if x is None else "%.4f" % x for x in rij])
        h.append(tabel(["filter_dagen \\ stop_factor"] + ["%.1f" % s for s in g["stop_factor"]], rijen))
    stops = next(iter(gvs.values()))["stop_factor"] if gvs else []
    schrijf_csv(map_ / "gevoeligheid.csv", ["variant", "filter_dagen"] + ["stop_%.1f" % s for s in stops], gcsv)

    if res.get("markt"):
        h.append("<h2>Marktstatistiek (alleen loggen, geen strategie)</h2><p class='muted'>Gemiddeld rendement van goud "
                 "overnacht (slot 13:30 gisteren → 08:20) en overdag (08:20 → 13:30), in basispunten (0,01%%). Overnight vasthouden "
                 "mag niet bij Topstep; dit is alleen om het overnacht/overdag-patroon uit de literatuur te volgen.</p>")
        h.append(tabel(["Jaar", "Overnacht (bp)", "t", "Overdag (bp)", "t", "Dagen"],
                       [[_e(r["jaar"]), _e("–" if r["nacht"] is None else "%+.1f" % r["nacht"]), _e(fmt("t_stat", r["nacht_t"])),
                         _e("–" if r["dag"] is None else "%+.1f" % r["dag"]), _e(fmt("t_stat", r["dag_t"])), _e(r["dag_n"])]
                        for r in res["markt"]]))

    h.append("<h2>Correlatie dag-P&amp;L (A) met andere bots</h2>")
    h.append(tabel(["Bot", "Correlatie", "Toelichting"], [[_e(n_), _e("–" if c is None else "%.2f" % c), _e(t)] for n_, c, t in res["correlaties"]]))
    h.append("<h2>Dagen zonder trade (hele periode)</h2>")
    tellers = {v: Counter(u["status"] for u in res[v]["uitkomsten"]) for v in vs}
    redenen = sorted({k for c in tellers.values() for k in c}, key=lambda k: -tellers["A"].get(k, 0))
    h.append(tabel(["Status / reden"] + vs, [[_e(k or "–")] + [_e(tellers[v].get(k, 0)) for v in vs] for k in redenen]))
    h.append("<h2>Rolls</h2><p>.v.0 wisselde %d keer van contract. Afwijkingen van de vaste regel van meer dan %d handelsdagen: %d.</p>"
             % (len(res.get("rolls", [])), strat["roll"]["max_afwijking_dagen_v0"], len(res.get("roll_afwijkingen", []))))
    if res.get("roll_afwijkingen"):
        h.append(tabel([".v.0-roll", "Vaste regel", "Verschil (handelsdagen)"],
                       [[_e(m["v0_roll"]), _e(m["regel_roll"]), _e(m["verschil_handelsdagen"])] for m in res["roll_afwijkingen"]]))
    h.append("<p class='muted'>CSV-bestanden in deze map: samenvatting.csv, trades_&lt;variant&gt;.csv, trades_A_stress.csv, "
             "gevoeligheid.csv, dag_pnl_A.csv.</p>")
    h.append("</main></body></html>")

    for var in vs:
        trade_csv(map_ / ("trades_%s.csv" % var), res[var]["trades"])
    trade_csv(map_ / "trades_A_stress.csv", a_s)
    dag = {}
    for t in a_tr:
        dag[t["datum"]] = dag.get(t["datum"], 0.0) + t["netto"]
    schrijf_csv(map_ / "dag_pnl_A.csv", ["datum", "pnl"], [[d, "%.2f" % p] for d, p in sorted(dag.items())])
    with open(map_ / "criteria.json", "w", encoding="utf-8") as f:
        json.dump({"oordeel": o["oordeel"], "datum": dt.date.today().isoformat(),
                   "criteria": [{"naam": n_, "ok": ok, "detail": d} for n_, ok, d in o["criteria"]],
                   "varianten": {v: {"oordeel": oo["oordeel"], "criteria": [{"naam": n_, "ok": ok, "detail": d}
                                                                           for n_, ok, d in oo["criteria"]]}
                                 for v, oo in oordelen.items()}}, f, indent=2, ensure_ascii=False)
    pad = map_ / "backtest.html"
    pad.write_text("".join(h), encoding="utf-8")
    return pad


def schrijf_live_rapport(pad, account, live, backtest, meldingen):
    """live/backtest = dicts met expectancy_R, winrate, vulgraad, slippage, trades."""
    def f(k, v):
        if v is None:
            return "–"
        if k in ("winrate", "vulgraad"):
            return "%.0f%%" % (100 * v)
        if k == "expectancy_R":
            return "%+.3fR" % v
        if k == "slippage":
            return "%+.2f ticks" % v
        if k == "t_stat":
            return "%.2f" % v
        return str(v)
    keys = [("trades", "Trades"), ("signalen", "Signalen"), ("expectancy_R", "Expectancy"), ("t_stat", "t-stat"),
            ("winrate", "Winrate"), ("vulgraad", "Vulgraad"), ("slippage", "Gem. slippage t.o.v. aanname")]
    h = ["<!doctype html><html lang='nl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         "<title>MGC live vs backtest</title><style>%s</style></head><body><main>" % CSS,
         "<h1>MGC live vs. backtest (%s)</h1><p class='sub'>Bijgewerkt %s.</p>" % (_e(account), dt.datetime.now().strftime("%Y-%m-%d %H:%M")),
         "<h2>Status: <span class='%s'>%s</span></h2>" % ("nogo" if live.get("status") == "NO-GO" else "go", _e(live.get("status", "actief")))]
    h.append(tabel(["", "Live", "Backtest (OOS, A)"], [[_e(l), _e(f(k, live.get(k))), _e(f(k, backtest.get(k)))] for k, l in keys]))
    if meldingen:
        h.append("<h2>Meldingen</h2><ul>" + "".join("<li>%s</li>" % _e(m) for m in meldingen) + "</ul>")
    h.append("</main></body></html>")
    Path(pad).parent.mkdir(parents=True, exist_ok=True)
    Path(pad).write_text("".join(h), encoding="utf-8")
