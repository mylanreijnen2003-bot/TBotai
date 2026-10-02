# Learnings — observaties en hypotheses

Regels:
- Hier komen **alleen** feiten en hypotheses. Niets hiervan wordt automatisch toegepast.
- Een regel wijzigen mag pas bij ≥30 trades in een vergelijkbare situatie, hooguit één keer per maand, en alleen na goedkeuring.
- Elke wijziging = nieuwe strategieversie (v2 …) die opnieuw vanaf nul getest wordt. Resultaten van versies worden niet opgeteld.
- Houd bij hoeveel varianten er in totaal zijn geprobeerd (voor de deflated Sharpe).

Aantal geteste varianten tot nu toe: 12 (S1–S10, M1, M2; S5–S9 afgevallen).

## Log
<!-- Formaat: YYYY-MM-DD — observatie/hypothese — onderbouwing (aantal trades, periode) -->
- 2026-09-30 — Observatie: S1 is in de backtest gemiddeld maar ~8% belegd (max per munt ≈ 1/15 × 0,25/σ90). De lage drawdown komt dus grotendeels uit cash aanhouden. — Backtest 2020-03 t/m 2026-09, 0,30% kosten.
- 2026-09-30 — Hypothese (kandidaat v2, NIET toepassen in v1): vol-target op portefeuilleniveau (25% voor het hele mandje) i.p.v. per munt zou de blootstelling dichter bij het paper brengen. Pas beoordelen na ≥2 jaar v1-data en als aparte variant tellen.
- 2026-10-01 — Idee (eigenaar): macromodel als regimefilter — niet handelen als de langetermijntrend negatief is. Testen als aparte variant (bv. S4 + macrofilter tegen S4), alleen met een point-in-time signaal (zoals het model het op elke dag zou hebben gegeven).
- 2026-10-01 — Backtest na data-fix (incl. later genoteerde munten). S4: CAGR 29,7%, max drawdown −45% (B2: 12,7% / −90%). S5: 27,2% / −47% (B1: 39,9% / −74%). Holdout vanaf apr 2025: S4 +4,2% en S1 +2,5% tegen B1 −2,2% en B2 −18,7%.
- 2026-10-01 — S6 (4-uurs) haalt H6 niet: bij 0,30% kosten −1,8%/jaar (2021-08 t/m 2026-09), holdout −30%/jaar. 772 trades, 30% winstgevend, gem. +0,10% per trade na kosten. Bij 0,15% (limietorders) +13,9%/jaar, bij 0,60% −27%/jaar: de kosten bepalen de uitkomst. Volgens de vooraf afgesproken regel stoppen.
- 2026-10-01 — Cursussen Miles Deutscher (7-daagse AI-tradingbot + Free Markets Assets Library) doorgenomen. Niet overgenomen: (1) "stop na één verlies"-geheugen (hun eigen veiligheidsgids raadt dit af; trendvolgen verdient juist aan weinig grote winnaars), (2) een LLM in de beslisketen (TradingAgents, Jev, Claude-bias; geen bewijs na kosten, uitkomsten niet herhaalbaar), (3) EMA 9/21 op BTC-dag ("beste van 12" = selectie-bias; lijkt op S5, dat H5 niet haalde). Wel overgenomen, zonder regelwijziging: wekelijkse controle live vs. dezelfde code, meldingen bij gemiste dagen en oude koersen, tests met vooraf uitgerekende uitkomst. Aantal geteste varianten blijft 6.
- 2026-10-01 — Snelle verkenning BTC-cyclusfilters (0,30% kosten, sept 2020 t/m sept 2026): BTC vasthouden 42%/jaar (−74%); boven SMA100 43% (−54%); SMA200 36% (−62%); SMA350 18% (−51%). Perfecte timing achteraf ×45 (88%/jaar) als plafond. Vanaf feb 2021 haalt BTC vasthouden maar 8,7%/jaar: de startdatum bepaalt veel. Daarom S10 als ensemble van alle drie, niet de beste losse.
- 2026-10-01 — Backtest H7–H10 (results/hypotheses.md): alleen S10 geslaagd. S8 had het hoogste rendement (44,7%/jaar gemiddeld over weekdagen, Sharpe 1,16) maar een drawdown van −40,6% boven de vooraf gestelde 35%; spreiding over uitvoeringsdag 37–54% laat zien hoeveel toeval erin zit. S9 correleert 0,87 met S4 en voegt weinig toe.
- 2026-10-02 — Mixen verkend op de backtest-equity (maandelijks herbalanceren): S4+S8+S10 41,6%/jaar, max drawdown −36,9%; S1+S8 29,8%, −25,0%. Wisselen tussen strategieën op BTC-regime gaf wisselende uitkomsten (−38% tot −56% drawdown) en is daarom niet gekozen.
