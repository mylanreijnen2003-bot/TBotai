# HYPOTHESIS – MES-bot (vastgelegd 3 okt 2026, vóór de start)

Forward test op GitHub met gratis Yahoo-koersen (ES, zelfde prijs als MES; gerekend met MES: $5 per punt). Start maandag
5 oktober 2026. Geen orders, geen account. Niet aanpassen om alsnog te slagen; nieuwe varianten alleen als nieuwe, gedateerde versie.

## Gemeenschappelijk
- $200 risico per trade, contracten = floor(200 ÷ (stop × $5)), max 5; halveren binnen $600 van de bodem; weekstop −$800.
- Kosten $1,22 per contract (heen en terug) + 1 tick slippage op market-instap, stop en tijdsuitstap. Doel alleen gevuld bij 1 tick doorbraak; stop en doel in dezelfde minuut → stop.
- Stop < 2 punten → overslaan. Niet traden op FOMC-dagen, 24 dec–2 jan, vervroegde sluitingen, feestdagen.
- Elke strategie heeft een eigen virtueel Topstep 50K-account.

## Strategieën
| Code | Regels (New York-tijd) | Bron / rol |
|---|---|---|
| A | Plan-MES §3: bias om 14:45 (slot > VWAP én > hoog 09:30–10:00, of spiegelbeeld); pullback op 5-minuutbars tot ≤ VWAP + 2 punten; trigger = bar sluit hoger dan open, boven hoog vorige bar en boven VWAP; instap volgende bar (14:50–15:45); stop pullback-laag − 1 tick (max 12 punten); doel 2R; uit 15:55; max 2 trades, dagstop 2 verliezen / −$400, winstplafond +$700 | hoofdstrategie (eigen handmatige regels) |
| B | Plan-MES §4: teken 09:30→10:00 → instap 15:30, stop 8 punten, uit 15:55 | benchmark uit het plan |
| C | ROD = prijs 15:30 ÷ slot gisteren 16:00 − 1; teken → instap 15:30, uit 15:59; stop 1,5 × gem. beweging 15:30–16:00 (20 dagen) | Baltussen e.a. 2021 (JFE): intraday momentum, het sterkst in aandelenindex-futures |
| D | Als C, alleen als \|ROD\| > mediaan 60 dagen | filtervariant (zelfde als goud A) |
| E | Rendement slot gisteren → 10:00 voorspelt het laatste half uur; zelfde uitvoering als C | Gao, Han, Li & Zhou 2018 (JFE), S&P 500 |
| G | Eerste 5-minuutbar (09:30–09:34) bepaalt de richting; instap 09:35; stop andere kant van die bar; doel 10R; uit 15:59 | Zarattini, Aziz & Barbon 2023 (ORB op QQQ); op MNQ out-of-sample niet overeind (Mesfin 2026) |
| R | Willekeurige richting (seed 20261003) op de dagen van D | controle |

Keuzes die het plan openliet: de pullback-check gebruikt de VWAP bij het slot van de triggerbar; een triggerbar beëindigt de pullback (ook als die ongeldig was); na een trade zoekt A pas weer vanaf de 5-minuutbar na de uitstap.

## Lat (per strategie A, C, D, E, G; pas bij 300 trades)
Expectancy ≥ +0,05R na kosten, t-stat ≥ 2,50 (5 strategieën tegelijk), profit factor ≥ 1,15, max drawdown < $2.000, beter dan B én R.
Opwarmen: C en E handelen vanaf de eerste dag (20 dagen historie via 5-minuutdata), D en R na ± 4 weken; A, B en G meteen.
