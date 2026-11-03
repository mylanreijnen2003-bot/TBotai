# MES-bot – dagrapport 02-11-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 03-11-2026 02:55 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: pullback bleef te ver boven/onder de VWAP | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | long, stop geraakt | 2 | 15:30 7597.0 → 7588.75 | −$85 | -1.062 |
| C – ROD-momentum laatste half uur, zonder filter | short, tijdsuitstap | 3 | 15:30 7596.5 → 7573.75 | $338 | +2.196 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | long, stop geraakt | 3 | 15:30 7597.0 → 7586.5 | −$161 | -1.048 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | short, stop geraakt | 2 | 09:35 7648.25 → 7652.25 | −$42 | -1.132 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 4 | 10:00 7658.75 → 7664.5 | $110 | +0.629 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 2 | 0% | -0.667 | -1.72 | −$230 | $230 | $49.770 | loopt (2/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 20 | 25% | -0.482 | -3.40 | −$1.673 | $1.673 | $48.327 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 20 | 25% | -0.288 | -1.75 | −$987 | $1.324 | $49.013 | loopt (20/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 20 | 20% | -0.433 | -4.03 | −$1.415 | $1.415 | $48.585 | loopt (20/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 20 | 15% | -0.433 | -0.64 | −$735 | $1.603 | $49.265 | loopt (20/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 21 | 38% | -0.110 | -0.30 | −$60 | $1.241 | $49.940 | loopt (21/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
