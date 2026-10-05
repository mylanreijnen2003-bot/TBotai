# MES-bot (Micro E-mini S&P 500) – forward test op GitHub

Test acht vooraf vastgelegde strategieën met **nepgeld** op **gratis Yahoo-koersen**. Geen account, geen API-sleutel, je laptop hoeft niet aan. Er gaat nooit een order naar een broker.

- **Stand:** [`../mes_paper/DAGRAPPORT.md`](../mes_paper/DAGRAPPORT.md)
- **Regels en lat:** [`HYPOTHESIS.md`](HYPOTHESIS.md)

## Hoe het draait
- Elke werkdag om 21:17 UTC (23:17 NL in de zomer, 22:17 in de winter) start de workflow `mes-paper`, na het slot van 16:00 New York-tijd.
- De bot haalt de 1-minuutkoersen (met volume, voor de VWAP) van de S&P 500-future op en speelt alle strategieën af. Elke strategie gebruikt alleen koersen tot zijn eigen beslismoment, dus achteraf uitrekenen is eerlijk.
- Gemiste dagen worden ingehaald zolang Yahoo de 1-minuutdata nog heeft (30 dagen).
- Alles komt in `futures/mes_paper/`: `journal.csv` (trades), `signalen.csv` (per dag en strategie wat er gebeurde), `DAGRAPPORT.md`.

| Code | Wat (New York-tijd) |
|---|---|
| A | Laatste uur trend volgen na een terugval naar de VWAP (je eigen plan), 2R-doel |
| B | Richting van 09:30–10:00 → laatste half uur (benchmark uit het plan) |
| C | Richting van de dag tot 15:30 → laatste half uur |
| D | Als C, alleen bij een grotere beweging dan normaal |
| E | Richting van gisteren 16:00 tot 10:00 → laatste half uur |
| G | Opening range breakout: richting van de eerste 5 minuten, doel 10R |
| H | Noise area: elk half uur meegaan als de koers buiten zijn normale dagbeweging breekt (toegevoegd 5 okt) |
| R | Willekeurige richting (controle) |

## Zelf doen
- **Handmatig starten:** Actions → `mes-paper` → Run workflow (vinkje "datatest" = alleen controleren of Yahoo data geeft, uitkomst in `mes_paper/datatest.txt`).
- **Noodstop:** bestand `KILL` in de hoofdmap (alle bots) of `futures/mes_paper/STOP` (alleen deze bot).
- Tests: `cd futures && python -m pytest -q bot_mes` (geen netwerk nodig).
