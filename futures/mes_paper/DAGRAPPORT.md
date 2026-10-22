# MES-bot – dagrapport 21-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 22-10-2026 00:00 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: stop te groot voor $200 risico | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | short, tijdsuitstap | 5 | 15:30 7799.25 → 7803.75 | −$119 | -0.593 |
| C – ROD-momentum laatste half uur, zonder filter | long, tijdsuitstap | 3 | 15:30 7799.75 → 7800.25 | $4 | +0.025 |
| D – ROD-momentum laatste half uur, filter | geen trade: nog te weinig historie | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | long, tijdsuitstap | 3 | 15:30 7799.75 → 7800.25 | $4 | +0.025 |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | short, stop geraakt | 3 | 09:35 7769.25 → 7780.5 | −$172 | -1.045 |
| R – willekeurige richting op de dagen van D (controle) | geen trade: nog te weinig historie | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | long, trailing stop (band/VWAP) | 1 | 14:30 7810.25 → 7787.25 | −$116 | -0.788 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 13 | 38% | -0.218 | -1.25 | −$567 | $755 | $49.433 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 13 | 23% | -0.401 | -3.42 | −$885 | $938 | $49.115 | loopt (13/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 13 | 23% | -0.375 | -3.05 | −$815 | $868 | $49.185 | loopt (13/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 13 | 15% | +0.092 | 0.10 | $439 | $1.323 | $50.439 | loopt (13/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 12 | 42% | +0.426 | 0.92 | $934 | $329 | $50.934 | loopt (12/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
