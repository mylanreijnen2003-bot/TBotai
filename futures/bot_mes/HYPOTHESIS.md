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

## Toevoeging H (vastgelegd 5 okt 2026, vóór de eerste handelsdag; A–G ongewijzigd)
Bron: Zarattini, Aziz & Barbon (2024), "Beat the Market – An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)".
Het paper meldt op S&P 500-futures (2007–2024) Sharpe 1,32; een onafhankelijke replicatie vindt sinds 2025 een Sharpe rond 0.
Deze forward test beslist.

| Code | Regels (New York-tijd) |
|---|---|
| H | σ(t) = gemiddelde \|prijs(t) ÷ opening 09:30 − 1\| over de laatste 14 handelsdagen, voor t = 10:00, 10:30, … 15:30. Bovenband = max(opening, slot gisteren) × (1 + σ), onderband = min(opening, slot gisteren) × (1 − σ). Op elk controlepunt: prijs boven de bovenband → long, onder de onderband → short; instap op de opening van het controlepunt. Trailing-uitstap op een controlepunt als de prijs onder max(bovenband, VWAP) zakt (long) of boven min(onderband, VWAP) komt (short). Uit 15:59. |

Aanpassingen aan het paper (voor Topstep en deze bot): vaste $200 risico i.p.v. volatiliteitsdoel en hefboom tot 4×; harde stop op
σ(t) × opening tegen de positie in (daarop rekent de positiegrootte); max 4 trades per dag; na een trailing-uitstap niet op hetzelfde
controlepunt in dezelfde richting terug. Gemeenschappelijke regels (kosten, slippage, stop < 2 punten, kalender, weekstop) gelden ook voor H.
Lat: dezelfde als A, C, D, E en G (≥ 300 trades, ≥ +0,05R, t ≥ 2,50, PF ≥ 1,15, DD < $2.000, beter dan B én R). Opwarmen: 14 dagen
met halfuurprijzen uit 5-minuutdata, dus H handelt vanaf de eerste dag.
