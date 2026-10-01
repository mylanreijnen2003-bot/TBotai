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

## Aanvulling 1 oktober 2026 — S6, 4-uurs trendsprongen (apart spoor)
Toegevoegd op verzoek (korte stijgingen van 1–3 dagen meepakken), vóór het zien van een backtest.
Eigen logboek in `state_4h/`, draait elke 4 uur. Raakt S1–S5 niet.

- **Munten:** BTC/EUR, ETH/EUR, SOL/EUR. Elk krijgt 1/3 van het vermogen bij instap.
- **Candles:** 4 uur (UTC). Signaal op het slot van candle t, uitvoering tegen de open van candle t+1.
- **Instap:** slot ≥ hoogste slot van de vorige 20 candles (±3,3 dagen).
- **Vangnet:** midden van het 20-candle-kanaal (max + min van de laatste 20 sloten / 2); schuift alleen omhoog.
- **Uitstap:** slot onder het vangnet van de vorige candle. Geen nieuwe instap op dezelfde candle.
- **Tussendoor:** geen bijsturing van een lopende positie.
- **Kosten:** 0,30% per kant (live). Backtest ook 0,15% (limietorders) en 0,60%.
- **Gemiste runs:** tot 12 gemiste candles (2 dagen) worden achteraf in volgorde verwerkt.
- **Benchmarks in dit spoor:** HB1 = 100% BTC vasthouden, HB3 = 1/3 BTC, ETH, SOL vasthouden.

### Hypothese
- **H6:** na 0,30% kosten: CAGR S6 ≥ CAGR S5 (dagversie) én ≥ CAGR HB3, met max drawdown ≤ 60% van HB3.
- Als S6 bij 0,30% kosten onder S5 eindigt, levert de korte termijn niets extra op; dan stoppen we S6.
- De drempel 60% en de lookback 20 zijn eigen keuzes, niet uit een bron.
- Totaal geteste varianten nu: 6 (S1–S6).

## Aanvulling 1 oktober 2026 (middag) — S7 t/m S10, gericht op ≥20% per jaar
Vastgelegd vóór de backtest. Regels en getallen staan in `config.yaml` (s7–s10). Live vanaf de eerstvolgende run.
Bron S7–S9: onderzoek "drie nieuwe spot-strategieën" (1 okt 2026). S10 is opgesteld ná een snelle verkenning
op de BTC-reeks (100/200/350-daags gemiddelde) en telt daarom als zwakker bewijs.

- **S7 — S4 × BTC-regime:** S4-doelgewichten × R_t, R_t = 1 als BTC/EUR-slot > SMA200 (gewoon 200-daags gemiddelde), anders 0. Dagelijks, band 20%.
- **S8 — BTC/ETH traag momentum:** per munt s1 = slot_t > slot_(t−28), s2 = slot_t > slot_(t−84), s3 = slot_t > SMA200; w = ½ × (s1+s2+s3)/3, rest cash. Alleen bijsturen op maandag-open (signaal zondagslot), zonder band. Robuustheid: zelfde regels met elke weekdag; het CAGR-criterium gebruikt het gemiddelde van de 7 varianten.
- **S9 — Keltner/Donchian met ratchet-stop:** universum = top-15. Upper = min(hoogste slot 20d, EMA20 + 2·ATR20); Lower = max(laagste slot 40d, EMA40 − 2·ATR40). Instap: slot_t ≥ Upper_(t−1); stop = max(stop, Lower_t), nooit omlaag; uitstap: slot_t < stop_(t−1). w = min(1,5/N; (1/N)/σ90), totaal ≤ 100%. Band 20% (instap/uitstap altijd).
- **S10 — BTC-cyclus:** w_BTC = aantal van [slot > SMA100, SMA200, SMA350] / 3. Dagelijks, band 20%.

### Doelen (H7–H10), elk geldt pas als ALLE punten gehaald zijn
- CAGR ≥ 20% bij 0,30% kosten (backtest maart 2020 t/m sept 2026; S8: gemiddelde van de 7 weekdagvarianten).
- Max drawdown ≤ 30% (S7), ≤ 35% (S8, S9), ≤ 2/3 van die van B1 (S10).
- CAGR ≥ 15% bij 0,60% kosten.
- Holdout (vanaf april 2025) CAGR ≥ 0% én ≥ B1. Let op: deze periode is al gezien, dus dit is een extra check, geen schone test.
- Deflated Sharpe ≥ 0,90 met N = 10 geteste varianten (S1–S10).
- Uitkomst wordt automatisch geschreven naar `results/hypotheses.md`.
- Wat zakt, gaat eruit. Wat slaagt, draait minimaal 12 maanden live op nepgeld voordat er iets met echt geld gebeurt.

## Afgevallen op 1 oktober 2026 (backtest, vóór live-start)
Volgens de vooraf vastgelegde hypotheses verwijderd. Ze tellen mee als geteste varianten.
- **S5 (BTC-trend):** H5 niet gehaald — CAGR 27,2% tegen 39,9% voor B1, max drawdown −47% (grens: 60% van B1 = −44%).
- **S6 (4-uurs trendsprongen):** H6 niet gehaald — bij 0,30% kosten −1,8% per jaar (2021-08 t/m 2026-09), holdout −30% per jaar; 772 trades, 30% winstgevend.
- Details in `results/` en `learnings.md`. Code staat in de git-geschiedenis.

## Alleen loggen, niet gebruiken
Fear & Greed Index en BTC-funding rate worden dagelijks met tijdstempel opgeslagen (`state/observations.csv`) voor een latere, eerlijke A/B-test in een volgende versie.
