"""Nep-broker voor tests (en droogoefeningen). Doet alsof hij de ProjectX-API is; er gaat niets naar buiten.

- bars worden vooraf ingeladen; alleen afgeronde bars (t + 1 min <= nu) worden teruggegeven
- limietorders blijven open tot vul_order(); stop-orders tot raak_stop(); sluit_positie() sluit op de laatste koers
- opties om fouten na te bootsen: faal_bij_order, verbinding_weg, weiger_stop, weiger_instap
"""
import datetime as dt
import itertools

from .broker import KOOP, LIMIT, MARKET, ORDER_GEANNULEERD, ORDER_GEVULD, ORDER_OPEN, POS_LONG, POS_SHORT, STOP, VerbindingsFout
from .tijd import UTC


class OrderVerbodenFout(AssertionError):
    """Paper-modus mag nooit een order versturen."""


class NepBroker:
    def __init__(self, account_id=111, nu=None, faal_bij_order=False):
        self.account_id = account_id
        self.nu = nu
        self.faal_bij_order = faal_bij_order
        self.verbinding_weg = False
        self.weiger_stop = False
        self.weiger_instap = None     # bijv. "Max position exceeded" -> firmabeperking
        self.time_out_na_plaatsen = False
        self._bars = {}               # contract -> {t_utc: (o,h,l,c)}
        self.orders = {}              # id -> dict
        self.posities_ = {}           # contract -> {size, type, averagePrice}
        self.trades_ = []
        self._ids = itertools.count(1001)
        self.verzoeken = []           # log van alle aanroepen
        self.order_aanroepen = 0

    # ---------- testhulp ----------
    def zet_bars(self, contract_id, bars):
        """bars = {datetime (met tijdzone, begintijd): (o,h,l,c)}"""
        self._bars.setdefault(contract_id, {}).update({t.astimezone(UTC): v for t, v in bars.items()})

    def _check(self, naam):
        self.verzoeken.append(naam)
        if self.verbinding_weg:
            raise VerbindingsFout(naam)

    def _order_check(self, naam):
        self.order_aanroepen += 1
        if self.faal_bij_order:
            raise OrderVerbodenFout("Order-aanroep '%s' terwijl dat verboden is" % naam)
        self._check(naam)

    def laatste_koers(self, contract_id):
        bars = self._bars.get(contract_id, {})
        ks = [t for t in bars if self.nu is None or t <= self.nu.astimezone(UTC)]
        return bars[max(ks)][3] if ks else None

    def vul_order(self, order_id, prijs, size=None):
        o = self.orders[order_id]
        n = size or o["size"]
        o["fillVolume"] = n
        o["filledPrice"] = prijs
        o["status"] = ORDER_GEVULD if n == o["size"] else ORDER_OPEN
        self._boek(o["contractId"], o["side"], n, prijs, order_id)

    def raak_stop(self, prijs=None):
        for o in self.orders.values():
            if o["type"] == STOP and o["status"] == ORDER_OPEN:
                p = prijs if prijs is not None else o["stopPrice"]
                o["status"] = ORDER_GEVULD
                o["filledPrice"] = p
                self._boek(o["contractId"], o["side"], o["size"], p, o["id"])
                return True
        return False

    def _boek(self, contract, side, n, prijs, order_id):
        teken = 1 if side == KOOP else -1
        p = self.posities_.get(contract)
        huidig = 0 if p is None else (p["size"] if p["type"] == POS_LONG else -p["size"])
        nieuw = huidig + teken * n
        if nieuw == 0:
            self.posities_.pop(contract, None)
        else:
            avg = prijs if huidig == 0 else p["averagePrice"]
            self.posities_[contract] = {"contractId": contract, "size": abs(nieuw),
                                        "type": POS_LONG if nieuw > 0 else POS_SHORT, "averagePrice": avg}
        self.trades_.append({"id": len(self.trades_) + 1, "contractId": contract, "price": prijs, "side": side,
                             "size": n, "orderId": order_id, "creationTimestamp": (self.nu or dt.datetime.now(UTC)).isoformat()})

    # ---------- API ----------
    def login(self):
        self._check("login")

    def houd_sessie_vast(self):
        pass

    def accounts(self):
        self._check("accounts")
        return [{"id": self.account_id, "name": "PRACTICE", "balance": 150000, "canTrade": True, "simulated": True}]

    def contract_id(self, jaar, maand, **kw):
        from .kalender_zn import MAAND_CODES
        return "CON.F.US.TYA.%s%02d" % (MAAND_CODES[maand], jaar % 100)

    def bars(self, contract_id, start, eind, partieel=False, live=False, limiet=200):
        self._check("bars")
        s, e = start.astimezone(UTC), eind.astimezone(UTC)
        nu = self.nu.astimezone(UTC) if self.nu else None
        out = []
        for t, (o, h, l, c) in sorted(self._bars.get(contract_id, {}).items()):
            if not (s <= t < e):
                continue
            if nu is not None and not partieel and t + dt.timedelta(minutes=1) > nu:
                continue
            if nu is not None and t > nu:
                continue
            out.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": 1})
        return out

    def plaats_order(self, account_id, contract_id, type_, side, size, limiet=None, stop=None, tag=None):
        self._order_check("plaats_order")
        if tag and any(o.get("customTag") == tag for o in self.orders.values()):
            return {"success": False, "errorCode": 2, "errorMessage": "Duplicate customTag"}
        if type_ == STOP and self.weiger_stop:
            return {"success": False, "errorCode": 2, "errorMessage": "Stop rejected"}
        if type_ == LIMIT and self.weiger_instap:
            return {"success": False, "errorCode": 2, "errorMessage": self.weiger_instap}
        oid = next(self._ids)
        self.orders[oid] = {"id": oid, "accountId": account_id, "contractId": contract_id, "type": type_, "side": side,
                            "size": size, "limitPrice": limiet, "stopPrice": stop, "customTag": tag,
                            "status": ORDER_OPEN, "fillVolume": 0, "filledPrice": None}
        if type_ == MARKET:
            self.vul_order(oid, self.laatste_koers(contract_id))
        if self.time_out_na_plaatsen:
            self.time_out_na_plaatsen = False
            raise VerbindingsFout("time-out na plaatsen")
        return {"success": True, "orderId": oid, "errorCode": 0, "errorMessage": None}

    def annuleer(self, account_id, order_id):
        self._order_check("annuleer")
        o = self.orders.get(order_id)
        if o and o["status"] == ORDER_OPEN:
            o["status"] = ORDER_GEANNULEERD
            return {"success": True}
        return {"success": False, "errorCode": 1}

    def open_orders(self, account_id):
        self._check("open_orders")
        return [dict(o) for o in self.orders.values() if o["status"] == ORDER_OPEN]

    def orders_zoek(self, account_id, start):
        self._check("orders")
        return [dict(o) for o in self.orders.values()]


    def posities(self, account_id):
        self._check("posities")
        return [dict(p) for p in self.posities_.values()]

    def sluit_positie(self, account_id, contract_id):
        self._order_check("sluit_positie")
        p = self.posities_.get(contract_id)
        if not p:
            return {"success": False, "errorCode": 1}
        side = 1 if p["type"] == POS_LONG else 0
        self._boek(contract_id, side, p["size"], self.laatste_koers(contract_id), None)
        return {"success": True}

    def trades(self, account_id, start):
        self._check("trades")
        return list(self.trades_)
