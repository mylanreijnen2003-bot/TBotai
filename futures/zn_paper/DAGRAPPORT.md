# ZN-bot – dagrapport 07-10-2026

Fronttest (paper) van de 10-jaars Treasury-future op gratis Yahoo-koersen. Er gaat nooit een order naar een broker. Start: 2026-10-05. Bijgewerkt 08-10-2026 09:46 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste half uur, ROD-filter (basis) | geen trade: fomc notulen | | | | |
| B1 – als A, maar ochtend en dag in dezelfde richting | geen trade: fomc notulen | | | | |
| B2 – alleen de laatste 10 minuten | geen trade: fomc notulen | | | | |
| C – maandeinde long | geen trade: geen maandeinde | | | | |
| D – veilingdag: long na de uitslag van 13:00 | geen trade: fomc notulen | | | | |
| E – drift vóór de cijfers van 10:00 (ISM, Conference Board) | geen trade: geen release | | | | |
| G – opening range breakout (controlegroep) | short (stop) | 1 | 104.046875 → 104.171875 | −$129 | -1.176 |
| H – ochtend-reversal van het laatste half uur van gisteren | geen trade: te weinig historie | | | | |

## Sinds de start

| Strategie | Trades | Winrate | Gem. R per trade | t-stat | Netto | Max drawdown | Voortgang oordeel |
|---|---:|---:|---:|---:|---:|---:|---|
| A – laatste half uur, ROD-filter (basis) | 0 | – | – | – | – | – | 0 / 100 trades |
| B1 – als A, maar ochtend en dag in dezelfde richting | 0 | – | – | – | – | – | 0 / 100 trades |
| B2 – alleen de laatste 10 minuten | 0 | – | – | – | – | – | 0 / 100 trades |
| C – maandeinde long | 0 | – | – | – | – | – | 0 / 100 trades |
| D – veilingdag: long na de uitslag van 13:00 | 0 | – | – | – | – | – | 0 / 100 trades |
| E – drift vóór de cijfers van 10:00 (ISM, Conference Board) | 0 | – | – | – | – | – | 0 / 100 trades |
| G – opening range breakout (controlegroep) | 3 | 33% | -0.601 | -1.02 | −$264 | $355 | 3 / 100 trades |
| H – ochtend-reversal van het laatste half uur van gisteren | 0 | – | – | – | – | – | 0 / 100 trades |

R = winst of verlies gedeeld door het geplande risico (± $200). G is een controlegroep: als die "wint", is dat toeval. Pas na tientallen trades per strategie zegt dit iets. Volledige tabel met grafiek: `reports/fronttest.html`.
