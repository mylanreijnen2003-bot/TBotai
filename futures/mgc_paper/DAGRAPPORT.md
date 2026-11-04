# MGC-bot – dagrapport 03-11-2026

Forward test (paper) op gratis Yahoo-koersen. Venster 13:00–13:29 New York-tijd (19:00–19:29 NL). Er gaat nooit een order naar een broker. Bijgewerkt 04-11-2026 00:00 UTC.

## Vandaag

Signalen om 13:00 ET: ROD -0.680%, ochtend +0.201%.

| Strategie | Beslissing | Contracten | Instap → uitstap | Uitstap / reden | Netto | R |
|---|---|---:|---|---|---:|---:|
| A – laatste-halfuur momentum (ROD, filter) | SHORT | 4 | 3942.7 → 3941.4 | tijdsuitstap 13:29 | $42 | +0.235 |
| B – altijd long (benchmark) | LONG | 4 | 3942.9 → 3941.2 | tijdsuitstap 13:29 | −$78 | -0.432 |
| C – ROD zonder filter (replicatie paper) | SHORT | 4 | 3942.7 → 3941.4 | tijdsuitstap 13:29 | $42 | +0.235 |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | geen trade | | | beweging kleiner dan normaal (filter) | | |
| E – eensgezind (ROD en ochtend zelfde richting) | geen trade | | | ROD en ochtendsignaal oneens | | |
| R – willekeurige richting (controle) | SHORT | 4 | 3942.7 → 3941.4 | tijdsuitstap 13:29 | $42 | +0.235 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo |
|---|---:|---:|---:|---:|---:|---:|---:|
| A – laatste-halfuur momentum (ROD, filter) | 2 | 100% | +0.179 | 3.23 | $65 | $0 | $50.065 |
| B – altijd long (benchmark) | 2 | 50% | -0.154 | -0.55 | −$55 | $78 | $49.945 |
| C – ROD zonder filter (replicatie paper) | 2 | 100% | +0.179 | 3.23 | $65 | $0 | $50.065 |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | 1 | 100% | +0.124 | – | $22 | $0 | $50.022 |
| E – eensgezind (ROD en ochtend zelfde richting) | 1 | 100% | +0.124 | – | $22 | $0 | $50.022 |
| R – willekeurige richting (controle) | 2 | 50% | -0.421 | -0.64 | −$151 | $194 | $49.849 |

## Eindoordeel forward test

Pas bij 300 trades krijgt een strategie GO of NO-GO (lat in `bot_mgc/HYPOTHESIS.md`). Tot dan is het ruis.

| Strategie | Oordeel | ≥ 300 trades | expectancy ≥ +0.05R | t-stat ≥ 2.50 | profit factor ≥ 1.15 | max drawdown < $2000 | beter dan B (altijd long) | beter dan R (willekeurig) |
|---|---|---|---|---|---|---|---|---|
| A – laatste-halfuur momentum (ROD, filter) | **loopt (nog ± 156 mnd)** | 2 trades | ✓ +0.179R | ✓ 3.23 | – | ✓ $0 | ✓ B -0.154R | ✓ R -0.421R |
| C – ROD zonder filter (replicatie paper) | **loopt (nog ± 156 mnd)** | 2 trades | ✓ +0.179R | ✓ 3.23 | – | ✓ $0 | ✓ B -0.154R | ✓ R -0.421R |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | **loopt (nog ± 313 mnd)** | 1 trades | ✓ +0.124R | – | – | ✓ $0 | ✓ B -0.154R | ✓ R -0.421R |
| E – eensgezind (ROD en ochtend zelfde richting) | **loopt (nog ± 313 mnd)** | 1 trades | ✓ +0.124R | – | – | ✓ $0 | ✓ B -0.154R | ✓ R -0.421R |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). B = altijd long, R = willekeurige richting; A, C, D en E moeten die allebei verslaan.
