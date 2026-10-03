"""ProjectX Gateway API (TopstepX). Alleen REST, maximaal 1 verzoek per seconde (rate-limits worden gedeeld met de MES-bot).

Bronnen: https://gateway.docs.projectx.com en https://api.topstepx.com/swagger/v1/swagger.json (gecontroleerd 3 okt 2026).
De key komt uit .env (PROJECTX_USERNAME, PROJECTX_API_KEY) en wordt nooit gelogd.
"""
import datetime as dt
import json
import socket
import threading
import time
import urllib.error
import urllib.request

from .kalender_zn import MAAND_CODES
from .tijd import UTC

# enums uit de Swagger-spec
LIMIT, MARKET, STOP = 1, 2, 4
KOOP, VERKOOP = 0, 1            # OrderSide: 0 = Bid (kopen), 1 = Ask (verkopen)
POS_LONG, POS_SHORT = 1, 2      # PositionType
ORDER_OPEN, ORDER_GEVULD, ORDER_GEANNULEERD = 1, 2, 3
MINUUT = 2                      # AggregateBarUnit


class VerbindingsFout(Exception):
    """Netwerkfout of time-out: de status van een order is onbekend en moet eerst worden opgevraagd."""


class ApiFout(Exception):
    pass


class RateLimiter:
    def __init__(self, min_interval=1.0, klok=time.monotonic, slaap=time.sleep):
        self.min_interval = min_interval
        self.klok, self.slaap = klok, slaap
        self.laatste = None
        self.lock = threading.Lock()

    def wacht(self):
        with self.lock:
            nu = self.klok()
            if self.laatste is not None and nu - self.laatste < self.min_interval:
                self.slaap(self.min_interval - (nu - self.laatste))
                nu = self.klok()
            self.laatste = nu


class ProjectXClient:
    def __init__(self, gebruiker, api_key, basis="https://api.topstepx.com", per_seconde=1, timeout=15, log=None):
        self.gebruiker = gebruiker
        self._key = api_key
        self.basis = basis.rstrip("/")
        self.timeout = timeout
        self.limiter = RateLimiter(1.0 / max(per_seconde, 0.01))
        self.token = None
        self.token_tijd = None
        self.log = log
        self._symbol_id = None

    # ---------- transport ----------
    def _post(self, pad, body, auth=True, pogingen=3):
        data = json.dumps(body).encode()
        for poging in range(pogingen):
            self.limiter.wacht()
            req = urllib.request.Request(self.basis + pad, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("accept", "text/plain")
            if auth:
                req.add_header("Authorization", "Bearer " + (self.token or ""))
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode() or "{}")
            except urllib.error.HTTPError as e:
                if e.code == 429 and poging < pogingen - 1:
                    time.sleep(5 * (poging + 1))
                    continue
                if e.code == 401 and auth and poging < pogingen - 1:
                    self.login()
                    continue
                raise ApiFout("HTTP %s op %s" % (e.code, pad)) from None
            except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as e:
                raise VerbindingsFout("%s: %s" % (pad, type(e).__name__)) from None
        raise ApiFout("geen antwoord op %s" % pad)

    def _ok(self, r, pad):
        if not r.get("success", False):
            raise ApiFout("%s mislukt: code %s %s" % (pad, r.get("errorCode"), r.get("errorMessage") or ""))
        return r

    # ---------- sessie ----------
    def login(self):
        r = self._post("/api/Auth/loginKey", {"userName": self.gebruiker, "apiKey": self._key}, auth=False)
        if not r.get("success") or not r.get("token"):
            raise ApiFout("Inloggen mislukt (code %s). Controleer PROJECTX_USERNAME en PROJECTX_API_KEY in .env"
                          % r.get("errorCode"))
        self.token, self.token_tijd = r["token"], time.time()

    def houd_sessie_vast(self):
        """Tokens zijn 24 uur geldig: na 12 uur vernieuwen."""
        if self.token is None:
            self.login()
        elif time.time() - self.token_tijd > 12 * 3600:
            r = self._post("/api/Auth/validate", {})
            if r.get("success") and r.get("newToken"):
                self.token, self.token_tijd = r["newToken"], time.time()
            else:
                self.login()

    # ---------- account / contract ----------
    def accounts(self):
        return self._ok(self._post("/api/Account/search", {"onlyActiveAccounts": True}), "Account/search").get("accounts", [])

    def zoek_contracten(self, tekst, live=False):
        return self._ok(self._post("/api/Contract/search", {"searchText": tekst, "live": live}), "Contract/search").get("contracts", [])

    def contract_id(self, jaar, maand, zoekterm="ZN", live=False, symbol_id=None):
        """Bouwt het ID, bijv. CON.F.US.TYA.Z26. Het symbolId (bijv. F.US.TYA) wordt eenmalig opgezocht."""
        if symbol_id:
            self._symbol_id = symbol_id
        if not self._symbol_id:
            kandidaten = [c for c in self.zoek_contracten(zoekterm, live)
                          if "10" in (c.get("description") or "") and ("Year" in (c.get("description") or "") or "T-Note" in (c.get("description") or ""))]
            if not kandidaten:
                raise ApiFout("Geen 10-Year T-Note gevonden bij Contract/search '%s'" % zoekterm)
            self._symbol_id = kandidaten[0]["symbolId"]
        return "CON.%s.%s%02d" % (self._symbol_id, MAAND_CODES[maand], jaar % 100)

    # ---------- data ----------
    def bars(self, contract_id, start, eind, partieel=False, live=False, limiet=200):
        """1-minuutbars [start, eind) (datetimes met tijdzone). -> [{'t': datetime UTC, 'o','h','l','c','v'}] oud -> nieuw."""
        body = {"contractId": contract_id, "live": live,
                "startTime": start.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endTime": eind.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "unit": MINUUT, "unitNumber": 1, "limit": limiet, "includePartialBar": partieel}
        r = self._ok(self._post("/api/History/retrieveBars", body), "History/retrieveBars")
        out = []
        for b in r.get("bars", []) or []:
            t = dt.datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(UTC)
            out.append({"t": t, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b.get("v", 0)})
        out.sort(key=lambda x: x["t"])
        return out

    # ---------- orders / posities ----------
    def plaats_order(self, account_id, contract_id, type_, side, size, limiet=None, stop=None, tag=None):
        body = {"accountId": int(account_id), "contractId": contract_id, "type": type_, "side": side, "size": int(size)}
        if limiet is not None:
            body["limitPrice"] = limiet
        if stop is not None:
            body["stopPrice"] = stop
        if tag:
            body["customTag"] = tag
        return self._post("/api/Order/place", body)

    def annuleer(self, account_id, order_id):
        return self._post("/api/Order/cancel", {"accountId": int(account_id), "orderId": int(order_id)})

    def open_orders(self, account_id):
        return self._ok(self._post("/api/Order/searchOpen", {"accountId": int(account_id)}), "Order/searchOpen").get("orders", [])

    def orders_zoek(self, account_id, start):
        return self._ok(self._post("/api/Order/search", {"accountId": int(account_id),
                                                         "startTimestamp": start.astimezone(UTC).isoformat()}),
                        "Order/search").get("orders", [])

    def posities(self, account_id):
        return self._ok(self._post("/api/Position/searchOpen", {"accountId": int(account_id)}), "Position/searchOpen").get("positions", [])

    def sluit_positie(self, account_id, contract_id):
        return self._post("/api/Position/closeContract", {"accountId": int(account_id), "contractId": contract_id})

    def trades(self, account_id, start):
        return self._ok(self._post("/api/Trade/search", {"accountId": int(account_id),
                                                         "startTimestamp": start.astimezone(UTC).isoformat()}),
                        "Trade/search").get("trades", [])
