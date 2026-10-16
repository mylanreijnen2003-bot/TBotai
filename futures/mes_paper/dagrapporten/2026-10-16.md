# MES-bot – dagrapport 16-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 16-10-2026 23:36 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: pullback bleef te ver boven/onder de VWAP | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | short, tijdsuitstap | 5 | 15:30 7701.75 → 7700.75 | $19 | +0.094 |
| C – ROD-momentum laatste half uur, zonder filter | short, tijdsuitstap | 4 | 15:30 7701.75 → 7705.75 | −$85 | -0.424 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, tijdsuitstap | 4 | 15:30 7701.75 → 7705.75 | −$85 | -0.424 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | short, doel geraakt | 3 | 09:35 7792.5 → 7682.5 | $1.646 | +9.978 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | short, tijdsuitstap | 1 | 11:30 7757.0 → 7705.75 | $255 | +2.148 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 10 | 30% | -0.368 | -2.27 | −$736 | $755 | $49.264 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 10 | 10% | -0.451 | -4.28 | −$738 | $738 | $49.262 | loopt (10/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 10 | 10% | -0.416 | -3.54 | −$668 | $668 | $49.332 | loopt (10/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 10 | 20% | +0.445 | 0.39 | $868 | $1.323 | $50.868 | loopt (10/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 8 | 50% | +0.701 | 1.04 | $974 | $329 | $50.974 | loopt (8/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
