# Testoverzicht ZN-bot

Starten: dubbelklik `test_zn.bat`. Alle tests draaien tegen een nep-broker; de echte API wordt nooit aangeroepen. Het nummer verwijst naar plan §11.

| Nr | Test | Wat hij controleert |
|---|---|---|
| 1 | `test_rod_gewone_dag_maandag_en_na_feestdag` | De ROD klopt op een handgemaakte dataset, ook op een maandag (vergelijkt met vrijdag) en na MLK-dag. |
| 1 | `test_rod_niet_over_een_contractwissel` | Er wordt geen ROD berekend als gisteren een ander contract was. |
| 2 | `test_mediaan_alleen_vorige_60_dagen` | De filtermediaan gebruikt precies de vorige 60 dagen; oudere dagen tellen niet mee en "gelijk aan" is niet genoeg. |
| 2 | `test_vandaag_telt_niet_mee` | De ROD van vandaag zit niet in de mediaan (geen vooruitkijken). |
| 2 | `test_te_weinig_historie` | Met minder dan 60 dagen historie: `te_weinig_historie`. |
| 3 | `test_long_short_geen` | ROD > 0 geeft long, < 0 short, = 0 geen trade; benchmark B is altijd long. |
| 4 | `test_stop_hele_ticks_minimaal_4` | Stop = 1,5 × het gemiddelde, afgerond op hele ticks (4,5 wordt 5), minimaal 4 ticks. |
| 4 | `test_stop_prijs` | De limiet is de signaalprijs en de stop is 6 ticks bij een gemiddelde van 4. |
| 5 | `test_contracten` | $200 risico: stop 4 ticks geeft 3 ZN, 6 geeft 2, 7 geeft 1, 13 geeft 0 (`stop_te_groot`); nooit meer dan 3. |
| 5 | `test_halveren` | Binnen $600 van de bodem wordt het aantal gehalveerd (naar beneden); uitkomst 0 betekent overslaan. |
| 6 | `test_alleen_gevuld_bij_doorbraak_van_1_tick` | De limiet alleen raken geeft geen fill; een doorbraak van 1 tick wel, op de limietprijs. |
| 6 | `test_short_spiegelbeeld` | Voor short werkt de limiet-fill precies omgekeerd. |
| 6 | `test_niet_gevuld_voor_1435` | Een doorbraak pas om 14:35 is te laat: `niet_gevuld`, geen trade. |
| 6 | `test_stress_vraagt_2_ticks` | In de stresstest is een doorbraak van 2 ticks nodig. |
| 6 | `test_limiet_niet_gevuld_wordt_geannuleerd` | In sim wordt een niet-gevulde limietorder om 14:35 echt geannuleerd bij de (nep-)broker. |
| 7 | `test_eerst_fill_dan_stop` | Gaat één bar door de limiet én de stop, dan eerst de fill, dan de stop (stop − 1 tick). |
| 8 | `test_uitstap_1459_open_min_1_tick` | Tijdsuitstap om 14:59:00 op de opening van de 14:59-bar − 1 tick. |
| 8 | `test_stop_niet_meer_in_1459_bar` | Na 14:59:00 wordt de stop niet meer gecontroleerd (de positie is al dicht). |
| 8 | `test_geen_instap_na_143459` | Na 14:34:59 wordt niet meer ingestapt. |
| 9 | `test_geen_trade` | FOMC-dag, notulendag, vervroegde sluiting, kerstperiode en rolldag geven geen trade. |
| 9 | `test_weekend_en_feestdag` | Weekend en Thanksgiving geven geen trade. |
| 9 | `test_veilingdag_wel` | Op een dag met een Treasury-veiling om 13:00 ET wordt wél gehandeld. |
| 10 | `test_mismatchweek_okt_2026` | In 26–30 okt 2026 blijft het 14:30 ET, maar is het in Nederland 19:30 in plaats van 20:30. |
| 11 | `test_tick_kosten_r` | Tickwaarde $15,625, kosten $3,62 per contract en R kloppen tot op de cent. |
| 11 | `test_32ste` | De notatie in 32ste klopt (110-16, 110-16+, 109-31+). |
| 12 | `test_rolldatums` | De vaste rollregel geeft 20 nov 2026 (dec → mrt) en 19 feb 2027; de rolldag wordt herkend. |
| 12 | `test_afwijking_v0_wordt_gemeld` | Wijkt de .v.0-roll meer dan 3 handelsdagen af van de vaste regel, dan komt er een melding. |
| 12 | `test_backtest_rolldag_uit_v0` | In de backtest is de eerste dag op een nieuw .v.0-contract een `roll_dag` zonder trade. |
| 13 | `test_goede_instap_mag` | Een correcte limiet-instap tussen 14:30:00 en 14:34:59 wordt doorgelaten. |
| 13 | `test_foute_orders` | De guard weigert een market-instap, een stop als instap, 4 of 0 contracten, een fout symbool, het account van MES of MGC, een onbekend account, en orders te vroeg, te laat of na 16:10. |
| 13 | `test_foute_toestand` | De guard weigert een instap bij een open positie, een open instaporder, een FOMC-dag, NO-GO, een gestopte dag, een tweede trade en in paper. |
| 13 | `test_mes_mgc_account_ook_als_config_dat_zegt` | Ook als de config per ongeluk het MES-account noemt, wordt geweigerd. |
| 13 | `test_kill_switch` | Met het bestand STOP wordt elke instap geweigerd. |
| 13 | `test_stop_order` | Een stop-order moet de juiste kant en grootte hebben en mag alleen bij een open positie. |
| 13 | `test_sluiten_mag_altijd` | Sluiten mag altijd (ook na 16:10), maar alleen wat er open staat. |
| 13 | `test_weigering_wordt_gelogd` | Elke weigering staat in de log. |
| 14 | `test_geen_dubbele_order_na_time_out` | Na een time-out zoekt de bot de order op via zijn unieke tag en stuurt hij hem niet opnieuw. |
| 14 | `test_onbekende_positie_na_herstel_wordt_gesloten` | Staat er na een verbroken verbinding een onbekende positie, dan sluit de bot die en stopt hij voor die dag. |
| 14 | `test_opstartcheck_onbekende_positie` | Een onbekende positie bij het opstarten: niets doen, alarm, stoppen. |
| 15 | `test_stop_bestand_sluit_alles` | De kill switch (bestand STOP) sluit de open positie, annuleert de stop-order en stopt de bot. |
| 15 | `test_start_geweigerd_met_stop_bestand` | Zolang STOP bestaat, start de bot niet. |
| 16 | `test_paper_volledige_dag` | Een hele paperdag met een nep-broker die faalt bij elke order: er gaat geen order uit en de trade komt in het journal. |
| 17 | `test_60_verliezers_no_go_en_geen_orders` | 60 verliezende trades geven NO-GO en een rapport; daarna stuurt de bot in sim geen orders meer en logt hij in paper. |
| 17 | `test_59_verliezers_nog_geen_no_go` | Onder de 60 trades volgt nog geen automatische stop. |
| 17 | `test_slippage_melding` | Meer dan 1 tick slechtere slippage dan aangenomen geeft een melding. |
| 18 | `test_combine_geweigerd` | Een config met modus combine (of live/funded) wordt geweigerd. |
| 18 | `test_sim_zonder_account_of_met_mes_account` | Sim zonder account-ID of met het MES-account wordt geweigerd; paper mag. |
| 19 | `test_weekstop` | Na 4 verliezen in één week (−$905) wordt op vrijdag niet gehandeld (`weekstop`). |
| 19 | `test_weekstop_reset_volgende_week` | De maandag erna wordt weer gehandeld. |
| 19 | `test_max_een_trade_per_dag` | Nooit meer dan 1 trade per dag. |
| 20 | `test_bestaande_tests_groen` | Alle bestaande tests in `tests\` blijven groen. |
| – | `test_fill_stop_order_en_uitstap` | Een volledige simtrade: fill, stop-order bij de broker, om 14:59 stop annuleren en positie sluiten, journalregel. |
| – | `test_stop_order_mislukt_positie_dicht` | Weigert de broker de stop-order, dan sluit de bot de positie direct en stopt hij voor die dag. |
| – | `test_firmabeperking_niet_opnieuw` | Weigert de server de instap om een firmaregel, dan volgt geen tweede poging en stopt de bot voor die dag. |
| – | `test_rapport_en_journal` | De hele backtest-keten op nepdata maakt het HTML-rapport, alle CSV's en het journal, zonder dubbele rijen. |
| – | `test_eerste_run_alleen_laatste_dag_en_geen_orders` | De eerste fronttest-run speelt alleen de laatste handelsdag af, voor alle 8 strategieën, zonder één order. |
| – | `test_inhalen_en_niet_dubbel` | Stond de pc een week uit, dan worden alle gemiste dagen ingehaald; nog een keer draaien schrijft niets dubbel. |
| – | `test_voor_het_slot_nog_gisteren` | Vóór 15:20 New York-tijd telt de dag van gisteren als laatste complete dag (weekend: vrijdag). |
| – | `test_multi_A_geeft_dezelfde_trades` | Strategie A in de fronttest geeft precies dezelfde trades als de bestaande strategie A. |
| – | `test_veiling_D` | D handelt alleen op 5/10/30-jaars veilingdagen, van 13:01 tot 14:25. |
| – | `test_maandeinde_C` | C handelt alleen op de laatste 3 handelsdagen van de maand. |
| – | `test_drift_E_alleen_op_releasedag` | E handelt alleen op een dag met een 10:00-cijfer, van 09:59 tot 10:02. |
| – | `test_orb_G_breakout_en_beide_kanten` | G volgt een breakout; raakt één bar beide kanten, dan telt dat conservatief als verlies. |
| – | `test_reversal_H` | H gaat om 08:20 tegen een groot laatste half uur van gisteren in, tot 10:00. |
| – | `test_geen_vooruitkijken` | Een strategie krijgt alleen koersen vóór zijn eigen beslismoment te zien. |
| – | `test_fill_limiet_doorbraak` | Een limietorder wordt alleen gevuld als de koers er 1 tick doorheen gaat. |
