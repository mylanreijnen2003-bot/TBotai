# MES-bot – dagrapport 23-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 23-10-2026 23:51 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: geen duidelijke trend om 14:45 | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | long, stop geraakt | 5 | 15:30 7667.25 → 7659.0 | −$212 | -1.062 |
| C – ROD-momentum laatste half uur, zonder filter | short, tijdsuitstap | 3 | 15:30 7666.75 → 7662.25 | $64 | +0.405 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, tijdsuitstap | 3 | 15:30 7666.75 → 7662.25 | $64 | +0.405 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | long, stop geraakt | 5 | 09:35 7662.0 → 7658.75 | −$87 | -1.165 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | geen trade: koers bleef binnen de ruisband | | | | |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 15 | 33% | -0.330 | -1.96 | −$992 | $992 | $49.009 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 15 | 27% | -0.360 | -3.11 | −$911 | $975 | $49.089 | loopt (15/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 15 | 27% | -0.337 | -2.82 | −$841 | $905 | $49.159 | loopt (15/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 15 | 13% | -0.067 | -0.09 | $209 | $1.323 | $50.209 | loopt (15/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 14 | 43% | +0.300 | 0.74 | $782 | $329 | $50.782 | loopt (14/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
