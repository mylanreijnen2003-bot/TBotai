# Learnings — observaties en hypotheses

Regels:
- Hier komen **alleen** feiten en hypotheses. Niets hiervan wordt automatisch toegepast.
- Een regel wijzigen mag pas bij ≥30 trades in een vergelijkbare situatie, hooguit één keer per maand, en alleen na goedkeuring.
- Elke wijziging = nieuwe strategieversie (v2 …) die opnieuw vanaf nul getest wordt. Resultaten van versies worden niet opgeteld.
- Houd bij hoeveel varianten er in totaal zijn geprobeerd (voor de deflated Sharpe).

Aantal geteste varianten tot nu toe: 3 (S1, S2, S3 in v1).

## Log
<!-- Formaat: YYYY-MM-DD — observatie/hypothese — onderbouwing (aantal trades, periode) -->
- 2026-09-30 — Observatie: S1 is in de backtest gemiddeld maar ~8% belegd (max per munt ≈ 1/15 × 0,25/σ90). De lage drawdown komt dus grotendeels uit cash aanhouden. — Backtest 2020-03 t/m 2026-09, 0,30% kosten.
- 2026-09-30 — Hypothese (kandidaat v2, NIET toepassen in v1): vol-target op portefeuilleniveau (25% voor het hele mandje) i.p.v. per munt zou de blootstelling dichter bij het paper brengen. Pas beoordelen na ≥2 jaar v1-data en als aparte variant tellen.
