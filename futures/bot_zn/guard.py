"""Guard: controleert ELKE order vóór verzending (plan §7). Bij een overtreding: weigeren en loggen.

Een order is een dict:
  soort       'instap' | 'stop' | 'sluit'
  type        1 limiet, 2 market, 4 stop (broker.LIMIT/MARKET/STOP)
  side        0 kopen, 1 verkopen
  size        aantal contracten
  symbool     moet 'ZN' zijn
  account_id  moet het account uit de config zijn (en niet dat van de MES- of MGC-bot)
  tijd_et     datetime in ET
Toestand (dict): positie (getekend aantal: +2 long, -1 short), open_instap_orders, dag_redenen (lijst),
  no_go (bool), dag_gestopt (bool), modus ('paper'/'sim').
"""
from .broker import KOOP, LIMIT, STOP, VERKOOP
from .instellingen import BOT


class Guard:
    def __init__(self, strat, cfg, andere_ids, logboek=None, bot_map=BOT):
        self.strat = strat
        self.cfg = cfg
        self.andere_ids = {str(x) for x in andere_ids}
        self.log = logboek
        self.bot_map = bot_map
        t = strat["tijden_et"]
        self.instap_start, self.instap_eind = t["instap_start"], t["instap_eind"]
        self.firma_flat = t["firma_flat"]
        self.weigeringen = []

    def _weiger(self, order, reden):
        self.weigeringen.append((order, reden))
        if self.log:
            self.log.waarschuwing("GUARD WEIGERT %s-order (%s): %s" % (order.get("soort"), _kort(order), reden))
        return False, reden

    def kill_switch_actief(self):
        return (self.bot_map / "STOP").exists()

    def controleer(self, order, toestand):
        soort = order.get("soort")
        tijd = order["tijd_et"].strftime("%H:%M:%S")
        if toestand.get("modus") != "sim":
            return self._weiger(order, "modus %s verstuurt nooit orders" % toestand.get("modus"))
        acc = str(order.get("account_id"))
        if acc != str(self.cfg.get("account_id")):
            return self._weiger(order, "account %s staat niet op de whitelist" % acc)
        if acc in self.andere_ids:
            return self._weiger(order, "account %s is van de MES- of MGC-bot" % acc)
        size = int(order.get("size") or 0)
        pos = int(toestand.get("positie") or 0)
        if soort in ("instap", "stop"):
            if order.get("symbool") != self.strat["instrument"]["symbool"]:
                return self._weiger(order, "symbool %s is niet ZN" % order.get("symbool"))
            if size < 1 or size > self.strat["max_contracten"]:
                return self._weiger(order, "%d contracten (toegestaan 1–%d)" % (size, self.strat["max_contracten"]))

        if soort == "instap":
            if self.kill_switch_actief():
                return self._weiger(order, "kill switch (bestand STOP) actief")
            if toestand.get("no_go"):
                return self._weiger(order, "status NO-GO: geen orders meer")
            if toestand.get("dag_gestopt"):
                return self._weiger(order, "bot is voor vandaag gestopt")
            if order.get("type") != LIMIT:
                return self._weiger(order, "instap moet een limietorder zijn")
            if not (self.instap_start <= tijd <= self.instap_eind):
                return self._weiger(order, "instap om %s ET valt buiten %s–%s" % (tijd, self.instap_start, self.instap_eind))
            if toestand.get("dag_redenen"):
                return self._weiger(order, "geen handeldag: %s" % "+".join(toestand["dag_redenen"]))
            if pos != 0:
                return self._weiger(order, "er is al een open positie (max 1)")
            if toestand.get("open_instap_orders", 0) > 0:
                return self._weiger(order, "er staat al een instaporder open")
            if toestand.get("trades_vandaag", 0) >= self.strat["max_trades_per_dag"]:
                return self._weiger(order, "maximaal %d trade per dag" % self.strat["max_trades_per_dag"])
            return True, ""

        if soort == "stop":
            if order.get("type") != STOP:
                return self._weiger(order, "beschermende order moet een stop-order zijn")
            if pos == 0:
                return self._weiger(order, "stop zonder open positie")
            if order.get("side") != (VERKOOP if pos > 0 else KOOP):
                return self._weiger(order, "stop staat aan de verkeerde kant")
            if size != abs(pos):
                return self._weiger(order, "stop voor %d contracten, positie is %d" % (size, abs(pos)))
            return True, ""

        if soort == "sluit":
            # sluiten verkleint risico: mag altijd (ook na 16:10, ook een onbekende positie), maar alleen wat er is
            if size < 1 or pos == 0:
                return self._weiger(order, "niets te sluiten")
            if size > abs(pos):
                return self._weiger(order, "sluiten van %d contracten, positie is %d" % (size, abs(pos)))
            return True, ""

        return self._weiger(order, "onbekende soort order '%s'" % soort)


def _kort(o):
    return "%s %s x%s %s" % (o.get("symbool"), {0: "koop", 1: "verkoop"}.get(o.get("side"), "?"), o.get("size"),
                             {1: "limiet", 2: "market", 4: "stop"}.get(o.get("type"), o.get("type")))
