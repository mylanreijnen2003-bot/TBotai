# MES-bot – dagrapport 12-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 13-10-2026 02:35 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: geen instapsignaal na een pullback | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | short, stop geraakt | 5 | 15:30 7849.25 → 7857.5 | −$212 | -1.062 |
| C – ROD-momentum laatste half uur, zonder filter | short, tijdsuitstap | 3 | 15:30 7849.25 → 7857.5 | −$127 | -0.829 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, tijdsuitstap | 3 | 15:30 7849.25 → 7857.5 | −$127 | -0.829 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | long, stop geraakt | 5 | 09:35 7864.5 → 7861.75 | −$75 | -1.198 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | geen trade: koers bleef binnen de ruisband | | | | |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 6 | 17% | -0.504 | -2.01 | −$605 | $605 | $49.395 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 6 | 0% | -0.614 | -5.06 | −$573 | $573 | $49.427 | loopt (6/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 6 | 0% | -0.614 | -5.06 | −$573 | $573 | $49.427 | loopt (6/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 6 | 17% | -0.386 | -0.54 | −$284 | $828 | $49.716 | loopt (6/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 5 | 20% | -0.254 | -0.74 | −$154 | $329 | $49.846 | loopt (5/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
