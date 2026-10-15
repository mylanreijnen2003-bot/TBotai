# MES-bot – dagrapport 15-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 15-10-2026 23:42 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: geen instapsignaal na een pullback | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | short, tijdsuitstap | 5 | 15:30 7793.5 → 7793.25 | $0 | +0.001 |
| C – ROD-momentum laatste half uur, zonder filter | long, tijdsuitstap | 4 | 15:30 7794.0 → 7794.75 | $10 | +0.052 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, tijdsuitstap | 4 | 15:30 7793.5 → 7795.25 | −$40 | -0.205 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | short, stop geraakt | 3 | 09:35 7729.0 → 7740.5 | −$176 | -1.044 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, tijdsuitstap | 1 | 15:30 7794.0 → 7794.75 | $3 | +0.024 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 9 | 22% | -0.419 | -2.44 | −$755 | $755 | $49.245 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 9 | 11% | -0.454 | -3.86 | −$653 | $663 | $49.347 | loopt (9/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 9 | 11% | -0.415 | -3.16 | −$583 | $583 | $49.417 | loopt (9/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 9 | 11% | -0.614 | -1.30 | −$779 | $1.323 | $49.221 | loopt (9/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 7 | 43% | +0.494 | 0.67 | $719 | $329 | $50.719 | loopt (7/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
