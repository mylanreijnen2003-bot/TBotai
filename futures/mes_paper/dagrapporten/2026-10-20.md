# MES-bot – dagrapport 20-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 20-10-2026 23:53 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: geen duidelijke trend om 14:45 | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | long, tijdsuitstap | 5 | 15:30 7749.5 → 7752.75 | $75 | +0.376 |
| C – ROD-momentum laatste half uur, zonder filter | long, tijdsuitstap | 3 | 15:30 7749.5 → 7753.0 | $49 | +0.318 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | long, tijdsuitstap | 3 | 15:30 7749.5 → 7753.0 | $49 | +0.318 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | short, stop geraakt | 5 | 09:35 7723.0 → 7727.5 | −$119 | -1.116 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 4 | 10:00 7748.0 → 7754.25 | $120 | +0.632 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 1 | 13:30 7764.0 → 7760.25 | −$20 | -0.147 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 12 | 42% | -0.187 | -1.00 | −$448 | $755 | $49.552 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 12 | 17% | -0.437 | -3.60 | −$889 | $938 | $49.111 | loopt (12/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 12 | 17% | -0.408 | -3.17 | −$819 | $868 | $49.181 | loopt (12/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 12 | 17% | +0.186 | 0.19 | $612 | $1.323 | $50.612 | loopt (12/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 11 | 45% | +0.536 | 1.09 | $1.051 | $329 | $51.051 | loopt (11/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
