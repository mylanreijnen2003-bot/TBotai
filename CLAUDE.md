# Instructies voor AI-assistenten (Claude, Cursor)

Dit is een paper-tradingbot die vooraf vastgelegde strategieën eerlijk test. De eigenaar leest zelf (nog) geen code; leg wijzigingen kort en in het Nederlands uit.

## Harde regels
- **Wijzig nooit** de strategieregels, parameters of `config.yaml` van een lopende versie. `HYPOTHESIS.md` is leidend. Een wijziging = nieuwe `strategy_version` + nieuwe lege `state/`-map, en alleen op expliciet verzoek.
- **Geen echt geld.** Voeg geen orderplaatsing bij een beurs toe en vraag nooit om API-sleutels met handels- of opnamerechten.
- **Geen LLM in de beslisketen.** Signalen, risicoregels en orders zijn vaste code.
- Pas `state/` nooit met de hand aan: de reconciliatie stopt de bot bij verschillen.
- Backtest en live gebruiken dezelfde code (`tbot/engine.py`, `strategies.py`, `portfolio.py`). Houd dat zo.
- Nieuwe ideeën gaan naar `learnings.md` als hypothese, niet in de code.

## Werken
- Tests: `python -m pytest -q` (moeten altijd slagen, geen netwerk nodig).
- Commit-berichten in het Nederlands, kort.
