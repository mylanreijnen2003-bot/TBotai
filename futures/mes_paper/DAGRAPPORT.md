# MES-bot – dagrapport 04-11-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 05-11-2026 01:27 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: geen duidelijke trend om 14:45 | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | long, stop geraakt | 2 | 15:30 7732.75 → 7724.5 | −$85 | -1.062 |
| C – ROD-momentum laatste half uur, zonder filter | long, stop geraakt | 3 | 15:30 7732.75 → 7721.75 | −$169 | -1.046 |
| D – ROD-momentum laatste half uur, filter | long, stop geraakt | 3 | 15:30 7732.75 → 7721.75 | −$169 | -1.046 |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | long, stop geraakt | 1 | 15:30 7732.75 → 7721.75 | −$56 | -1.046 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | short, stop geraakt | 1 | 09:35 7682.0 → 7697.5 | −$79 | -1.032 |
| R – willekeurige richting op de dagen van D (controle) | long, stop geraakt | 3 | 15:30 7732.75 → 7721.75 | −$169 | -1.046 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, stop geraakt | 4 | 10:00 7726.5 → 7716.75 | −$200 | -1.052 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 1 | 10:30 7719.25 → 7714.25 | −$26 | -0.238 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, tijdsuitstap | 1 | 12:00 7739.75 → 7719.25 | −$104 | -0.715 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 2 | 0% | -0.667 | -1.72 | −$230 | $230 | $49.770 | loopt (2/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 22 | 23% | -0.535 | -4.00 | −$1.843 | $1.843 | $48.157 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 22 | 23% | -0.313 | -2.04 | −$1.170 | $1.324 | $48.830 | loopt (22/300 trades) |
| D – ROD-momentum laatste half uur, filter | 1 | 0% | -1.046 | – | −$169 | $169 | $49.831 | loopt (1/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 22 | 18% | -0.445 | -4.33 | −$1.477 | $1.477 | $48.523 | loopt (22/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 22 | 18% | -0.409 | -0.66 | −$771 | $1.639 | $49.229 | loopt (22/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 1 | 0% | -1.046 | – | −$169 | $169 | $49.831 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 27 | 33% | -0.154 | -0.54 | −$316 | $1.387 | $49.684 | loopt (27/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
