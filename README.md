# TBotai — paper-tradingbot

Test vooraf vastgelegde crypto-strategieën (nu S1–S4, S10 en de mixen M1, M2) met **nepgeld** en echte Bitvavo-koersen, tegen BTC vasthouden en een gelijk verdeeld mandje. Geen API-sleutels, geen echt geld.

- Regels en hypotheses: [`HYPOTHESIS.md`](HYPOTHESIS.md)
- Stand van de live-test: [`state/summary.md`](state/summary.md)
- Backtest-resultaten: [`results/`](results/) — oordeel per strategie in [`results/hypotheses.md`](results/hypotheses.md)

## Goud-bot (MGC)
Aparte forward test op gratis Yahoo-koersen in [`futures/`](futures/bot_mgc/README.md): zes goudstrategieën, elke werkdag via de workflow `mgc-paper`. Stand: [`futures/mgc_paper/DAGRAPPORT.md`](futures/mgc_paper/DAGRAPPORT.md).

## Obligatie-bot (ZN)
Fronttest van acht strategieën op de 10-jaars Treasury-future, ook op gratis Yahoo-koersen ([`futures/bot_zn`](futures/bot_zn/README.md)), elke werkdag via de workflow `zn-paper`. Stand: [`futures/zn_paper/DAGRAPPORT.md`](futures/zn_paper/DAGRAPPORT.md).

## Hoe het draait
- **Elke dag 00:17 UTC** start GitHub Actions (`paper-run`) de bot: signaal op het slot van gisteren, uitvoering tegen de open van vandaag, alles opgeslagen in `state/`.
- **Backtest:** handmatig via Actions → `backtest` → Run workflow.
- **Controle (elke maandag):** `verify` rekent alle live-dagen opnieuw uit met dezelfde code en vergelijkt elke trade, uitvoeringsprijs en equity. Uitkomst in `results/verify_live.md`; bij een verschil volgt een Telegram-melding.
- **Meldingen per run:** gemiste dagen en munten zonder verse slotkoers staan in het Telegram-bericht en in `state/summary.md`.
- **Tests:** draaien bij elke codewijziging.

## Noodstop
Maak een bestand `KILL` in de hoofdmap van de repo (inhoud maakt niet uit). De bot doet dan niets meer tot je het weer verwijdert.

## Telegram-meldingen (optioneel)
Zet twee secrets in GitHub (Settings → Secrets and variables → Actions): `TELEGRAM_BOT_TOKEN` en `TELEGRAM_CHAT_ID`.

## Lokaal draaien
```
pip install -r requirements.txt
python -m pytest -q          # tests
python run.py live           # één dag paper-run
python run.py download       # koersdata voor de backtest
python run.py backtest       # backtest
python run.py verify         # live-dagen opnieuw uitrekenen en vergelijken
```

## Bestanden
| Bestand | Wat |
|---|---|
| `config.yaml` | alle getallen (niet wijzigen tijdens de test) |
| `tbot/strategies.py` | S1–S4, S10, mixen M1/M2, B1, B2 (S7–S9 afgevallen, regels bewaard) |
| `tbot/portfolio.py` | nepgeld-portefeuille, kosten, band |
| `tbot/live.py` | de dagelijkse run |
| `tbot/backtest.py` | backtest met dezelfde code |
| `tbot/ledger.py` | logboek (SQLite) en reconciliatie |
| `tbot/verify.py` | controle: live-run tegen dezelfde code opnieuw uitgerekend |
| `learnings.md` | observaties en hypotheses (worden níét automatisch toegepast) |
