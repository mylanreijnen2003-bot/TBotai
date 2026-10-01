# Learnings — observaties en hypotheses

Regels:
- Hier komen **alleen** feiten en hypotheses. Niets hiervan wordt automatisch toegepast.
- Een regel wijzigen mag pas bij ≥30 trades in een vergelijkbare situatie, hooguit één keer per maand, en alleen na goedkeuring.
- Elke wijziging = nieuwe strategieversie (v2 …) die opnieuw vanaf nul getest wordt. Resultaten van versies worden niet opgeteld.
- Houd bij hoeveel varianten er in totaal zijn geprobeerd (voor de deflated Sharpe).

Aantal geteste varianten tot nu toe: 5 (S1–S3 vanaf 30 sept, S4–S5 vanaf 2 okt 2026).

## Log
<!-- Formaat: YYYY-MM-DD — observatie/hypothese — onderbouwing (aantal trades, periode) -->
- 2026-09-30 — Observatie: S1 is in de backtest gemiddeld maar ~8% belegd (max per munt ≈ 1/15 × 0,25/σ90). De lage drawdown komt dus grotendeels uit cash aanhouden. — Backtest 2020-03 t/m 2026-09, 0,30% kosten.
- 2026-09-30 — Hypothese (kandidaat v2, NIET toepassen in v1): vol-target op portefeuilleniveau (25% voor het hele mandje) i.p.v. per munt zou de blootstelling dichter bij het paper brengen. Pas beoordelen na ≥2 jaar v1-data en als aparte variant tellen.
- 2026-10-01 — Idee (eigenaar): macromodel als regimefilter — niet handelen als de langetermijntrend negatief is. Testen als aparte variant (bv. S4 + macrofilter tegen S4), alleen met een point-in-time signaal (zoals het model het op elke dag zou hebben gegeven).
