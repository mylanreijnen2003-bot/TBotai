# MGC-bot – dagrapport 02-11-2026

Forward test (paper) op gratis Yahoo-koersen. Venster 13:00–13:29 New York-tijd (19:00–19:29 NL). Er gaat nooit een order naar een broker. Bijgewerkt 03-11-2026 01:40 UTC.

## Vandaag

Signalen om 13:00 ET: ROD +1.777%, ochtend +1.480%.

| Strategie | Beslissing | Contracten | Instap → uitstap | Uitstap / reden | Netto | R |
|---|---|---:|---|---|---:|---:|
| A – laatste-halfuur momentum (ROD, filter) | LONG | 4 | 3968.3 → 3969.1 | tijdsuitstap 13:29 | $22 | +0.124 |
| B – altijd long (benchmark) | LONG | 4 | 3968.3 → 3969.1 | tijdsuitstap 13:29 | $22 | +0.124 |
| C – ROD zonder filter (replicatie paper) | LONG | 4 | 3968.3 → 3969.1 | tijdsuitstap 13:29 | $22 | +0.124 |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | LONG | 4 | 3968.3 → 3969.1 | tijdsuitstap 13:29 | $22 | +0.124 |
| E – eensgezind (ROD en ochtend zelfde richting) | LONG | 4 | 3968.3 → 3969.1 | tijdsuitstap 13:29 | $22 | +0.124 |
| R – willekeurige richting (controle) | SHORT | 4 | 3968.1 → 3972.7 | stop geraakt | −$194 | -1.076 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo |
|---|---:|---:|---:|---:|---:|---:|---:|
| A – laatste-halfuur momentum (ROD, filter) | 1 | 100% | +0.124 | – | $22 | $0 | $50.022 |
| B – altijd long (benchmark) | 1 | 100% | +0.124 | – | $22 | $0 | $50.022 |
| C – ROD zonder filter (replicatie paper) | 1 | 100% | +0.124 | – | $22 | $0 | $50.022 |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | 1 | 100% | +0.124 | – | $22 | $0 | $50.022 |
| E – eensgezind (ROD en ochtend zelfde richting) | 1 | 100% | +0.124 | – | $22 | $0 | $50.022 |
| R – willekeurige richting (controle) | 1 | 0% | -1.076 | – | −$194 | $194 | $49.806 |

## Eindoordeel forward test

Pas bij 300 trades krijgt een strategie GO of NO-GO (lat in `bot_mgc/HYPOTHESIS.md`). Tot dan is het ruis.

| Strategie | Oordeel | ≥ 300 trades | expectancy ≥ +0.05R | t-stat ≥ 2.50 | profit factor ≥ 1.15 | max drawdown < $2000 | beter dan B (altijd long) | beter dan R (willekeurig) |
|---|---|---|---|---|---|---|---|---|
| A – laatste-halfuur momentum (ROD, filter) | **loopt (nog ± 299 mnd)** | 1 trades | ✓ +0.124R | – | – | ✓ $0 | B +0.124R | ✓ R -1.076R |
| C – ROD zonder filter (replicatie paper) | **loopt (nog ± 299 mnd)** | 1 trades | ✓ +0.124R | – | – | ✓ $0 | B +0.124R | ✓ R -1.076R |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | **loopt (nog ± 299 mnd)** | 1 trades | ✓ +0.124R | – | – | ✓ $0 | B +0.124R | ✓ R -1.076R |
| E – eensgezind (ROD en ochtend zelfde richting) | **loopt (nog ± 299 mnd)** | 1 trades | ✓ +0.124R | – | – | ✓ $0 | B +0.124R | ✓ R -1.076R |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). B = altijd long, R = willekeurige richting; A, C, D en E moeten die allebei verslaan.
