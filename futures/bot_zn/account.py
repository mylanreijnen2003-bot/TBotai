"""Virtueel 50K-account volgens firms/topstep_50k.json: saldo en bodem (MLL met EOD-trailing).

Gebruikt voor de halveerregel (saldo − bodem < $600) en de noodrem bodem, in backtest, paper én sim.
Het practice-account bij TopstepX heeft een ander saldo; de bot rekent daarom met dit virtuele account.
In de backtest begint het account opnieuw (nieuwe 'Combine') als de bodem wordt geraakt; dat wordt geteld.
"""


class VirtueelAccount:
    def __init__(self, firm, herstart_bij_bodem=True):
        self.firm = firm
        self.herstart = herstart_bij_bodem
        self.herstarts = 0
        self._reset()

    def _reset(self):
        self.start = self.firm["start_balance"]
        self.saldo = float(self.start)
        self.hoogste_slot = float(self.start)
        self.bodem = float(self.start - self.firm["max_loss"])

    def afstand_tot_bodem(self):
        return self.saldo - self.bodem

    def verwerk_trade(self, netto, mae=None):
        """Trade van vandaag. Geeft True als de bodem is geraakt (saldo + MAE <= bodem)."""
        laag = self.saldo + min(netto, mae if mae is not None else 0.0, 0.0)
        self.saldo += netto
        if laag <= self.bodem:
            if self.herstart:
                self.herstarts += 1
                self._reset()
            return True
        return False

    def herstart_na_vastlopen(self):
        """Halveren geeft 0 contracten en zonder trades verandert het saldo nooit: nieuw account (geteld)."""
        self.vastgelopen = getattr(self, "vastgelopen", 0) + 1
        self.herstarts += 1
        self._reset()

    def einde_dag(self):
        """EOD-trailing: bodem schuift mee met het hoogste slotsaldo, maximaal tot lock_level."""
        self.hoogste_slot = max(self.hoogste_slot, self.saldo)
        lock = self.firm.get("lock_level", self.start)
        self.bodem = min(self.hoogste_slot - self.firm["max_loss"], lock)
        self.bodem = max(self.bodem, self.start - self.firm["max_loss"])


def account_uit_trades(firm, trades):
    """Herbouwt het virtuele account uit eerdere trades [(datum, netto, mae)] (live: uit journal_bot.csv)."""
    acc = VirtueelAccount(firm, herstart_bij_bodem=False)
    huidige = None
    for datum, netto, mae in sorted(trades, key=lambda x: x[0]):
        if huidige is not None and datum != huidige:
            acc.einde_dag()
        huidige = datum
        acc.verwerk_trade(netto, mae)
    if huidige is not None:
        acc.einde_dag()
    return acc
