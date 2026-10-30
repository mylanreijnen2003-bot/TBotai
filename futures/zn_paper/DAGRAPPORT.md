# ZN-bot – dagrapport 29-10-2026

Fronttest (paper) van de 10-jaars Treasury-future op gratis Yahoo-koersen. Er gaat nooit een order naar een broker. Start: 2026-10-05. Bijgewerkt 30-10-2026 00:15 UTC.

## Laatste handelsdag

| Strategie | Uitkomst | Contracten | Instap → uitstap | Netto | R |
|---|---|---:|---|---:|---:|
| A – laatste half uur, ROD-filter (basis) | geen trade: te weinig historie | | | | |
| B1 – als A, maar ochtend en dag in dezelfde richting | geen trade: te weinig historie | | | | |
| B2 – alleen de laatste 10 minuten | geen trade: te weinig historie | | | | |
| C – maandeinde long | long (tijd) | 1 | 105.921875 → 106.171875 | $246 | 1.577 |
| D – veilingdag: long na de uitslag van 13:00 | geen trade: geen veiling | | | | |
| E – drift vóór de cijfers van 10:00 (ISM, Conference Board) | geen trade: geen release | | | | |
| G – opening range breakout (controlegroep) | long (tijd) | 1 | 106.109375 → 106.09375 | −$19 | -0.123 |
| H – ochtend-reversal van het laatste half uur van gisteren | geen trade: te weinig historie | | | | |

## Sinds de start

| Strategie | Trades | Winrate | Gem. R per trade | t-stat | Netto | Max drawdown | Voortgang oordeel |
|---|---:|---:|---:|---:|---:|---:|---|
| A – laatste half uur, ROD-filter (basis) | 0 | – | – | – | – | – | 0 / 100 trades |
| B1 – als A, maar ochtend en dag in dezelfde richting | 0 | – | – | – | – | – | 0 / 100 trades |
| B2 – alleen de laatste 10 minuten | 0 | – | – | – | – | – | 0 / 100 trades |
| C – maandeinde long | 2 | 50% | +0.227 | 0.17 | $71 | $176 | 2 / 100 trades |
| D – veilingdag: long na de uitslag van 13:00 | 2 | 0% | -0.788 | -1.89 | −$296 | $296 | 2 / 100 trades |
| E – drift vóór de cijfers van 10:00 (ISM, Conference Board) | 0 | – | – | – | – | – | 0 / 100 trades |
| G – opening range breakout (controlegroep) | 18 | 17% | -0.649 | -2.73 | −$1.836 | $2.081 | 18 / 100 trades |
| H – ochtend-reversal van het laatste half uur van gisteren | 0 | – | – | – | – | – | 0 / 100 trades |

R = winst of verlies gedeeld door het geplande risico (± $200). G is een controlegroep: als die "wint", is dat toeval. Pas na tientallen trades per strategie zegt dit iets. Volledige tabel met grafiek: `reports/fronttest.html`.
