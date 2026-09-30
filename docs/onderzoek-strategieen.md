# Trendvolgen verdient de testplek, de rest niet

**Kort antwoord:** voor crypto-spot (geen hefboom, long of cash, posities van dagen tot weken, top 10-20 munten) heeft **trendvolgen per munt met volatiliteit-targeting als sizing** het sterkste bewijs dat na kosten overeind blijft. Trendvolgen betekent: kopen als de prijs stijgt en naar cash als de trend breekt. Volatiliteit-targeting betekent: de positie kleiner maken als de koers wilder beweegt. Ook bij 0,25% kosten per kant blijft de strategie staan. Maar het bewijs is vooral dat de **drawdown** (grootste daling van piek naar dal) sterk omlaag gaat. Dat hij na 2022 **meer rendement** haalt dan buy-and-hold (kopen en vasthouden), is niet aangetoond. Cross-sectioneel momentum ("koop de sterkste munten") en korte-termijn mean reversion ("koop de dip") hebben in de meest liquide munten zwak of negatief bewijs. Voor sentiment-, on-chain- en LLM-signalen is geen enkel onderzoek gevonden dat na kosten robuust werkt. Een deel ervan kun je bovendien niet zonder lookahead-bias backtesten (lookahead-bias: in een test per ongeluk informatie gebruiken die je toen nog niet had). Advies: leg drie strategieën vast.

| Code | Strategie | Rol |
|---|---|---|
| S1 | Donchian-trend-ensemble met 25% vol-target | hoofdkandidaat |
| S2 | Vol-getarget equal-weight vasthouden, zonder trendsignaal | controle: werkt trend, of alleen minder blootstelling? |
| S3 | Wekelijkse aan/uit-schakelaar op 28-daags marktmomentum | simpele uitdager |

Alle drie worden vergeleken met BTC vasthouden en een equal-weight mandje vasthouden (equal-weight: elke munt krijgt evenveel geld). Belangrijk om vooraf te weten: een paper-test van een paar maanden kan **geen** winnaar aanwijzen. Om Sharpe 1,0 van 0,5 te onderscheiden heb je ongeveer 11 jaar data nodig. De paper-test controleert dus of je code en je kostenaannames kloppen. Het echte bewijs moet uit een eerlijke point-in-time backtest komen, plus een lange forward-periode.

| Begrip | Betekenis |
|---|---|
| Sharpe | rendement gedeeld door beweeglijkheid (per jaar). Hoger = beter rendement per eenheid risico |
| CAGR | gemiddeld jaarrendement met rente-op-rente |
| σ (vol) | geannualiseerde standaardafwijking van dagrendementen: hoe wild de koers beweegt |
| Point-in-time | per datum alleen de data gebruiken die er toen was, inclusief munten die later verdwenen |
| Survivorship bias | vertekening doordat je alleen munten test die nu nog bestaan |
| Overfitting | parameters zo lang bijstellen tot het verleden mooi past. Werkt daarna meestal niet meer |
| Taker / maker | taker = marktorder (duurder), maker = limietorder die in het orderboek blijft staan (goedkoper) |
| Slippage | verschil tussen de verwachte prijs en de prijs waartegen je order echt wordt uitgevoerd |

## Trendvolgen per munt halveert drawdowns, maar wint niet op rendement

Het best gedocumenteerde en direct codeerbare recept is **Zarattini, Pagani & Barbon (2025), "Catching Crypto Trends"**. Het combineert negen Donchian-kanalen (5, 10, 20, 30, 60, 90, 150, 250 en 360 dagen) op slotkoersen per dag. Een Donchian-kanaal is de hoogste en laagste slotkoers over de laatste N dagen. De strategie koopt bij een nieuwe N-daagse top. De uitstap is een trailing stop op het midden van het kanaal: die stop gaat alleen omhoog, nooit omlaag. De positie is 25% gedeeld door de 90-daagse volatiliteit, met een herbalanceerband van 20% om onnodige trades te beperken. Het universum is de top-20 meest liquide munten, elke maand opnieuw gekozen uit een survivorship-vrije dataset van 21.616 munten. Over 2015 tot maart 2025, na 10 bps kosten, haalt het gespreide portfolio **CAGR 18%, Sharpe 1,57 en max drawdown 11%**. Alleen op BTC: **CAGR 30%, Sharpe 1,58, max drawdown 19%**, tegen een **drawdown van ~80% voor BTC vasthouden** ([Concretum PDF](https://concretumgroup.com/wp-content/uploads/2026/02/Catching-Crypto-Trends.pdf)). Kosten maken het niet kapot: op BTC zakt de CAGR van 30% bij 0 bps naar **~26% bij 25 bps per kant** ([Concretum PDF](https://concretumgroup.com/wp-content/uploads/2026/02/Catching-Crypto-Trends.pdf)). In het paper mocht de positie tot 200% (2x hefboom). Voor spot wordt dat een cap van 100%. Omdat 25%/σ bij munten met 60-100% volatiliteit meestal ruim onder 1 blijft, zal die cap zelden knellen. Dat laatste is onze inschatting en niet getest.

Onafhankelijke studies wijzen dezelfde kant op. Detzel e.a. (Financial Management 2021) testten "long BTC als de prijs boven het N-daags gemiddelde staat, anders cash". Die regel verhoogde de Sharpe en verlaagde de drawdown. De break-even-kosten per kant lagen tussen **1,1% (MA5) en 4% (MA100)**, dus ver boven Bitvavo-tarieven. Out-of-sample waren alleen MA20 tot MA100 positief. De snelle MA5 en MA10 waren dat niet ([Detzel WP](https://community.portfolio123.com/uploads/short-url/jS0qs8gndLATbD3WlYQ79thDnzD.pdf)). Out-of-sample betekent: getest op data die niet is gebruikt om de regel te kiezen. Han, Kang & Ryu zijn een van de weinige studies waarvan de data door 2022 loopt (tot augustus 2023). Hun marktbrede long-only trendregel met 28 dagen terugkijken haalt na 15 bps **Sharpe 1,51 tegen 0,85 voor de markt**, met max drawdown 61,8% tegen 89,1%. De strategie zit ~48% van de tijd in de markt ([ACFR PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)). Een ensemble (meerdere lookbacks tegelijk) is het robuustst. Het Zarattini-ensemble heeft de laagste drawdown van alle losse lookbacks. Man Group vindt dat de Sharpe piekt bij **10-15 munten**, omdat munten onderling gemiddeld ~0,6 gecorreleerd zijn ([Man Group](https://www.man.com/insights/in-crypto-we-trend)).

De zwaktes zijn stevig. Zarattini heeft **geen holdout-periode en geen resultaten per jaar**: het is één backtest over de hele periode ([Concretum PDF](https://concretumgroup.com/wp-content/uploads/2026/02/Catching-Crypto-Trends.pdf)). De parameters zijn dus pas echt out-of-sample vanaf april 2025. Hudson & Urquhart vonden in een peer-reviewed test **geen out-of-sample-voorspelbaarheid voor BTC**, wel voor andere munten ([RePEc](https://ideas.repec.org/a/spr/annopr/v297y2021i1d10.1007_s10479-019-03357-1.html)). Momentum is "almost non-existent when the market is bearish" ([ACFR PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)). Voor long/cash betekent dat: in een beermarkt zit je in cash, en de winst komt uit een handvol grote stijgingen. De 30-daagse variant had gemiddeld **+17% per winnende trade tegen −5% per verliezende**, bij een winkans van 40-60%. Een replicatie op BTC/ETH/SOL tot juni 2025 had een bootstrap-betrouwbaarheidsinterval voor de Sharpe van **ruwweg 0,1 tot 1,5**, en een CAGR ver onder die van BTC vasthouden ([Summitward](https://summitward.com/learn/crypto-trend-following)). Dit is een blog en niet peer-reviewed. De strategie faalt in **zijwaartse, schokkerige markten** (veel valse uitbraken) en loopt **achter in sterke bullruns**, omdat vol-targeting de blootstelling laag houdt.

## Volatiliteit-targeting verlaagt risico, niet per se rendement

Vol-targeting verdient zijn plek als **sizing-laag** (regel voor hoe groot een positie is), niet als bron van extra rendement. Moreira & Muir (2017) vonden op aandelen hogere Sharpes. Met een cap van 1,0x (geen hefboom) blijft de Sharpe-winst staan (0,52), maar **halveert de alpha van 4,86% naar 2,12%** ([Moreira & Muir](https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf)). Alpha is het rendement boven wat de markt zelf opleverde. Cederburg e.a. testten 103 strategieën en vonden dat vol-gemanagede portfolio's in real-time **niet systematisch beter** zijn dan de onbeheerde versie ([EconPapers](https://econpapers.repec.org/article/eeejfinec/v_3a138_3ay_3a2020_3ai_3a1_3ap_3a95-117.htm)). Wat wel consistent terugkomt: minder extreme verliezen, en Sharpe-winst bij "risico-assets" ([Alpha Architect](https://alphaarchitect.com/volatility-targeting-improves-risk-adjusted-returns/)). In crypto verdubbelde vol-scaling de uitbetaling van top-30-momentum, van 0,90% naar 1,86% per week ([Springer](https://link.springer.com/article/10.1007/s11408-025-00474-9)). In de BTC/ETH/SOL-replicatie haalde **vol-scaling zonder trendsignaal de max drawdown van 84% naar 17%**. Een vol-gemanaged equal-weight mandje zonder trend kwam uit op Sharpe 1,24 en max drawdown 19,9% ([Summitward](https://summitward.com/learn/crypto-trend-following)). Daarom S2: als S1 niet duidelijk beter doet dan S2, komt de winst van S1 uit lagere blootstelling en niet uit trendvolgen.

## Cross-sectioneel momentum en mean reversion houden geen stand in de top-15

Cross-sectioneel momentum ("koop elke week de munten die de afgelopen 2-4 weken het best presteerden") werkte in oude, brede universums. Liu, Tsyvinski & Wu vonden **3,3-4,1% per week** voor long-short over 2014-2018, zonder kosten ([NBER](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf)). De enige directe test op de **30 grootste munten** vindt over 2016-2023 een **niet-significant** effect, en **na juli 2020 zelfs negatief**. Eén enkele munt leverde 37% van het totale rendement ([Springer](https://link.springer.com/article/10.1007/s11408-025-00474-9)). De long-only-versies zijn nog zwakker. Starkiller ging van +69% per jaar in-sample naar **−2,35% per jaar out-of-sample** ([Starkiller](https://www.starkiller.capital/post/cross-sectional-momentum-in-cryptocurrency-markets)). Een replicatie van "top-3 op 60 dagen, 10 majors, 2021-2026" gaf **CAGR −7,7%**, en met een BTC>200d-filter +10,8% bij Sharpe 0,14. Dat is nog steeds onder equal-weight vasthouden (Sharpe 0,42) ([GitHub](https://github.com/IsaacDodds/crypto-momentum-backtest)). Die replicatie is een hobbyproject en niet peer-reviewed. Han e.a. vonden dat van 21 geoptimaliseerde varianten er **maar 6 de markt versloegen en 5 failliet gingen** ([ACFR PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)). Met 10-20 munten is de "topgroep" bovendien maar 2-4 munten, dus sterk geconcentreerd.

Voor mean reversion is het beeld nog duidelijker negatief. In de meest liquide munten keren rendementen niet om, maar lopen ze juist door. Het reversal-effect zit in kleine, illiquide munten ([RePEc](https://ideas.repec.org/a/eee/finana/v78y2021ics1057521921002349.html)). Bij grote munten is het maar **0,44% per dag** ([Fairfield PDF](https://digitalcommons.fairfield.edu/cgi/viewcontent.cgi?article=1249&context=business-facultypubs)). Omkering binnen de dag bestaat wel in majors, maar levert **~1,3 bp per trade tegen 5 bp kosten** per retour, dus te klein om te verdienen ([arXiv](https://arxiv.org/html/2608.21888v1)). De regel "koop BTC op een 10-daags dieptepunt" had een drawdown van **meer dan 80%** ([Quantpedia](https://quantpedia.com/trend-following-and-mean-reversion-in-bitcoin/)).

## Regimefilters en alternatieve signalen zijn onbewezen, en deels niet eerlijk te backtesten

Een BTC>200d-filter houdt in: alleen in altcoins als BTC boven zijn 200-daags gemiddelde staat. Hiervoor is **geen peer-reviewed out-of-sample-test** gevonden. De replicatie hierboven laat zien dat zo'n filter de drawdown ongeveer halveert "zonder alpha te genereren" ([GitHub](https://github.com/IsaacDodds/crypto-momentum-backtest)). Als elke munt al zijn eigen trendregel heeft, zoals in S1, voegt zo'n filter vrijwel niets toe. We bouwen hem daarom niet in. Test hem hooguit later als losse variant in de backtest.

Voor de Fear & Greed Index zijn de bevindingen tegenstrijdig. Een recente strenge test vindt **out-of-sample R² −1,1%** en concludeert dat de index vooral op de prijs reageert ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S305070062600006X)). Een oudere studie vindt wel voorspelkracht op 1 dag tot 1 week ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S154461232300778X)). Nieuwssentiment gescoord met ChatGPT leverde **out-of-sample geen significante winst** ([Springer](https://link.springer.com/article/10.1186/s40537-026-01392-x)). Een LLM backtesten op data van vóór zijn trainingsdatum is bovendien besmet, omdat het model de afloop "kent" ([arXiv](https://arxiv.org/abs/2512.23847)). On-chain data (gegevens direct van de blockchain) wordt achteraf herzien. Een exchange-flow-strategie presteerde "notably worse" op point-in-time data, en die point-in-time data is alleen beschikbaar in het betaalde Professional-plan van Glassnode ([Glassnode](https://research.glassnode.com/why-use-point-in-time-data/)). MVRV-cycle-timing laat een mooie Sharpe zien (1,28 tegen 0,45), maar steunt op **slechts 3 cycli** ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0275531926002138)). Advies: gebruik dit nu nergens als signaal. Log wel vanaf dag 1 elke dag met tijdstempel de Fear & Greed-waarde ([gratis API](https://alternative.me/crypto/fear-and-greed-index/)) en de funding rates. Funding rate is de periodieke vergoeding tussen long- en short-houders op perpetual futures; hoge funding wijst op overvolle longs en liquidatierisico ([CEPR](https://cepr.org/voxeu/columns/crypto-carry-market-segmentation-and-price-distortions-digital-asset-markets)). Zo bouw je een eigen eerlijk archief op voor een latere A/B-test.

| Familie | Bewijs na kosten (spot, top 10-20) | Faalt in | Oordeel |
|---|---|---|---|
| Trendvolgen per munt (ensemble) | Middel-sterk; lagere drawdown robuust, extra rendement na 2022 onbewezen | zijwaartse markten, V-herstel, sterke bull (loopt achter) | **Testen (S1)** |
| Vol-targeting als sizing | Sterk voor risicoreductie, zwak voor alpha | lage-vol rally's | **Testen (S2, en als laag in S1)** |
| Marktbrede trendschakelaar | Middel (1 studie t/m 2023) | schokkerige markten | **Testen (S3)** |
| Cross-sectioneel momentum long-only | Zwak/negatief na 2020 | na 2020, crashes van één munt | Niet testen |
| Korte-termijn mean reversion | Negatief in liquide munten | trends, crashes | Niet testen |
| BTC-200d-regimefilter | Alleen hobby-/blogbewijs | – | Later als losse variant |
| Sentiment / on-chain / LLM | Geen robuust bewijs; lookahead-risico | – | Alleen loggen |

## Kosten op Bitvavo: omzet is de vijand, niet de spread

Bitvavo rekent op EUR-paren **0,25% taker en 0,15% maker** onder €100k volume per 30 dagen ([Bitvavo](https://bitvavo.com/en/fees)). De gemiddelde spread (verschil tussen bied- en laatprijs) voor BTC, ETH, SOL, XRP en ADA is slechts **~1 bp** ([Kaiko/Bitvavo](https://bitvavo.com/en/news/kaiko-report-2026)). Voor majors bepaalt de fee dus bijna alle kosten. Een retour met marktorders kost ~0,5%. Wie 50 keer per jaar het hele portfolio omzet, betaalt ~25% per jaar aan fees. Daarom kiezen we dagcandles, een herbalanceerband van 20% en geen snelle intraday-regels. Kostenaanname: **0,30% per kant als basis** (0,25% fee + 0,05% slippage) en **0,60% als stresstest**.

Survivorship bias is bij equal-weighting geen detail. In één dataset verdween 31% van de munten, met een gemiddeld rendement bij verdwijnen van **−77,8%**. De vertekening was **62% per jaar bij equal-weight** tegen 0,9% bij marktwaarde-weging ([St. Gallen PDF](https://www.alexandria.unisg.ch/bitstreams/2bc8397d-47dd-4f66-8467-9004b2c9d212/download)). Een backtest op "de huidige top-15 terug in de tijd" is dus waardeloos. Bouw het universum per maand opnieuw op uit historische data waarin ook dode munten zitten ([Concretum-handleiding](https://concretumgroup.com/building-a-survivorship-bias-free-crypto-dataset-with-coinmarketcap-api/)).

## Een paper-test van maanden bewijst geen voorsprong

De standaardfout van een Sharpe is ongeveer √(1/T), met T in jaren ([Portfolio Optimizer](https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/)). Na 6 maanden is die ~1,4. Een gemeten Sharpe van 1,0 is dan statistisch niet te onderscheiden van −1,8 of +3,8. Ook met langere looptijden blijft het lastig:

| Vergelijking | Nodige looptijd |
|---|---|
| Sharpe 1,0 tegen 0 | ~2,7 jaar |
| Sharpe 1,0 tegen 0,5 | ~11 jaar |
| Twee strategieën onderling, correlatie 0 | ~22 jaar |
| Twee strategieën onderling, correlatie 0,9 | ~2,2 jaar |

Dit zijn eigen berekeningen met de formules van [Portfolio Optimizer](https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-hypothesis-testing-and-minimum-track-record-length-for-the-difference-of-sharpe-ratios/). Correlatie meet hoe sterk twee rendementsreeksen samen bewegen (1 = identiek). Een simulatie van twee strategieën over 52 weken gaf ~48% kans dat de ene de andere verslaat: een muntworp (zelfde bron). Tel je per trade in plaats van per dag, dan heb je **100-400 trades** nodig voor t ≥ 2. S1 maakt vooral kleine, onderling afhankelijke aanpassingen, dus trades tellen misleidt hier. Test daarom de **dagelijkse verschilreeks** (strategie min benchmark) met een HAC-test of block-bootstrap (Ledoit-Wolf). Dat zijn statistische tests die rekening houden met dikke staarten en met dagen die op elkaar lijken ([PeerPerformance docs](https://search.r-project.org/CRAN/refmans/PeerPerformance/html/sharpeTesting.html)).

| Een paper-test van 3-6 maanden kan WEL aantonen | Een paper-test van 3-6 maanden kan NIET aantonen |
|---|---|
| Dat de code doet wat de backtest doet (per dag vergelijken met een backtest-replay over dezelfde periode) | Welke strategie beter is |
| Dat de echte kosten en slippage binnen de aanname van 0,30% per kant vallen | Of een strategie buy-and-hold verslaat |
| Dat omzet en blootstelling in de verwachte orde liggen | Of de backtest-Sharpe echt is |
| Grove fouten: een Sharpe ver onder de backtest-verwachting, of een drawdown ruim boven het historisch slechtste | |

Beperk ook het aantal varianten dat je probeert. Hoe meer je test, hoe groter de "haircut" op de Sharpe: bij 200 tests daalt een Sharpe van 0,75 naar 0,32 ([Harvey & Liu](https://www.cmegroup.com/education/files/backtesting.pdf)). Een haircut is de verlaging die je toepast omdat je veel varianten hebt geprobeerd en de beste eruit pikte.

## Aanbeveling: deze drie leggen we vast

**Waarom deze drie:** S1 heeft het sterkste gepubliceerde bewijs, inclusief 2022, een survivorship-vrij universum en kostengevoeligheid. S2 is dezelfde machine zonder trendsignaal. Het is de eerlijkste controle op de vraag of trendvolgen iets toevoegt bovenop "minder blootstelling". S3 test of een veel simpelere regel even goed is. Als dat zo is, verdient simpel de voorkeur. De drie strategieën zijn sterk met elkaar gecorreleerd, dus onderlinge verschillen worden sneller zichtbaar dan tegen onafhankelijke strategieën. Toch duurt dat jaren, niet maanden. De sizing per munt (1/N per munt-slot) is onze interpretatie. De notities bevestigen niet exact hoe Zarattini het kapitaal over munten verdeelt.

```text
# HYPOTHESIS.md — vastgelegd vóór start, niet meer wijzigen

## Gemeenschappelijk
Data:            dagcandles Bitvavo EUR, slot = 00:00 UTC
Uitvoering:      signaal op slot dag t, fill = open dag t+1 (+ kosten)
Kosten:          0,30% per kant op elke verhandelde euro (basis); 0,60% (stresstest)
Cash:            0% rente
Startkapitaal:   €10.000 per strategie/benchmark (paper)
σ90_i:           stdev(dagelijkse log-rendementen, 90 dagen) × √365
Universum:       elke 1e van de maand 00:00 UTC: top N=15 EUR-paren op
                 mediaan dagvolume in EUR (volume × close) over 30 dagen;
                 eisen: ≥365 dagen koershistorie; mediaan |dagrendement| ≥0,5%
                 (sluit stablecoins uit); geen wrapped/tokenized varianten
                 (handmatige uitsluitlijst, vooraf vastgelegd).
                 Munt valt uit universum -> positie volledig verkopen.
Band:            handel een munt alleen als |huidig − doel| / doel > 20%,
                 of bij doel 0 -> >0 (instap) of >0 -> 0 (uitstap)

## S1 — Donchian-trend-ensemble, spot (naar Zarattini/Pagani/Barbon 2025)
Lookbacks L:     5, 10, 20, 30, 60, 90, 150, 250, 360 dagen
Per munt i, per L, toestand s ∈ {0,1}:
  Instap:        s=0 en close_t ≥ max(close_{t−L} … close_{t−1}) -> s=1,
                 stop = (max + min van close over laatste L dagen) / 2
  Stop-update:   zolang s=1: stop_t = max(stop_{t−1}, Donchian-midden_t)
  Uitstap:       close_t < stop_{t−1} -> s=0
  Warme start:   toestanden berekend over volledige historie
Doelgewicht:     w_i = (1/N) × (Σ_L s_{i,L} / 9) × min(1, 0,25 / σ90_i)
Check:           dagelijks. Totale blootstelling ≤100% (geen hefboom)

## S2 — Vol-getarget equal-weight vasthouden (controle, geen trendsignaal)
Doelgewicht:     w_i = (1/N) × min(1, 0,25 / σ90_i)
Check:           dagelijks, zelfde band

## S3 — Wekelijkse marktschakelaar (naar Han/Kang/Ryu, 28d lookback)
Check:           elke maandag 00:00 UTC
Signaal:         M = gemiddelde over universum van (close_t / close_{t−28} − 1)
Positie:         M > 0 -> 1/N in elke munt (100% belegd); M ≤ 0 -> 100% cash
Tussen checks:   niets doen

## Benchmarks
B1:              BTC-EUR 100%, eenmalig kopen
B2:              equal-weight universum (1/N), herbalanceren alleen bij
                 maandelijkse universumwissel; kosten meegerekend

## Metingen
Dagelijks: equity, gewichten, trades, betaalde fees, slippage.
Rapport: CAGR, Sharpe (dag × √365), max drawdown, Calmar,
omzet, % tijd belegd.

## Hypotheses
H1: S1 max drawdown ≤ 50% van B2's max drawdown, Sharpe S1 ≥ Sharpe B2
H2: S1 − S2 dagverschil > 0 (trend voegt iets toe bovenop sizing)
H3: S1 − S3 dagverschil > 0 (complexiteit loont)
Toets:           gepaarde verschilreeks, Ledoit-Wolf HAC / block-bootstrap
Oordeel:         pas na ≥2 jaar forward + point-in-time backtest
                 2018–nu (echte holdout S1: vanaf apr 2025)

## Implementatiechecks na 6 maanden (geen oordeel over voorsprong)
- paper vs backtest-replay: afwijking in dagrendement klein en verklaarbaar
- gerealiseerde kosten per kant ≤ 0,30%; zo niet -> kosten herzien
- stop en herzie de code als drawdown > 1,5× slechtste backtest-drawdown
```

De drempels van 20% band, 50% van de B2-drawdown en 1,5× slechtste drawdown komen niet uit een bron. Het zijn eigen, vooraf vastgelegde keuzes. Controleer ook de minimale ordergrootte op Bitvavo: in S1 worden de deelposities per munt klein.

**Bewust NIET testen:** cross-sectioneel momentum (negatief na 2020 in large caps), mean reversion en RSI-dipkopen (geen bewijs in liquide munten, risico op drawdowns van meer dan 80%), 4-uurs- of intraday-regels (geen spot-bewijs, hoge kosten), de BTC-200d-filter als los signaal (overbodig naast S1), hefboom, perpetuals en shorts (buiten scope, en in de studies deed de shortkant het slechter), ML-factoren zoals CTREND (long-short, complex, niet te repliceren zonder een grote dataset) en sentiment-, on-chain- en LLM-filters (alleen loggen, later A/B-testen).

## Bronnen om verder te lezen, gratis of goedkoop

| Bron | Waarom |
|---|---|
| [Catching Crypto Trends (PDF)](https://concretumgroup.com/wp-content/uploads/2026/02/Catching-Crypto-Trends.pdf) | Het recept achter S1 |
| [Concretum: survivorship-vrije dataset bouwen](https://concretumgroup.com/building-a-survivorship-bias-free-crypto-dataset-with-coinmarketcap-api/) | Nodig voor een eerlijke backtest |
| [Rob Carver: start here](https://qoppac.blogspot.com/p/systematic-trading-start-here.html) + [pysystemtrade](https://qoppac.blogspot.com/p/pysystemtrade.html) | Gratis basis voor systematisch handelen |
| [Robot Wealth mini course](https://robotwealth.com/trade-like-a-quant-mini-course/) | Gratis beginnersfouten en werkwijze |
| [Portfolio Optimizer: PSR/MinTRL](https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/) | Hoe lang je moet testen |
| [Harvey & Liu, Backtesting](https://www.cmegroup.com/education/files/backtesting.pdf) + [pypbo](https://github.com/esvhd/pypbo) | Overfitting meten |
| [Liu & Tsyvinski (NBER)](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf) | Hoe crypto-factoren getest worden |

## Conclusie

Het eerlijke beeld is minder spannend dan de headline-Sharpes doen vermoeden. Wat in crypto-spot robuust lijkt, is geen rendementsmachine. Het is **een manier om de 80%-dalen te ontlopen en een deel van de grote stijgingen mee te pakken**, tegen de prijs van achterblijven in sterke bullruns. De belangrijkste vraag voor dit project is dus niet "verslaat de bot BTC?", maar "levert S1 een vergelijkbaar rendement per eenheid risico met een veel kleinere drawdown, en komt dat door trendvolgen (S1 tegen S2) of alleen door minder blootstelling?".

Dat antwoord komt niet uit enkele maanden paper trading. Het komt uit een point-in-time backtest met een echte holdout vanaf april 2025, aangevuld met jaren aan forward-data. Leg de regels nu vast en verander ze niet meer. Zie de paper-test als controle van code en kosten, niet als scheidsrechter.
