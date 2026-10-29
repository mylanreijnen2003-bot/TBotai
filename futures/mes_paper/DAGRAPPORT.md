# MES-bot – dagrapport 28-10-2026

Forward test (paper) op gratis Yahoo-koersen van de S&P 500-future (ES, zelfde prijs als MES). Er gaat nooit een order naar een broker. Start 2026-10-05. Bijgewerkt 29-10-2026 00:58 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | geen trade: FOMC-dag | | | | |
| B – eerste half uur → laatste half uur (benchmark uit plan) | geen trade: FOMC-dag | | | | |
| C – ROD-momentum laatste half uur, zonder filter | geen trade: FOMC-dag | | | | |
| D – ROD-momentum laatste half uur, filter | geen trade: FOMC-dag | | | | |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | geen trade: FOMC-dag | | | | |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | geen trade: FOMC-dag | | | | |
| R – willekeurige richting op de dagen van D (controle) | geen trade: FOMC-dag | | | | |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | geen trade: FOMC-dag | | | | |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo | Oordeel |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A – laatste-uur trendvervolg (VWAP + opening range + pullback, 2R) | 1 | 0% | -0.279 | – | −$45 | $45 | $49.955 | loopt (1/300 trades) |
| B – eerste half uur → laatste half uur (benchmark uit plan) | 17 | 29% | -0.380 | -2.47 | −$1.291 | $1.291 | $48.709 | vergelijking |
| C – ROD-momentum laatste half uur, zonder filter | 17 | 24% | -0.343 | -3.36 | −$988 | $988 | $49.012 | loopt (17/300 trades) |
| D – ROD-momentum laatste half uur, filter | 0 | – | – | – | – | – | $50.000 | loopt (0/300 trades) |
| E – eerste half uur incl. nacht → laatste half uur (Gao e.a.) | 17 | 24% | -0.323 | -3.07 | −$918 | $918 | $49.082 | loopt (17/300 trades) |
| G – opening range breakout 5 min, 10R (Zarattini e.a.) | 17 | 18% | +0.008 | 0.01 | $457 | $1.323 | $50.457 | loopt (17/300 trades) |
| R – willekeurige richting op de dagen van D (controle) | 0 | – | – | – | – | – | $50.000 | vergelijking |
| H – noise-area momentum, halfuurlijks (Zarattini e.a. 2024; toegevoegd 5 okt) | 17 | 41% | +0.214 | 0.63 | $718 | $352 | $50.718 | loopt (17/300 trades) |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). Oordeel pas bij 300 trades: expectancy ≥ +0.05R, t-stat ≥ 2.50, profit factor ≥ 1.15, max drawdown < $2000, beter dan B én R. Elke strategie heeft een eigen virtueel Topstep 50K-account.
