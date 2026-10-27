# MES-bot – dagrapport 26-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 27-10-2026 00:26 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | long, tijdsuitstap | 3 | 15:15 7715.25 → 7712.5 | −$45 | -0.279 |
| B – eerste half uur → laatste half uur (benchmark uit plan) | long, tijdsuitstap | 5 | 15:30 7715.75 → 7712.5 | −$87 | -0.437 |
| C – ROD-momentum laatste half uur, zonder filter | long, tijdsuitstap | 3 | 15:30 7715.75 → 7713.5 | −$37 | -0.243 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | long, tijdsuitstap | 3 | 15:30 7715.75 → 7713.5 | −$37 | -0.243 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | long, tijdsuitstap | 3 | 09:35 7688.0 → 7713.5 | $379 | +2.245 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 2 | 10:30 7709.75 → 7711.75 | $18 | +0.111 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, tijdsuitstap | 1 | 15:30 7715.75 → 7713.5 | −$12 | -0.088 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 1 | 0% | -0.279 | – | −$45 | $45 | $49.955 | loopt (1/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 16 | 31% | -0.337 | -2.14 | −$1.079 | $1.079 | $48.921 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 16 | 25% | -0.352 | -3.25 | −$948 | $975 | $49.052 | loopt (16/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 16 | 25% | -0.331 | -2.96 | −$878 | $905 | $49.122 | loopt (16/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 16 | 19% | +0.077 | 0.11 | $588 | $1.323 | $50.588 | loopt (16/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 16 | 44% | +0.264 | 0.74 | $787 | $329 | $50.787 | loopt (16/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
