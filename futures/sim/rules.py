"""Firma-regels: speelt trades dag voor dag af en geeft PASS / FAIL / RUNNING.

Een trade is een dict met:
  net_pnl : winst of verlies in dollars (na kosten)
  mae     : grootste openstaande verlies tijdens de trade, als negatief getal (mag None zijn)
"""
from .config import load_firm  # noqa: F401  (hergebruikt door andere modules)

_FIRM_DEFAULT = object()


class Tracker:
    """Houdt de stand van één evaluatie-account bij. Voer het dag voor dag."""

    def __init__(self, firm, consistency=None):
        self.firm = firm
        self.consistency = firm.get("consistency") if consistency is None else consistency
        self.start = firm["start_balance"]
        self.balance = self.start
        self.highest_eod = self.start
        self.floor = self.start - firm["max_loss"]
        self.day_pnls = []
        self.paused_dates = []
        self.status = "RUNNING"
        self.reason = ""
        self.end_date = None

    @property
    def total_profit(self):
        return self.balance - self.start

    @property
    def best_day(self):
        return max(self.day_pnls) if self.day_pnls else 0.0

    @property
    def effective_target(self):
        """Winstdoel, verhoogd naar beste dag ÷ percentage als de consistency-regel dat eist."""
        target = self.firm["profit_target"]
        if self.consistency and self.best_day > 0:
            target = max(target, self.best_day / self.consistency)
        return target

    @property
    def consistency_raised(self):
        return self.effective_target > self.firm["profit_target"]

    def _fail(self, date, reason):
        self.status = "FAIL"
        self.reason = reason
        self.end_date = date

    def process_day(self, date, trades):
        if self.status != "RUNNING":
            return self.status
        firm = self.firm
        day_start = self.balance
        running = day_start
        dll = firm.get("daily_loss_limit")
        pause = dll is not None and firm.get("dll_mode", "fail") == "pause"
        # DLL-niveau = slotsaldo vorige dag − DLL. Ligt het boven de bodem, dan raak je eerst de DLL.
        dll_level = day_start - dll if dll is not None else None
        dll_first = pause and dll_level > self.floor
        use_mae = firm.get("intraday_breach_uses_mae", True)
        for t in trades:
            net = t["net_pnl"]
            worst = min(net, 0.0)
            if use_mae and t.get("mae") is not None:
                worst = min(worst, t["mae"])
            low = running + worst
            if dll_first and low <= dll_level:
                # pause: positie gesloten op het DLL-niveau (plus kosten), rest van de dag geen trades
                running = dll_level - (t.get("kosten") or 0.0)
                self.paused_dates.append(date)
                if running <= self.floor:
                    self.balance = running
                    self._fail(date, "Bodem geraakt na DLL-sluiting (%.2f <= %.2f)" % (running, self.floor))
                    return self.status
                break
            # saldo + MAE <= bodem is FAIL (precies op de bodem ook)
            if low <= self.floor:
                self.balance = running + net
                self._fail(date, "Bodem geraakt (%.2f <= %.2f)" % (low, self.floor))
                return self.status
            if dll is not None and not pause and low <= dll_level:
                self.balance = running + net
                self._fail(date, "Daily loss limit geraakt (−%.2f)" % (day_start - low))
                return self.status
            running += net
        self.balance = running
        self.day_pnls.append(running - day_start)
        if firm.get("trail_type", "eod") == "eod":
            self.highest_eod = max(self.highest_eod, self.balance)
            self.floor = min(self.highest_eod - firm["max_loss"], firm.get("lock_level", self.start))
        self._check_target(date)
        return self.status

    def _check_target(self, date):
        if self.total_profit < self.effective_target:
            return
        if len(self.day_pnls) < self.firm.get("min_trading_days", 0):
            return
        self.status = "PASS"
        self.reason = "Winstdoel gehaald (%.2f)" % self.effective_target
        self.end_date = date


def simulate(firm, days, consistency=None):
    """days = [(datum, [trades]), ...]. Geeft de Tracker terug."""
    tr = Tracker(firm, consistency)
    for date, trades in days:
        tr.process_day(date, trades)
        if tr.status != "RUNNING":
            break
    return tr
