# Tests MGC-bot

Draaien: `cd futures && python -m pytest -q bot_mgc` (of vanuit de hoofdmap `python -m pytest -q`). Geen netwerk nodig.

| Bestand | Wat |
|---|---|
| `test_forward.py` | De forward test op een nep-Yahoo-bron: **zelfde trades als de backtest-code** (alle 6 strategieën), geen dubbele verwerking, gemiste dagen inhalen, vandaag pas na het slot, wachten en dan `geen_data`, terugval op GC=F, noodstop, dagrapport. |
| `test_strategie.py` | ROD, filter zonder vooruitkijken, richting, stop, positiegrootte, halveren, weekstop. |
| `test_varianten.py` | D (ochtendsignaal), E (beide eens), R (zelfde dagen als A, vaste munt), gat over de stop, eindoordeel forward test. |
| `test_fills_kalender.py` | Instap/uitstap/stop op 1-minuutbars, kosten en slippage, feestdagen, zomertijd, rolldata. |
| `test_backtest_rapport.py` | De backtest-keten met Monte Carlo en het rapport (voor als er later toch historische data komt). |
