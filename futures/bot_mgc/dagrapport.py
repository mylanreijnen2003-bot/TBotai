"""Dagrapport: na elke handelsdag een overzicht van alle strategieën (vandaag én sinds de start).

Schrijft bot_mgc/reports/dagrapport.html (altijd de nieuwste) en een kopie in reports/dagrapporten/<datum>.html.
De live-bot maakt het automatisch na 13:35 ET en opent het in je browser. Zelf openen: dagrapport_mgc.bat.

Gebruik: python -m bot_mgc.dagrapport [--account mgc-paper] [--datum 2026-10-14] [--niet-openen]
"""
import argparse
import datetime as dt
import html
import json
import sys
from pathlib import Path

from .account import account_uit_trades
from .journal_mgc import lees
from .logboek import lees_signalen
from .rapport import CSS, KLEUREN, equity_svg, tabel
from .statistiek import fmt, geld, stats
from .strategie import variant_naam
from .tijd import nl_tijd

REDENEN = {
    "filter_zwak": "beweging kleiner dan normaal (filter)",
    "geen_richting": "geen richting (signaal precies 0)",
    "signalen_oneens": "ROD en ochtendsignaal oneens",
    "te_weinig_historie": "nog te weinig historie",
    "geen_data": "geen koers om 13:00",
    "geen_ochtenddata": "geen ochtendkoers (08:50)",
    "stop_te_klein": "stop kleiner dan 2,0 punten",
    "stop_te_groot": "stop te groot voor $200 risico",
    "gehalveerd_naar_0": "virtueel account te dicht bij de bodem",
    "weekstop": "weekstop (−$800 deze week)",
    "instap_te_laat": "geen koers vóór 13:02",
    "te_laat": "bot te laat gestart",
    "weekend": "weekend",
    "feestdag": "beursfeestdag",
    "vervroegde_sluiting": "vervroegde sluiting",
    "kerstperiode": "kerstperiode",
    "geen_trade_periode": "geen-tradeperiode",
    "roll_dag": "rolldag (wissel naar volgend contract)",
    "tijd": "tijdsuitstap 13:29",
    "stop": "stop geraakt",
    "noodrem": "noodrem (−$400)",
    "tijd_geen_bar": "geen 13:29-koers, laatste koers",
}


def _e(x):
    return html.escape(str(x))


def reden_tekst(r):
    return " + ".join(REDENEN.get(x, x) for x in str(r or "").split("+") if x) or "–"


def _trades(rows, account, setup):
    out = []
    for r in rows:
        if r.get("account") != account or r.get("setup") != setup:
            continue
        try:
            out.append({"datum": dt.date.fromisoformat(r["datum"]), "netto": float(r["netto_pnl"]),
                        "R": float(r["R"]) if r.get("R") else None, "mae": float(r.get("MAE_$") or 0),
                        "richting": 1 if r.get("richting") == "long" else -1, "instap": r.get("werkelijke_instap"),
                        "uitstap": r.get("uitstapprijs"), "uitstapreden": r.get("uitstapreden"),
                        "contracten": r.get("contracten"), "kosten": float(r.get("kosten") or 0),
                        "risico": float(r.get("risico_$") or 0)})
        except (KeyError, ValueError):
            continue
    return sorted(out, key=lambda t: t["datum"])


def _meldingen(map_, datum, account):
    """ALARM- en LET OP-regels van vandaag uit de logboeken van deze modus."""
    out = []
    for p in sorted((Path(map_) / "logs").glob("mgc_%s_%s.log" % (account.split("-")[-1], datum.isoformat()))):
        for regel in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if "[ALARM]" in regel or "[LET OP]" in regel:
                out.append(regel)
    return out[-30:]


def schrijf_dagrapport(datum, account, map_, strat, firm, kal=None, varianten=None):
    map_ = Path(map_)
    varianten = list(varianten or (strat.get("paper_varianten") if account == "mgc-paper" else ["A"]) or ["A"])
    rows = lees(map_ / "journal_bot.csv")
    sig = [r for r in lees_signalen(map_ / "logs", account) if r.get("datum") == datum.isoformat()]
    laatste = {}
    for r in sig:                       # laatste regel per variant telt (gevuld na eerder 'signaal')
        laatste[r.get("variant") or "A"] = r
    bt = {}
    bp = map_ / "reports" / "backtest_samenvatting.json"
    if bp.exists():
        try:
            bt = json.loads(bp.read_text(encoding="utf-8")).get("varianten", {})
        except ValueError:
            bt = {}
    trades = {v: _trades(rows, account, "G-" + v) for v in varianten}
    naam = lambda v: variant_naam(v, strat)  # noqa: E731

    h = ["<!doctype html><html lang='nl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         "<title>MGC dagrapport</title><style>%s</style></head><body><main>" % CSS]
    h.append("<h1>MGC-bot – dagrapport %s</h1>" % _e(datum.strftime("%d-%m-%Y")))
    venster = "%s–%s Nederlandse tijd" % (nl_tijd(datum, "13:00"), nl_tijd(datum, "13:29"))
    h.append("<p class='sub'>Account %s. Venster 13:00–13:29 New York-tijd (%s). Paper: live koersen, gesimuleerde fills, "
             "er gaat nooit een order naar de broker. Gemaakt %s.</p>" % (_e(account), _e(venster), dt.datetime.now().strftime("%d-%m-%Y %H:%M")))

    # ---------- vandaag ----------
    vandaag_trades = {v: [t for t in trades[v] if t["datum"] == datum] for v in varianten}
    n_trades = sum(len(x) for x in vandaag_trades.values())
    dag_pnl = sum(t["netto"] for x in vandaag_trades.values() for t in x)
    if not sig and not n_trades:
        reden = kal.redenen_geen_trade(datum) if kal is not None else []
        h.append("<h2>Vandaag</h2><p>%s</p>" % _e("Geen handelsdag: %s." % reden_tekst("+".join(reden)) if reden else
                                                 "Nog geen signalen voor vandaag (draaide de bot om 13:00 ET?)."))
    else:
        h.append("<h2>Vandaag: %d van %d strategieën handelden, samen %s</h2>" % (n_trades, len(varianten), _e(geld(dag_pnl))))
        rij0 = next(iter(laatste.values()), {})
        info = []
        if rij0.get("rod"):
            info.append("ROD %+.3f%%" % (100 * float(rij0["rod"])))
        if rij0.get("onfh"):
            info.append("ochtendsignaal %+.3f%%" % (100 * float(rij0["onfh"])))
        if info:
            h.append("<p class='muted'>Signalen om 13:00 ET: %s.</p>" % _e(", ".join(info)))
        rijen = []
        for v in varianten:
            r = laatste.get(v, {})
            tv = vandaag_trades[v]
            if tv:
                t = tv[-1]
                rijen.append([_e(naam(v)), _e("LONG" if t["richting"] > 0 else "SHORT"), _e(t["contracten"]),
                              _e("%s → %s" % (t["instap"], t["uitstap"])), _e(reden_tekst(t["uitstapreden"])),
                              "<span class='%s'>%s</span>" % ("go" if t["netto"] > 0 else "nogo", _e(geld(t["netto"]))),
                              _e(fmt("expectancy_R", t["R"]))])
            else:
                rijen.append([_e(naam(v)), "geen trade", "", "", _e(reden_tekst(r.get("reden") or r.get("status"))), "", ""])
        h.append(tabel(["Strategie", "Beslissing", "Contracten", "Instap → uitstap", "Uitstap / reden", "Netto", "R"], rijen))

    # ---------- sinds de start ----------
    alle = [t for v in varianten for t in trades[v]]
    if alle:
        start = min(t["datum"] for t in alle)
        h.append("<h2>Sinds de start (%s)</h2>" % _e(start.strftime("%d-%m-%Y")))
        rijen = []
        for v in varianten:
            tr = trades[v]
            m = stats(tr) if tr else {"trades": 0}
            acc = account_uit_trades(firm, [(t["datum"], t["netto"], t["mae"]) for t in tr])
            b = bt.get(v, {})
            rijen.append(["<i style='display:inline-block;width:10px;height:10px;border-radius:2px;background:%s;margin-right:6px'></i>%s"
                          % (KLEUREN.get(v, "var(--fg2)"), _e(naam(v))),
                          _e(m.get("trades", 0)), _e(fmt("winrate", m.get("winrate"))), _e(fmt("expectancy_R", m.get("expectancy_R"))),
                          _e(fmt("t_stat", m.get("t_stat"))), _e(fmt("netto_totaal", m.get("netto_totaal"))),
                          _e(fmt("max_dd", m.get("max_dd"))), _e(geld(acc.saldo)), _e(geld(acc.saldo - acc.bodem)),
                          _e(fmt("expectancy_R", b.get("expectancy_R")))])
        koppen = ["Strategie", "Trades", "Winrate", "Expectancy (R)", "t-stat", "Netto", "Max drawdown",
                  "Virtueel saldo", "Boven bodem", "Backtest (OOS)"]
        if not bt:      # geen backtest gedaan (besluit 3 okt 2026): kolom weglaten
            koppen = koppen[:-1]
            rijen = [r[:-1] for r in rijen]
        h.append(tabel(koppen, rijen))
        h.append(equity_svg({v: _cum(trades[v]) for v in varianten if trades[v]}, None,
                            namen={v: naam(v) for v in varianten}))
        # ---------- eindoordeel forward test ----------
        f = strat.get("forward_test", {})
        n_min = f.get("min_trades", 300)
        handelsdagen = len({r.get("datum") for r in lees_signalen(map_ / "logs", account) if r.get("status") != "te_laat"})
        rg = [v for v in strat.get("richtinggevende_varianten", ["A"]) if v in varianten]
        h.append("<h2>Eindoordeel forward test</h2><p class='muted'>Vooraf vastgelegde lat (HYPOTHESIS.md). Pas bij %d trades "
                 "geeft een strategie een oordeel; tot dan is alles ruis.</p>" % n_min)
        rijen = []
        for v in rg:
            status, lijst = forward_oordeel(trades, strat, v)
            nog = _nog_maanden(trades[v], n_min, handelsdagen)
            st = ("<span class='%s'>%s</span>" % ("go" if status == "GO" else "nogo", status) if status != "loopt" else
                  _e("loopt%s" % ("" if nog is None else " (nog ± %.0f maanden)" % nog)))
            rijen.append([_e(naam(v)), st] + [("<span class='go'>✓</span> " if ok else "<span class='muted'>·</span> ") + _e(d)
                                              for _, ok, d in lijst])
        h.append(tabel(["Strategie", "Oordeel"] + [x[0] for x in forward_oordeel(trades, strat, rg[0])[1]] if rg else [], rijen))
        if "R" in trades:
            from .backtest import controle_r
            rt = trades["R"]
            if len(rt) >= f.get("controle_r_min_trades", 100):
                cr = controle_r(rt)
                h.append("<p><b>Controle R</b> (%d trades): %s</p>" % (cr["trades"], _e(cr["uitleg"])))
            else:
                h.append("<p class='muted'>Controle R: vanaf %d R-trades (nu %d).</p>" % (f.get("controle_r_min_trades", 100), len(rt)))
        h.append("<p class='muted'>Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag). Elke strategie "
                 "heeft een eigen virtueel 50K-account (bodem $48.000, trailt mee). Een paar maanden paper zegt iets over de "
                 "uitvoering, niet over de voorsprong: daarvoor zijn honderden trades nodig. Vergelijk A, C, D en E vooral met "
                 "B (altijd long) en R (willekeurige richting).</p>")

    meld = _meldingen(map_, datum, account)
    if meld:
        h.append("<h2>Meldingen vandaag</h2><ul>" + "".join("<li><small>%s</small></li>" % _e(x) for x in meld) + "</ul>")
    h.append("</main></body></html>")

    rep = map_ / "reports"
    (rep / "dagrapporten").mkdir(parents=True, exist_ok=True)
    tekst = "".join(h)
    (rep / "dagrapporten" / ("%s_%s.html" % (datum.isoformat(), account))).write_text(tekst, encoding="utf-8")
    pad = rep / "dagrapport.html"
    pad.write_text(tekst, encoding="utf-8")
    return pad


def forward_oordeel(trades, strat, var):
    """Eindoordeel van de forward test voor één strategie (lat uit strategy.json 'forward_test' / HYPOTHESIS.md).
    -> (status, [(naam, ok, detail)]). Status 'loopt' zolang er te weinig trades zijn."""
    f = strat.get("forward_test", {})
    tr = trades.get(var, [])
    m = stats(tr) if tr else {"trades": 0}
    ex = m.get("expectancy_R")
    exb = (stats(trades["B"]).get("expectancy_R") if trades.get("B") else None)
    exr = (stats(trades["R"]).get("expectancy_R") if trades.get("R") else None)
    n_min = f.get("min_trades", 300)

    def v(x, s_):
        return "–" if x is None else s_ % x
    lijst = [
        ("≥ %d trades" % n_min, m["trades"] >= n_min, "%d trades" % m["trades"]),
        ("expectancy ≥ +%.2fR" % f.get("min_expectancy_R", 0.05), ex is not None and ex >= f.get("min_expectancy_R", 0.05), v(ex, "%+.3fR")),
        ("t-stat ≥ %.2f" % f.get("min_t_stat", 2.5), (m.get("t_stat") or -9) >= f.get("min_t_stat", 2.5), v(m.get("t_stat"), "%.2f")),
        ("profit factor ≥ %.2f" % f.get("min_profit_factor", 1.15), (m.get("profit_factor") or 0) >= f.get("min_profit_factor", 1.15),
         v(m.get("profit_factor"), "%.2f")),
        ("max drawdown < $%d" % f.get("max_drawdown_usd", 2000), m.get("max_dd") is not None and m["max_dd"] < f.get("max_drawdown_usd", 2000),
         v(m.get("max_dd"), "$%.0f")),
        ("beter dan B (altijd long)", ex is not None and exb is not None and ex > exb, "B %s" % v(exb, "%+.3fR")),
        ("beter dan R (willekeurig)", ex is not None and exr is not None and ex > exr, "R %s" % v(exr, "%+.3fR")),
    ]
    if m["trades"] < n_min:
        return "loopt", lijst
    return ("GO" if all(ok for _, ok, _ in lijst) else "NO-GO"), lijst


def _nog_maanden(tr, n_min, handelsdagen):
    """Grove schatting hoeveel maanden het nog duurt tot n_min trades, op basis van het tempo tot nu toe."""
    if not tr or handelsdagen <= 0:
        return None
    per_dag = len(tr) / float(handelsdagen)
    rest = max(0, n_min - len(tr))
    return rest / per_dag / 21.0 if per_dag > 0 else None


def _laatste_per_variant(map_, account, datum):
    laatste = {}
    for r in lees_signalen(Path(map_) / "logs", account):
        if r.get("datum") == datum.isoformat():
            laatste[r.get("variant") or "A"] = r
    return laatste


def schrijf_dagrapport_md(datum, account, map_, strat, firm, kal=None):
    """Dagrapport als Markdown (DAGRAPPORT.md): leesbaar op github.com en in de GitHub-app op je telefoon."""
    map_ = Path(map_)
    varianten = list(strat.get("paper_varianten") or ["A"])
    rows = lees(map_ / "journal_bot.csv")
    trades = {v: _trades(rows, account, "G-" + v) for v in varianten}
    laatste = _laatste_per_variant(map_, account, datum)
    naam = lambda v: variant_naam(v, strat)  # noqa: E731
    f = strat.get("forward_test", {})
    n_min = f.get("min_trades", 300)
    m = ["# MGC-bot – dagrapport %s" % datum.strftime("%d-%m-%Y"), "",
         "Forward test (paper) op gratis Yahoo-koersen. Venster 13:00–13:29 New York-tijd (%s–%s NL). Er gaat nooit een "
         "order naar een broker. Bijgewerkt %s UTC." % (nl_tijd(datum, "13:00"), nl_tijd(datum, "13:29"),
                                                        dt.datetime.now(dt.timezone.utc).strftime("%d-%m-%Y %H:%M")), ""]
    m += ["## Vandaag", ""]
    vt = {v: [t for t in trades[v] if t["datum"] == datum] for v in varianten}
    if not laatste and not any(vt.values()):
        reden = kal.redenen_geen_trade(datum) if kal is not None else []
        m.append("Geen handelsdag: %s." % reden_tekst("+".join(reden)) if reden else "Nog geen signalen voor deze dag.")
    else:
        r0 = next(iter(laatste.values()), {})
        sig = []
        if r0.get("rod"):
            sig.append("ROD %+.3f%%" % (100 * float(r0["rod"])))
        if r0.get("onfh"):
            sig.append("ochtend %+.3f%%" % (100 * float(r0["onfh"])))
        if sig:
            m += ["Signalen om 13:00 ET: %s." % ", ".join(sig), ""]
        m += ["| Strategie | Beslissing | Contracten | Instap → uitstap | Uitstap / reden | Netto | R |", "|---|---|---:|---|---|---:|---:|"]
        for v in varianten:
            if vt[v]:
                t = vt[v][-1]
                m.append("| %s | %s | %s | %s → %s | %s | %s | %s |" % (naam(v), "LONG" if t["richting"] > 0 else "SHORT",
                         t["contracten"], t["instap"], t["uitstap"], reden_tekst(t["uitstapreden"]), geld(t["netto"]),
                         fmt("expectancy_R", t["R"])))
            else:
                r = laatste.get(v, {})
                m.append("| %s | geen trade | | | %s | | |" % (naam(v), reden_tekst(r.get("reden") or r.get("status"))))
    alle = [t for v in varianten for t in trades[v]]
    m += ["", "## Sinds de start", ""]
    if not alle:
        m.append("Nog geen trades.")
    else:
        m += ["| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for v in varianten:
            tr = trades[v]
            st = stats(tr) if tr else {"trades": 0}
            acc = account_uit_trades(firm, [(t["datum"], t["netto"], t["mae"]) for t in tr])
            m.append("| %s | %d | %s | %s | %s | %s | %s | %s |" % (naam(v), st.get("trades", 0), fmt("winrate", st.get("winrate")),
                     fmt("expectancy_R", st.get("expectancy_R")), fmt("t_stat", st.get("t_stat")),
                     fmt("netto_totaal", st.get("netto_totaal")), fmt("max_dd", st.get("max_dd")), geld(acc.saldo)))
    handelsdagen = len({r.get("datum") for r in lees_signalen(map_ / "logs", account) if r.get("reden") not in ("gemist",)})
    rg = [v for v in strat.get("richtinggevende_varianten", ["A"]) if v in varianten]
    m += ["", "## Eindoordeel forward test", "",
          "Pas bij %d trades krijgt een strategie GO of NO-GO (lat in `bot_mgc/HYPOTHESIS.md`). Tot dan is het ruis." % n_min, "",
          "| Strategie | Oordeel | " + " | ".join(x[0] for x in forward_oordeel(trades, strat, rg[0])[1]) + " |",
          "|---|---|" + "---|" * len(forward_oordeel(trades, strat, rg[0])[1])]
    for v in rg:
        status, lijst = forward_oordeel(trades, strat, v)
        nog = _nog_maanden(trades[v], n_min, handelsdagen)
        st = status if status != "loopt" else ("loopt" + ("" if nog is None else " (nog ± %.0f mnd)" % nog))
        m.append("| %s | **%s** | %s |" % (naam(v), st, " | ".join(("✓ " if ok else "") + d for _, ok, d in lijst)))
    if "R" in trades and len(trades["R"]) >= f.get("controle_r_min_trades", 100):
        from .backtest import controle_r
        m += ["", "**Controle R:** %s" % controle_r(trades["R"])["uitleg"]]
    meld = _meldingen(map_, datum, account)
    if meld:
        m += ["", "## Meldingen", ""] + ["- %s" % x for x in meld]
    m += ["", "Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). B = altijd long, "
          "R = willekeurige richting; A, C, D en E moeten die allebei verslaan.", ""]
    pad = map_ / "DAGRAPPORT.md"
    pad.write_text("\n".join(m), encoding="utf-8")
    (map_ / "reports" / "dagrapporten").mkdir(parents=True, exist_ok=True)
    (map_ / "reports" / "dagrapporten" / ("%s.md" % datum.isoformat())).write_text("\n".join(m), encoding="utf-8")
    return pad


def telegram_tekst(datum, account, map_, strat, dagen):
    """Korte melding: per strategie de uitkomst van de laatst verwerkte dag en het totaal sinds de start."""
    varianten = list(strat.get("paper_varianten") or ["A"])
    rows = lees(Path(map_) / "journal_bot.csv")
    trades = {v: _trades(rows, account, "G-" + v) for v in varianten}
    laatste = _laatste_per_variant(map_, account, datum)
    regels = ["MGC forward test – %s%s" % (datum.strftime("%d-%m-%Y"),
                                           "" if len(dagen) <= 1 else " (%d dagen verwerkt)" % len(dagen))]
    for v in varianten:
        vt = [t for t in trades[v] if t["datum"] == datum]
        tot = sum(t["netto"] for t in trades[v])
        if vt:
            t = vt[-1]
            nu = "%s %s (%s)" % ("long" if t["richting"] > 0 else "short", geld(t["netto"]), fmt("expectancy_R", t["R"]))
        else:
            nu = "geen trade" if laatste.get(v) else "–"
        regels.append("%s: %s | totaal %s, %d trades" % (v, nu, geld(tot), len(trades[v])))
    return "\n".join(regels)


def _cum(trades):
    eq, out = 0.0, []
    for t in trades:
        eq += t["netto"]
        out.append((t["datum"], eq))
    return out


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from .instellingen import BOT, load_calendar, load_firm, load_strategy
    from .kalender_mgc import Kalender
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="mgc-paper")
    ap.add_argument("--datum", default=None)
    ap.add_argument("--niet-openen", action="store_true")
    a = ap.parse_args(argv)
    strat = load_strategy()
    datum = dt.date.fromisoformat(a.datum) if a.datum else _laatste_datum(BOT, a.account) or dt.date.today()
    pad = schrijf_dagrapport(datum, a.account, BOT, strat, load_firm("topstep_50k"), Kalender(load_calendar(), strat))
    print("Dagrapport: %s" % pad)
    if not a.niet_openen:
        import webbrowser
        webbrowser.open(pad.resolve().as_uri())
    return 0


def _laatste_datum(map_, account):
    sig = lees_signalen(Path(map_) / "logs", account)
    ds = [r["datum"] for r in sig if r.get("datum")]
    return dt.date.fromisoformat(max(ds)) if ds else None


if __name__ == "__main__":
    sys.exit(main())
