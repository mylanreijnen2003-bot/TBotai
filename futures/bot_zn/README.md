# ZN-bot (10-jaars Treasury) – fronttest op GitHub

Test acht vooraf vastgelegde strategieën op de 10-jaars Amerikaanse staatsobligatie-future (ZN) met **nepgeld** en **gratis Yahoo-koersen**. Geen account, geen API-sleutel, geen `.env`, je laptop hoeft niet aan. Er gaat nooit een order naar een broker.

- **Stand:** [`../zn_paper/DAGRAPPORT.md`](../zn_paper/DAGRAPPORT.md)
- **Strategieën en instellingen:** [`strategieen.json`](strategieen.json)

## Hoe het draait
- Elke werkdag om 20:37 UTC (22:37 NL in de zomer, 21:37 in de winter) start GitHub Actions de workflow `zn-paper`, na het slot van 15:00 New York-tijd.
- De bot haalt de 1-minuutkoersen van ZN op (contract volgens de rollregel, bijv. ZNZ26) en speelt alle strategieën af met dezelfde code als de laptopversie (`dagelijks.py` + `multi.py`). Elke strategie ziet van een dag alleen de koersen vóór zijn eigen beslismoment, dus achteraf uitrekenen is eerlijk.
- Gemiste dagen haalt hij de volgende run in (max. 30 handelsdagen, zolang Yahoo de 1-minuutdata nog heeft).
- Veilingdagen (strategie D) komen uit `calendar.json` (t/m 2026) en daarna uit de gratis API van het Amerikaanse ministerie van Financiën (fiscaldata.treasury.gov).
- Alles komt in `futures/zn_paper/`: journal, signalen, koerscache, `DAGRAPPORT.md` en `reports/fronttest.html`.
- **Telegram (optioneel):** met de secrets `TELEGRAM_BOT_TOKEN` en `TELEGRAM_CHAT_ID` in de repo krijg je elke dag een korte melding.

| Strategie | Wanneer (New York-tijd) | Wat |
|---|---|---|
| A | 14:30–14:59 | Laatste half uur, in de richting van de dagbeweging (als die groter is dan normaal). |
| B1 | 14:30–14:59 | Als A, maar alleen als de ochtend (tot 08:50) dezelfde kant op ging. |
| B2 | 14:50–14:59 | Als A, maar alleen de laatste 10 minuten. |
| C | 08:20–14:59 | Long op de laatste 3 handelsdagen van de maand. |
| D | 13:01–14:25 | Long na de uitslag van een 5-, 10- of 30-jaars veiling. |
| E | 09:59–10:02 | In de richting van 09:30–09:59, op dagen met ISM- of Conference Board-cijfers om 10:00. |
| G | 08:50–12:00 | Breakout van de range 08:20–08:50. Dit is een controlegroep: als die "wint", is dat toeval. |
| H | 08:20–10:00 | Tegen het laatste half uur van gisteren in, als dat groot was. |

- **Positiegrootte:** $200 ÷ (stop × $15,625), maximaal 3 contracten. Halveren en de weekstop gelden in de fronttest niet: hier wordt de strategie zelf gemeten.
- **Start:** maandag 5 oktober 2026. **Opwarmen:** Yahoo geeft gratis ± 40 handelsdagen terug (5-minuutdata). Strategieën die 60 dagen historie nodig hebben (A, B1, B2, H) handelen daarom pas vanaf ± begin november; C, D, E en G kunnen eerder.

## Zelf doen
- **Handmatig starten:** Actions → `zn-paper` → Run workflow (vinkje "datatest" = alleen controleren of Yahoo data geeft).
- **Noodstop:** bestand `KILL` in de hoofdmap van de repo (stopt alle bots) of `futures/zn_paper/STOP` (alleen deze bot).

## Beperkingen
- Yahoo-data is gratis en niet officieel: soms ontbreekt een minuut of een dag.
- De 10:00-cijfers (strategie E) volgen vaste regels: ISM op de 1e en 3e werkdag, Conference Board op de laatste dinsdag.
- Feestdagen, FOMC- en notulendata staan in `futures/calendar.json` t/m 2027; daarna bijwerken.
- Tests: `cd futures && python -m pytest -q bot_zn` (geen netwerk nodig).
