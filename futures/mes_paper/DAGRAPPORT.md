# MES-bot – dagrapport 14-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 14-10-2026 23:55 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: pullback bleef te ver boven/onder de VWAP | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | short, tijdsuitstap | 5 | 15:30 7763.5 → 7766.25 | −$75 | -0.374 |
| C – ROD-momentum laatste half uur, zonder filter | short, tijdsuitstap | 4 | 15:30 7763.5 → 7764.0 | −$15 | -0.078 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, tijdsuitstap | 4 | 15:30 7763.5 → 7764.0 | −$15 | -0.078 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | long, stop geraakt | 5 | 09:35 7825.0 → 7818.75 | −$162 | -1.082 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | short, tijdsuitstap | 4 | 10:00 7807.75 → 7764.0 | $870 | +4.703 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 8 | 12% | -0.472 | -2.55 | −$755 | $755 | $49.245 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 8 | 0% | -0.517 | -4.59 | −$663 | $663 | $49.337 | loopt (8/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 8 | 12% | -0.442 | -3.02 | −$543 | $573 | $49.457 | loopt (8/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 8 | 12% | -0.560 | -1.06 | −$603 | $1.146 | $49.397 | loopt (8/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 6 | 33% | +0.572 | 0.66 | $717 | $329 | $50.717 | loopt (6/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
