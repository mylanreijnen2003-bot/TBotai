# TBotai — paper-tradingbot

Test zes vooraf vastgelegde crypto-strategieën met **nepgeld** en echte Bitvavo-koersen, tegen BTC vasthouden en een gelijk verdeeld mandje. Geen API-sleutels, geen echt geld.

- Regels en hypotheses: [`HYPOTHESIS.md`](HYPOTHESIS.md)
- Stand van de live-test: [`state/summary.md`](state/summary.md) (dagstrategieën S1–S5)
- Stand van het 4-uurs spoor: [`state_4h/summary.md`](state_4h/summary.md) (S6)
- Backtest-resultaten: [`results/`](results/)

## Hoe het draait
- **Elke dag 00:17 UTC** start GitHub Actions (`paper-run`) de bot: signaal op het slot van gisteren, uitvoering tegen de open van vandaag, alles opgeslagen in `state/`.
- **Elke 4 uur** (`paper-run-4h`) het 4-uurs spoor S6 op BTC, ETH en SOL, met eigen logboek in `state_4h/`.
- **Backtest:** handmatig via Actions → `backtest` → Run workflow.
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
```

## Bestanden
| Bestand | Wat |
|---|---|
| `config.yaml` | alle getallen (niet wijzigen tijdens de test) |
| `tbot/strategies.py` | S1–S5, B1, B2 |
| `tbot/portfolio.py` | nepgeld-portefeuille, kosten, band |
| `tbot/live.py` | de dagelijkse run |
| `tbot/h4.py` | 4-uurs spoor S6 (live + backtest) |
| `tbot/backtest.py` | backtest met dezelfde code |
| `tbot/ledger.py` | logboek (SQLite) en reconciliatie |
| `learnings.md` | observaties en hypotheses (worden níét automatisch toegepast) |
