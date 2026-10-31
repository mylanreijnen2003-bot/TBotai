# MES-bot – dagrapport 30-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 31-10-2026 00:48 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: stop te groot voor $200 risico | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | short, stop geraakt | 2 | 15:30 7583.5 → 7591.75 | −$85 | -1.062 |
| C – ROD-momentum laatste half uur, zonder filter | short, stop geraakt | 4 | 15:30 7583.5 → 7592.0 | −$175 | -1.060 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, stop geraakt | 4 | 15:30 7583.5 → 7592.0 | −$175 | -1.060 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | short, stop geraakt | 2 | 09:35 7655.25 → 7754.5 | −$995 | -6.633 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | short, stop geraakt | 2 | 10:30 7635.75 → 7652.25 | −$167 | -1.030 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | short, stop geraakt | 1 | 11:30 7640.75 → 7754.5 | −$570 | -4.515 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | short, stop geraakt | 1 | 15:30 7583.5 → 7613.5 | −$151 | -1.017 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 2 | 0% | -0.667 | -1.72 | −$230 | $230 | $49.770 | loopt (2/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 19 | 26% | -0.452 | -3.09 | −$1.588 | $1.588 | $48.412 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 19 | 21% | -0.418 | -4.00 | −$1.324 | $1.324 | $48.676 | loopt (19/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 19 | 21% | -0.400 | -3.71 | −$1.254 | $1.254 | $48.746 | loopt (19/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 19 | 16% | -0.396 | -0.56 | −$693 | $1.560 | $49.307 | loopt (19/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 20 | 35% | -0.147 | -0.39 | −$170 | $1.241 | $49.830 | loopt (20/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
