# HYPOTHESIS.md — strategieversie v1

Vastgelegd op 30 september 2026, vóór de start. **Niet meer wijzigen.**
Een wijziging aan regels of parameters = nieuwe versie (v2) met een nieuwe, lege `state/`-map.
De code in `tbot/` voert precies deze regels uit; `config.yaml` bevat de getallen.

Onderbouwing: rapport "Crypto spot strategieën met bewijs" (30 sept 2026).

## Gemeenschappelijk
- **Data:** dagcandles Bitvavo, EUR-paren, slot = 00:00 UTC. Alleen publieke koersdata, geen echt geld.
- **Uitvoering:** signaal op het slot van dag t, uitvoering tegen de open van dag t+1.
- **Kosten:** 0,30% per kant op elke verhandelde euro (basis); 0,60% als stresstest (alleen backtest).
- **Startkapitaal:** €10.000 nepgeld per strategie en per benchmark. Cash levert 0% rente op.
- **σ90:** stdev van dagelijkse log-rendementen over 90 dagen × √365.
- **Universum:** op de 1e van de maand de top-15 EUR-paren op mediaan dagvolume in EUR (volume × slot) over 30 dagen.
  - Eisen: ≥365 dagen koershistorie, mediaan |dagrendement| over 30 dagen ≥0,5%, geen munt op de uitsluitlijst in `config.yaml` (stablecoins, wrapped en getokeniseerde varianten).
  - N = aantal munten dat voldoet (normaal 15).
  - Valt een munt uit het universum, dan wordt de positie volledig verkocht.
- **Band:** een munt wordt alleen bijgestuurd als |huidig − doel| / doel > 20%, of bij instap (doel 0 → >0) of uitstap (>0 → 0). Geldt voor S1, S2 en S3.
- **Minimale order:** €5; kleinere orders worden overgeslagen (een volledige uitstap altijd uitgevoerd).
- **Geen hefboom:** kopen kan alleen met aanwezig cash; totale blootstelling ≤100%.

## S1 — Donchian-trend-ensemble (naar Zarattini, Pagani & Barbon 2025)
- Lookbacks L: 5, 10, 20, 30, 60, 90, 150, 250, 360 dagen. Per munt en per L een toestand aan/uit:
  - **Instap:** uit en close_t ≥ max(close_{t−L} … close_{t−1}) → aan, stop = midden_t.
  - **Stop:** zolang aan: stop_t = max(stop_{t−1}, midden_t). De stop gaat nooit omlaag.
  - **Uitstap:** close_t < stop_{t−1} → uit. Op de dag van een uitstap geen nieuwe instap.
  - midden_t = (max + min van close over de laatste L dagen t/m t) / 2.
  - Toestanden worden elke run opnieuw berekend over alle opgehaalde historie (live: 1000 dagen).
- **Doelgewicht:** w_i = (1/N) × (aantal actieve toestanden / 9) × min(1; 0,25 / σ90_i). Dagelijks gecontroleerd.

## S2 — Vol-getarget gelijk verdeeld vasthouden (controle, geen trendsignaal)
- w_i = (1/N) × min(1; 0,25 / σ90_i). Dagelijks gecontroleerd.

## S3 — Wekelijkse marktschakelaar (naar Han, Kang & Ryu, 28 dagen)
- Controle alleen als de uitvoeringsdag een maandag is.
- M = gemiddelde over het universum van (close_t / close_{t−28} − 1).
- M > 0 → 1/N in elke munt; M ≤ 0 → 100% cash. Start in cash tot de eerste maandag.
- Tussen controles niets doen (behalve munten verkopen die uit het universum vallen).

## Benchmarks
- **B1:** 100% BTC/EUR, eenmalig kopen op dag 1, daarna vasthouden.
- **B2:** gelijk verdeeld universum (1/N): kopen op dag 1, herbalanceren alleen bij de maandelijkse universumwissel. Kosten meegerekend.

## Hypotheses
- **H1:** max drawdown van S1 ≤ 50% van die van B2, én Sharpe S1 ≥ Sharpe B2.
- **H2:** dagverschil S1 − S2 > 0 (trendvolgen voegt iets toe bovenop de positiegrootte).
- **H3:** dagverschil S1 − S3 > 0 (de complexere regel loont).
- **Toets:** gepaarde verschilreeks met block-bootstrap (blokken van 20 dagen).
- **Oordeel:** pas na ≥2 jaar forward plus backtest. De echte holdout voor S1 begint in april 2025. Een paper-test van maanden wijst géén winnaar aan.

## Controles na 6 maanden (geen oordeel over voorsprong)
- Draait de bot elke dag, zonder reconciliatiefouten?
- Kloppen omzet en blootstelling met de backtest over dezelfde periode?
- Stop en herzie de code als de drawdown groter wordt dan 1,5× de slechtste backtest-drawdown (de bot meldt dit zelf).

## Bekende beperkingen (vooraf benoemd)
- De backtest gebruikt de huidige Bitvavo-markten: verdwenen munten ontbreken (survivorship bias), dus de backtest is te optimistisch.
- Een gemiste dagrun wordt niet ingehaald; die dag gebeurt er niets.
- De 1/N-verdeling per munt in S1 is onze interpretatie van het paper.
- De drempels 20% band, 50% van B2-drawdown en 1,5× backtest-drawdown zijn eigen keuzes, niet uit een bron.

## Aanvulling 1 oktober 2026 — S4 en S5 (gericht op rendement)
Toegevoegd op verzoek, vóór het zien van een backtest. S1–S3, B1 en B2 blijven ongewijzigd.
Live gestart vanaf de eerstvolgende run (2 oktober 2026); hun rendement telt vanaf die dag.

### S4 — Trend-ensemble zonder volatiliteitsrem
- Zelfde 9 Donchian-toestanden per munt als S1, zelfde universum, band en kosten.
- w_i = (1/N) × (aantal actieve toestanden / 9). Geen 0,25/σ90-factor. Max 100% belegd.

### S5 — BTC-trend
- Alleen BTC/EUR, met de 9 Donchian-toestanden van S1 op BTC.
- w_BTC = aantal actieve toestanden / 9 (0–100%). Zelfde band en kosten. Volgt het universum niet.

### Hypotheses
- **H4:** CAGR S4 ≥ CAGR B2, én max drawdown S4 ≤ 70% van die van B2.
- **H5:** CAGR S5 ≥ CAGR B1, én max drawdown S5 ≤ 60% van die van B1.
- Zelfde toets en zelfde oordeelstermijn als hierboven (≥2 jaar forward + backtest).
- Drempels 70% en 60% zijn eigen keuzes, niet uit een bron.
- Totaal geteste varianten nu: 5 (S1–S5).

## Alleen loggen, niet gebruiken
Fear & Greed Index en BTC-funding rate worden dagelijks met tijdstempel opgeslagen (`state/observations.csv`) voor een latere, eerlijke A/B-test in een volgende versie.
