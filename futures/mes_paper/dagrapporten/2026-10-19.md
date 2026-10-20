# MES-bot – dagrapport 19-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 20-10-2026 00:21 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: geen duidelijke trend om 14:45 | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | short, tijdsuitstap | 5 | 15:30 7749.25 → 7740.5 | $213 | +1.063 |
| C – ROD-momentum laatste half uur, zonder filter | long, stop geraakt | 4 | 15:30 7749.75 → 7740.0 | −$200 | -1.052 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | long, stop geraakt | 4 | 15:30 7749.75 → 7740.0 | −$200 | -1.052 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | long, stop geraakt | 5 | 09:35 7743.25 → 7738.0 | −$137 | -1.099 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 1 | 11:30 7767.75 → 7763.25 | −$24 | -0.194 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 11 | 36% | -0.238 | -1.21 | −$523 | $755 | $49.477 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 11 | 9% | -0.505 | -4.60 | −$938 | $938 | $49.062 | loopt (11/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 11 | 9% | -0.474 | -3.92 | −$868 | $868 | $49.132 | loopt (11/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 11 | 18% | +0.305 | 0.29 | $730 | $1.323 | $50.730 | loopt (11/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 9 | 44% | +0.601 | 1.00 | $950 | $329 | $50.950 | loopt (9/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
