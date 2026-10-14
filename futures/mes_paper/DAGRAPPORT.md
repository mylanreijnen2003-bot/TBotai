# MES-bot – dagrapport 13-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 14-10-2026 00:19 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: geen duidelijke trend om 14:45 | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | long, tijdsuitstap | 5 | 15:30 7858.0 → 7855.25 | −$75 | -0.374 |
| C – ROD-momentum laatste half uur, zonder filter | long, tijdsuitstap | 4 | 15:30 7858.0 → 7854.5 | −$75 | -0.374 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, tijdsuitstap | 4 | 15:30 7857.5 → 7855.0 | $45 | +0.226 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | long, stop geraakt | 5 | 09:35 7852.5 → 7846.5 | −$156 | -1.086 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | geen trade: koers bleef binnen de ruisband | | | | |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 7 | 14% | -0.486 | -2.28 | −$680 | $680 | $49.320 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 7 | 0% | -0.579 | -5.37 | −$648 | $648 | $49.352 | loopt (7/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 7 | 14% | -0.494 | -3.13 | −$528 | $573 | $49.472 | loopt (7/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 7 | 14% | -0.486 | -0.80 | −$440 | $984 | $49.560 | loopt (7/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 5 | 20% | -0.254 | -0.74 | −$154 | $329 | $49.846 | loopt (5/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
