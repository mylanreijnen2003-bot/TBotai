# MGC-bot (Micro Gold) – forward test op GitHub

Test zes vooraf vastgelegde goudstrategieën met **nepgeld** op **gratis Yahoo-koersen**. Geen account, geen API-sleutel, geen `.env`, je laptop hoeft niet aan. Er gaat nooit een order naar een broker.

- **Stand van vandaag:** [`../mgc_paper/DAGRAPPORT.md`](../mgc_paper/DAGRAPPORT.md)
- **Regels en lat:** [`HYPOTHESIS.md`](HYPOTHESIS.md)

## Hoe het draait
- Elke werkdag om 19:23 UTC (21:23 NL in de zomer, 20:23 in de winter) start GitHub Actions de workflow `mgc-paper`.
- De bot haalt de 1-minuutkoersen van goud van die dag op (contract GC, dezelfde prijs als MGC) en speelt alle strategieën af, met precies dezelfde beslis- en fillcode als de backtest. De beslissing om 13:00 New York-tijd gebruikt alleen koersen tot 13:00, dus achteraf uitrekenen is eerlijk.
- Gemiste dagen haalt hij de volgende run in, zolang Yahoo de 1-minuutdata nog heeft (30 dagen).
- Alles komt in `futures/mgc_paper/`: journal, signalen, dagrapport (Markdown en HTML) en een koerscache.
- **Telegram (optioneel):** staan de secrets `TELEGRAM_BOT_TOKEN` en `TELEGRAM_CHAT_ID` al in de repo (zoals bij de cryptobot), dan krijg je elke dag een korte melding.

## De strategieën (venster 13:00–13:29 New York-tijd, $200 risico per trade)
| Code | Wanneer instappen |
|---|---|
| A | Beweging sinds gisteren (ROD) groter dan normaal |
| B | Altijd long (vergelijking) |
| C | ROD zonder filter (zoals het onderzoek) |
| D | Ochtendsignaal: gisteren 13:30 tot vandaag 08:50 |
| E | Alleen als ROD en ochtendsignaal dezelfde kant op wijzen |
| R | Willekeurige richting op de dagen van A (controle) |

Elke strategie heeft een eigen virtueel Topstep 50K-account. Een oordeel (GO/NO-GO) komt pas bij 300 trades per strategie; het dagrapport laat zien hoe ver elke strategie is.

## Zelf doen
- **Handmatig starten:** Actions → `mgc-paper` → Run workflow.
- **Controleren of de data werkt:** Run workflow met het vinkje "datatest" aan.
- **Noodstop:** maak een bestand `KILL` in de hoofdmap van de repo (stopt ook de cryptobot) of `futures/mgc_paper/STOP` (alleen deze bot).

## Opwarmen
De filters kijken 60 handelsdagen terug. Bij de start haalt de bot 5-minuutkoersen op (Yahoo bewaart die 60 kalenderdagen, ± 40 handelsdagen). A, D en R handelen daarom pas na ± 4 weken; daarna draait alles.

## Beperkingen
- Yahoo-data is gratis en niet officieel: soms ontbreekt een minuut of een dag. Ontbreekt de dag na 3 dagen nog, dan telt hij als `geen_data`.
- Beursfeestdagen en rolldata staan in `futures/calendar.json` tot en met 2027; daarna bijwerken.
- Tests: `cd futures && python -m pytest -q bot_mgc` (geen netwerk nodig).
