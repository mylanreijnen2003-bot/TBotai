# ZN-bot – dagrapport 04-11-2026

Fronttest (paper) van de 10-jaars Treasury-future op gratis Yahoo-koersen. Er gaat nooit een order naar een broker. Start: 2026-10-05. Bijgewerkt 05-11-2026 01:01 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste half uur, ROD-filter (basis) | geen trade: te weinig historie | | | | |
| B1 – als A, maar ochtend en dag in dezelfde richting | geen trade: te weinig historie | | | | |
| B2 – alleen de laatste 10 minuten | geen trade: te weinig historie | | | | |
| C – maandeinde long | geen trade: geen maandeinde | | | | |
| D – veilingdag: long na de uitslag van 13:00 | geen trade: geen veiling | | | | |
| E – drift vóór de cijfers van 10:00 (ISM, Conference Board) | geen trade: filter zwak | | | | |
| G – opening range breakout (controlegroep) | short (stop) | 1 | 106.546875 → 106.71875 | −$176 | -1.123 |
| H – ochtend-reversal van het laatste half uur van gisteren | geen trade: te weinig historie | | | | |

## Sinds de start

| Strategie | Trades | Winrate | Gem. R per trade | t-stat | Netto | Max drawdown | Voortgang oordeel |
|---|---:|---:|---:|---:|---:|---:|---|
| A – laatste half uur, ROD-filter (basis) | 0 | – | – | – | – | – | 0 / 100 trades |
| B1 – als A, maar ochtend en dag in dezelfde richting | 0 | – | – | – | – | – | 0 / 100 trades |
| B2 – alleen de laatste 10 minuten | 0 | – | – | – | – | – | 0 / 100 trades |
| C – maandeinde long | 3 | 33% | -0.223 | -0.25 | −$105 | $176 | 3 / 100 trades |
| D – veilingdag: long na de uitslag van 13:00 | 2 | 0% | -0.788 | -1.89 | −$296 | $296 | 2 / 100 trades |
| E – drift vóór de cijfers van 10:00 (ISM, Conference Board) | 1 | 0% | -0.529 | – | −$66 | $66 | 1 / 100 trades |
| G – opening range breakout (controlegroep) | 22 | 18% | -0.658 | -3.20 | −$2.272 | $2.517 | 22 / 100 trades |
| H – ochtend-reversal van het laatste half uur van gisteren | 0 | – | – | – | – | – | 0 / 100 trades |

R = winst of verlies gedeeld door het geplande risico (± $200). G is een controlegroep: als die "wint", is dat toeval. Pas na tientallen trades per strategie zegt dit iets. Volledige tabel met grafiek: `reports/fronttest.html`.
