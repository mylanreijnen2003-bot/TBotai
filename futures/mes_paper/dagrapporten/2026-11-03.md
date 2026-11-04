# MES-bot – dagrapport 03-11-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 04-11-2026 01:23 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: geen duidelijke trend om 14:45 | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | long, stop geraakt | 2 | 15:30 7597.75 → 7589.5 | −$85 | -1.062 |
| C – ROD-momentum laatste half uur, zonder filter | long, tijdsuitstap | 3 | 15:30 7597.75 → 7597.0 | −$15 | -0.086 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | long, tijdsuitstap | 1 | 15:30 7597.75 → 7597.0 | −$5 | -0.086 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | long, tijdsuitstap | 1 | 09:35 7588.25 → 7597.0 | $43 | +0.709 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 4 | 10:00 7591.25 → 7598.75 | $145 | +0.784 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 1 | 11:00 7615.5 → 7606.0 | −$49 | -0.453 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 1 | 12:30 7610.0 → 7605.75 | −$22 | -0.191 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 2 | 0% | -0.667 | -1.72 | −$230 | $230 | $49.770 | loopt (2/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 21 | 24% | -0.510 | -3.70 | −$1.758 | $1.758 | $48.242 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 21 | 24% | -0.278 | -1.78 | −$1.002 | $1.324 | $48.998 | loopt (21/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 21 | 19% | -0.416 | -4.03 | −$1.420 | $1.420 | $48.580 | loopt (21/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 21 | 19% | -0.379 | -0.59 | −$693 | $1.603 | $49.307 | loopt (21/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 24 | 38% | -0.090 | -0.28 | $14 | $1.241 | $50.014 | loopt (24/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
