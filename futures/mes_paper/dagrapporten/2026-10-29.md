# MES-bot – dagrapport 29-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 30-10-2026 01:00 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | short, stop geraakt | 4 | 15:45 7739.0 → 7748.0 | −$185 | -1.056 |
| B – eerste half uur → laatste half uur (benchmark uit plan) | short, stop geraakt | 5 | 15:30 7741.5 → 7749.75 | −$212 | -1.062 |
| C – ROD-momentum laatste half uur, zonder filter | short, stop geraakt | 3 | 15:30 7741.5 → 7752.0 | −$161 | -1.048 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, stop geraakt | 3 | 15:30 7741.5 → 7752.0 | −$161 | -1.048 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | short, stop geraakt | 2 | 09:35 7736.75 → 7752.0 | −$155 | -1.033 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | geen trade: koers bleef binnen de ruisband | | | | |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 2 | 0% | -0.667 | -1.72 | −$230 | $230 | $49.770 | loopt (2/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 18 | 28% | -0.418 | -2.78 | −$1.504 | $1.504 | $48.496 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 18 | 22% | -0.383 | -3.68 | −$1.149 | $1.149 | $48.851 | loopt (18/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 18 | 22% | -0.364 | -3.39 | −$1.079 | $1.079 | $48.921 | loopt (18/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 18 | 17% | -0.050 | -0.08 | $302 | $1.323 | $50.302 | loopt (18/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 17 | 41% | +0.214 | 0.63 | $718 | $352 | $50.718 | loopt (17/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
