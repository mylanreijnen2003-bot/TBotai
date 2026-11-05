# MGC-bot – dagrapport 04-11-2026

Forward test (paper) op gratis Yahoo-koersen. Venster 13:00–13:29 New York-tijd (19:00–19:29 NL). Er gaat nooit een order naar een broker. Bijgewerkt 05-11-2026 00:25 UTC.

## Vandaag

Signalen om 13:00 ET: ROD +3.454%, ochtend +2.870%.

| Strategie | Beslissing | Contracten | Instap → uitstap | Uitstap / reden | Netto | R |
|---|---|---:|---|---|---:|---:|
| A – laatste-halfuur momentum (ROD, filter) | LONG | 4 | 4076.7 → 4072.9 | tijdsuitstap 13:29 | −$162 | -0.919 |
| B – altijd long (benchmark) | LONG | 4 | 4076.7 → 4072.9 | tijdsuitstap 13:29 | −$162 | -0.919 |
| C – ROD zonder filter (replicatie paper) | LONG | 4 | 4076.7 → 4072.9 | tijdsuitstap 13:29 | −$162 | -0.919 |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | LONG | 4 | 4076.7 → 4072.9 | tijdsuitstap 13:29 | −$162 | -0.919 |
| E – eensgezind (ROD en ochtend zelfde richting) | LONG | 4 | 4076.7 → 4072.9 | tijdsuitstap 13:29 | −$162 | -0.919 |
| R – willekeurige richting (controle) | LONG | 4 | 4076.7 → 4072.9 | tijdsuitstap 13:29 | −$162 | -0.919 |

## Sinds de start

| Strategie | Trades | Winrate | Expectancy (R) | t-stat | Netto | Max drawdown | Virtueel saldo |
|---|---:|---:|---:|---:|---:|---:|---:|
| A – laatste-halfuur momentum (ROD, filter) | 3 | 67% | -0.187 | -0.51 | −$97 | $162 | $49.903 |
| B – altijd long (benchmark) | 3 | 33% | -0.409 | -1.36 | −$217 | $239 | $49.783 |
| C – ROD zonder filter (replicatie paper) | 3 | 67% | -0.187 | -0.51 | −$97 | $162 | $49.903 |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | 2 | 50% | -0.398 | -0.76 | −$139 | $162 | $49.861 |
| E – eensgezind (ROD en ochtend zelfde richting) | 2 | 50% | -0.398 | -0.76 | −$139 | $162 | $49.861 |
| R – willekeurige richting (controle) | 3 | 33% | -0.587 | -1.42 | −$313 | $313 | $49.687 |

## Eindoordeel forward test

Pas bij 300 trades krijgt een strategie GO of NO-GO (lat in `bot_mgc/HYPOTHESIS.md`). Tot dan is het ruis.

| Strategie | Oordeel | ≥ 300 trades | expectancy ≥ +0.05R | t-stat ≥ 2.50 | profit factor ≥ 1.15 | max drawdown < $2000 | beter dan B (altijd long) | beter dan R (willekeurig) |
|---|---|---|---|---|---|---|---|---|
| A – laatste-halfuur momentum (ROD, filter) | **loopt (nog ± 108 mnd)** | 3 trades | -0.187R | -0.51 | 0.40 | ✓ $162 | ✓ B -0.409R | ✓ R -0.587R |
| C – ROD zonder filter (replicatie paper) | **loopt (nog ± 108 mnd)** | 3 trades | -0.187R | -0.51 | 0.40 | ✓ $162 | ✓ B -0.409R | ✓ R -0.587R |
| D – ochtendsignaal (overnacht + eerste halfuur, filter) | **loopt (nog ± 163 mnd)** | 2 trades | -0.398R | -0.76 | 0.14 | ✓ $162 | ✓ B -0.409R | ✓ R -0.587R |
| E – eensgezind (ROD en ochtend zelfde richting) | **loopt (nog ± 163 mnd)** | 2 trades | -0.398R | -0.76 | 0.14 | ✓ $162 | ✓ B -0.409R | ✓ R -0.587R |

Expectancy = gemiddelde winst per trade in R (R = het geriskeerde bedrag, ± $200). B = altijd long, R = willekeurige richting; A, C, D en E moeten die allebei verslaan.
