# HYPOTHESIS – MGC-bot (vastgelegd 3 okt 2026, vóór het bekijken van de out-of-sample data)

Gebaseerd op het strategie-onderzoek van 3 okt 2026 (Baltussen e.a. 2021, JFE: intraday momentum; goud t ≈ 3, vóór kosten).
Deze regels worden niet aangepast om alsnog te slagen. Nieuwe varianten komen er alleen bij als een nieuwe, gedateerde versie.

## Besluit 3 okt 2026: forward test in plaats van backtest

Er wordt geen historische data gekocht. De paper-test (forward test: gesimuleerde fills, geen orders) is de toets.
Hij draait elke werkdag op GitHub Actions met gratis Yahoo-koersen (GC, 1-minuut), start op maandag 5 okt 2026 en
loopt maanden tot jaren. Een strategie krijgt pas een oordeel bij 300 paper-trades:

| Eis | Lat |
|---|---|
| Trades | ≥ 300 |
| Expectancy | ≥ +0,05R na kosten |
| t-stat | ≥ 2,50 (4 strategieën tegelijk getest) |
| Profit factor | ≥ 1,15 |
| Max drawdown | < $2.000 |
| Vergelijking | beter dan B én beter dan R |

Controle R vanaf 100 R-trades: wijkt R meer dan 2 standaardfouten af van −kosten, dan eerst de fout zoeken.
Het dagrapport toont dit oordeel per strategie. De backtest-regels hieronder blijven gelden als er later toch data komt.

## Gemeenschappelijk (alle varianten)

- Venster 13:00–13:29 ET (normaal 19:00–19:29 NL). Market-instap 13:00:05, tijdsuitstap 13:29, max 1 trade per dag.
- Stop = 1,5 × gemiddelde beweging 13:00–13:30 van 20 dagen; < 2,0 punten → overslaan.
- Contracten = floor($200 / (stop × $10)), max 10; halveren binnen $600 van de bodem; weekstop −$800; noodrem −$400.
- Elke variant heeft een eigen virtueel Topstep 50K-account. Alleen A mag ooit naar fase C/D (echte orders).
- 1R = het werkelijk geriskeerde bedrag van die trade.

## Varianten

| Code | Signaal | Filter | Rol |
|---|---|---|---|
| A | ROD = prijs 13:00 ÷ slot gisteren (13:30) − 1 | \|ROD\| > mediaan 60 dagen | hoofdstrategie |
| B | altijd long | – | benchmark (goud-drift) |
| C | ROD | geen | directe replicatie van het paper |
| D | ONFH = prijs 08:50 ÷ slot gisteren − 1 (overnacht + eerste halfuur) | \|ONFH\| > mediaan 60 dagen | sterkste goudsignaal in de bron |
| E | alleen als teken(ROD) = teken(ONFH) | geen | beide signalen eens |
| R | willekeurige richting (vaste seed 20261003) op precies de dagen van A | als A | negatieve controle |

## Hypotheses (out-of-sample 2020–nu, na kosten)

- **H-A, H-C, H-D, H-E:** expectancy ≥ +0,05R, t-stat ≥ **2,50** (Bonferroni: 4 richtinggevende varianten), profit factor ≥ 1,15
  met stresskosten, plus de overige criteria uit plan §8, beter dan B én beter dan R.
- **H-R (controle):** expectancy ligt binnen 2 standaardfouten van −(kosten ÷ risico). Zo niet: fout in de backtest; dan zijn
  A–E ongeldig tot de fout gevonden is.
- **Verwachting vooraf:** grote kans dat geen enkele variant alles haalt. Dan parkeren, niet nieuwe varianten zoeken.

## Alleen tonen, nooit automatisch kiezen

- Gevoeligheidstabel per variant: filter_dagen {geen, 40, 60, 120} × stop_factor {1,0; 1,5; 2,0}.
- Long en short apart; in-sample 2010–2014 (pithandel) en 2015–2019 apart.
- Marktstatistiek overnacht vs. overdag per jaar (overnight vasthouden mag niet bij Topstep).

## Bewust niet getest

Opening range breakout, handelen op CPI/NFP/FOMC, intraday mean reversion, London fix, VWAP-regels, dag-van-de-week,
ML-modellen, overnight-posities. Reden: geen bewijs na kosten, verdwenen effect of niet toegestaan bij Topstep.

## Paper (fase B)

Alle zes varianten draaien naast elkaar op live koersen, zonder orders. Een paar maanden paper toetst de uitvoering
(tijden, rolls, slippage), niet de voorsprong: daarvoor zijn honderden trades nodig.
