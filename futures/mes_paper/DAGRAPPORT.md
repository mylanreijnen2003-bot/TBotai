# MES-bot – dagrapport 22-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 22-10-2026 23:59 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: pullback bleef te ver boven/onder de VWAP | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | long, stop geraakt | 5 | 15:30 7697.0 → 7688.75 | −$212 | -1.062 |
| C – ROD-momentum laatste half uur, zonder filter | short, tijdsuitstap | 3 | 15:30 7696.5 → 7702.25 | −$90 | -0.585 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | short, tijdsuitstap | 3 | 15:30 7696.5 → 7702.25 | −$90 | -0.585 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | long, stop geraakt | 2 | 09:35 7738.5 → 7724.5 | −$142 | -1.036 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | short, trailing stop (band/VWAP) | 2 | 10:30 7698.0 → 7713.0 | −$152 | -0.910 |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | short, tijdsuitstap | 1 | 13:00 7702.5 → 7702.25 | $0 | +0.000 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 14 | 36% | -0.278 | -1.62 | −$779 | $779 | $49.221 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 14 | 21% | -0.414 | -3.79 | −$975 | $975 | $49.025 | loopt (14/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 14 | 21% | -0.390 | -3.39 | −$905 | $905 | $49.095 | loopt (14/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 14 | 14% | +0.011 | 0.01 | $297 | $1.323 | $50.297 | loopt (14/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 14 | 43% | +0.300 | 0.74 | $782 | $329 | $50.782 | loopt (14/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
