"""Fase B (paper) en C (sim): de bot die tijdens de handelsdag draait.

Gebruik: python -m bot_zn.live            (modus uit bot_zn/config.json, standaard paper)
         python -m bot_zn.live --modus sim (vraagt om het account-ID ter bevestiging)

- paper: haalt live 1-minuutbars op en simuleert de fills met DEZELFDE code als de backtest. Verstuurt nooit een order.
- sim:   orders naar het practice-account via de ProjectX-API. Elke order gaat eerst langs guard.py.
Alle tijden in ET (America/New_York); de Amsterdamse tijd staat erbij in de log.
"""
import argparse
import csv
import datetime as dt
import sys
import time
import uuid
from pathlib import Path

from . import bewaking
from .account import account_uit_trades
from .broker import KOOP, LIMIT, POS_LONG, STOP, VERKOOP, ApiFout, VerbindingsFout
from .fills import GESLOTEN, NIET_GEVULD, OPEN, WACHT, TradeSim
from .guard import Guard
from .journal_zn import live_trades, voeg_live_trade_toe
from .kalender_zn import contract_code
from .logboek import lees_signalen
from .strategie import WEEKSTOP, beslis, contracten, dag_uit_prijzen, signaalprijs, slotprijs
from .tijd import ET, NL, TICK, et, hms, in_32ste

FIRMA_BEPERKING = "firma_beperking"


def op_tick(prijs):
    return round(round(prijs / TICK) * TICK, 6)


def bars_naar_dict(bars):
    return {b["t"].astimezone(ET).strftime("%H:%M"): (b["o"], b["h"], b["l"], b["c"]) for b in bars}


class ZNRunner:
    def __init__(self, broker, strat, cfg, kal, firm, logboek, bot_map, andere_ids=()):
        self.broker = broker
        self.strat = strat
        self.cfg = cfg
        self.kal = kal
        self.firm = firm
        self.log = logboek
        self.map = Path(bot_map)
        self.modus = cfg["modus"]
        self.account_id = cfg.get("account_id")
        self.andere_ids = {str(x) for x in andere_ids}
        self.guard = Guard(strat, cfg, self.andere_ids, logboek, self.map)
        self.status_pad = self.map / "status.json"
        self.journal_pad = self.map / "journal_bot.csv"
        self.cache_pad = self.map / "data" / "live_dagen.csv"
        self.signalen_map = self.map / "logs"
        self.data_live = bool(cfg.get("data_live", False))
        self.poll = strat["live"]["poll_seconden"]
        self.t = strat["tijden_et"]
        self.gestopt = False
        self.stopreden = ""
        self.dag = None
        self.verbinding_verloren = False
        self.cache = self._lees_cache()
        self._cache_gewijzigd = False

    # ================= hulp =================
    @property
    def eff_modus(self):
        """NO-GO in sim -> alleen nog loggen in paper."""
        if self.modus == "sim" and bewaking.is_no_go(self.status_pad):
            return "paper"
        return self.modus

    @property
    def account(self):
        return "zn-sim" if self.eff_modus == "sim" else "zn-paper"

    def _lees_cache(self):
        c = {}
        if self.cache_pad.exists():
            with open(self.cache_pad, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    c[(r["datum"], r["contract"])] = (float(r["signaal"]) if r["signaal"] else None,
                                                      float(r["slot"]) if r["slot"] else None)
        return c

    def _schrijf_cache(self):
        if not self._cache_gewijzigd:
            return
        self.cache_pad.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_pad, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["datum", "contract", "signaal", "slot"])
            for (d, c), (sp, sl) in sorted(self.cache.items()):
                w.writerow([d, c, "" if sp is None else sp, "" if sl is None else sl])
        self._cache_gewijzigd = False

    def _cid(self, jm):
        return self.broker.contract_id(jm[0], jm[1], zoekterm=self.cfg.get("contract_zoekterm", "ZN"),
                                       live=self.data_live, symbol_id=self.cfg.get("contract_symbol_id"))

    def _prijzen(self, datum, jm):
        """(signaalprijs, slotprijs) van een eerdere dag op contract jm; uit de cache of via de API."""
        sleutel = (datum.isoformat(), contract_code(*jm))
        if sleutel not in self.cache:
            bars = bars_naar_dict(self.broker.bars(self._cid(jm), et(datum, "14:00"), et(datum, "15:01"), live=self.data_live))
            self.cache[sleutel] = (signaalprijs(bars, self.strat), slotprijs(bars, self.strat))
            self._cache_gewijzigd = True
        return self.cache[sleutel]

    def laad_historie(self, vandaag):
        """Geldige dagen van de laatste ~140 kalenderdagen, elk op het contract dat de bot die dag handelde."""
        start = vandaag - dt.timedelta(days=self.strat["live"]["historie_kalenderdagen"])
        d, out = start, []
        while d < vandaag:
            if self.kal.is_handelsdag(d):
                jm = self.kal.contract_voor(d)
                sp, sl = self._prijzen(d, jm)
                vsl = self._prijzen(self.kal.vorige_handelsdag(d), jm)[1]
                dag = dag_uit_prijzen(d, contract_code(*jm), sp, sl, vsl, self.kal, self.strat)
                if dag.geldig:
                    out.append(dag)
            d += dt.timedelta(days=1)
        self._schrijf_cache()
        return out

    def _toestand(self):
        return {"modus": self.eff_modus, "positie": self.positie, "dag_redenen": self.redenen,
                "open_instap_orders": 1 if (self.fase == "instap_open" and self.order_id) else 0,
                "no_go": bewaking.is_no_go(self.status_pad), "dag_gestopt": self.dag_gestopt,
                "trades_vandaag": self.trades_vandaag}

    def _order(self, soort, type_, side, size, now, symbool="ZN"):
        return {"soort": soort, "type": type_, "side": side, "size": size, "symbool": symbool,
                "account_id": self.account_id, "tijd_et": now}

    def _mag_pollen(self, now):
        if self.laatste_poll is None or (now - self.laatste_poll).total_seconds() >= self.poll:
            self.laatste_poll = now
            return True
        return False

    def _virtueel(self):
        return account_uit_trades(self.firm, [(d, n, m) for d, n, m, _ in live_trades(self.account, self.journal_pad)])

    def _week_pnl(self, d):
        wk = d.isocalendar()[:2]
        return sum(n for dd, n, _, _ in live_trades(self.account, self.journal_pad) if dd.isocalendar()[:2] == wk and dd <= d)

    # ================= start / stop =================
    def start(self):
        if (self.map / "STOP").exists():
            self.log.alarm("Het bestand STOP staat in bot_zn. Verwijder het om de bot te starten.")
            self.gestopt = True
            return False
        if self.modus == "sim":
            ids = [str(a.get("id")) for a in self.broker.accounts()]
            if str(self.account_id) not in ids:
                return self._stop_bot("Account %s niet gevonden bij de broker" % self.account_id)
            if str(self.account_id) in self.andere_ids:
                return self._stop_bot("Account %s is van de MES- of MGC-bot" % self.account_id)
            pos = self.broker.posities(self.account_id)
            oo = self.broker.open_orders(self.account_id)
            if pos or oo:
                return self._stop_bot("OPSTARTCHECK: onbekende positie of order op het account (%d posities, %d orders). "
                                      "De bot doet niets." % (len(pos), len(oo)))
        self.log.info("Bot gestart in modus %s (account %s)%s" % (
            self.modus, self.account_id or "–", "; status NO-GO: alleen loggen in paper" if bewaking.is_no_go(self.status_pad) else ""))
        return True

    def _stop_bot(self, reden):
        self.log.alarm(reden)
        self.gestopt = True
        self.stopreden = reden
        return False

    def kill(self, reden="kill switch"):
        self.log.alarm("KILL SWITCH: %s. Alles sluiten en stoppen." % reden)
        if self.modus == "sim":
            try:
                self._sluit_alles("kill switch", stop_dag=True)
            except (VerbindingsFout, ApiFout) as e:
                self.log.alarm("Sluiten na kill switch mislukt (%s). Controleer het account handmatig!" % e)
        if self.dag is not None and getattr(self, "papier", None) is not None and self.papier.status == OPEN:
            self.papier.einde_data(self._laatste_prijs_papier)
            self._afronden_papier()
        self.gestopt = True
        self.stopreden = reden

    # ================= dag =================
    def nieuwe_dag(self, d):
        self.dag = d
        self.fase = "wachten"
        self.redenen = self.kal.redenen_geen_trade(d)
        self.jm = self.kal.contract_voor(d)
        self.cid = None
        self.historie = None
        self.beslissing = None
        self.papier = None
        self._laatste_prijs_papier = None
        self.gevoerd_tot = ""
        self.order_id = None
        self.order_tag = None
        self.stop_order_id = None
        self.positie = 0
        self.instap = None
        self.instap_tijd = None
        self.stop_prijs = None
        self.slechtste = self.beste = None
        self.dag_gestopt = False
        self.trades_vandaag = 0
        self.herplaatsingen = 0
        self.controle_1505 = False
        self.afgerond = False
        self.laatste_poll = None
        self.rij = {}

    def _stop_dag(self, reden):
        self.dag_gestopt = True
        self.log.waarschuwing("Rest van de dag gestopt: %s" % reden)

    def tick(self, now):
        """Wordt elke seconde aangeroepen met de huidige tijd in ET."""
        if self.gestopt:
            return
        if (self.map / "STOP").exists():
            self.kill("bestand STOP gevonden")
            return
        d = now.date()
        if d != self.dag:
            self.nieuwe_dag(d)
        t = hms(now)
        try:
            if self.verbinding_verloren:
                self.herstel(now)
                if self.verbinding_verloren:
                    return
            self._dagverloop(now, t)
        except VerbindingsFout as e:
            if not self.verbinding_verloren:
                self.log.waarschuwing("Verbinding verbroken (%s). Bij herstel eerst vergelijken met de server." % e)
            self.verbinding_verloren = True
        except ApiFout as e:
            self.log.waarschuwing("API-fout: %s" % e)

    def _dagverloop(self, now, t):
        if self.afgerond:
            return
        if t < self.t["voorbereiden"]:
            return
        if self.historie is None:
            self._voorbereiden(now)
        if self.fase == "wachten":
            if t >= self.t["instap_start"] and t <= self.t["instap_eind"]:
                self.beslis_nu(now)
            elif t > self.t["instap_eind"]:
                self.log.waarschuwing("Te laat gestart: na %s ET wordt niet meer ingestapt." % self.t["instap_eind"])
                self._signaal_log(status="te_laat", reden="na 14:34:59 gestart")
                self.fase = "klaar"
        if self.fase in ("instap_open", "positie", "instap_onbekend"):
            if self.eff_modus == "paper" or self.papier is not None:
                self._paper_stap(now, t)
            else:
                self._sim_stap(now, t)
        if t >= self.t["controle_flat"] and not self.controle_1505:
            self._controle_flat(now)
        if self.fase == "klaar" and (t >= self.t["controle_flat"] or self.modus == "paper" or self.eff_modus == "paper"):
            self.afgerond = True

    def _voorbereiden(self, now):
        d = self.dag
        nl = et(d, self.t["instap_start"]).astimezone(NL).strftime("%H:%M")
        if self.redenen:
            self.log.info("%s: geen handeldag voor ZN (%s)." % (d, "+".join(self.redenen)))
            self.historie = []
            if self.kal.is_handelsdag(d):
                self._signaal_log(status="geen", reden="+".join(self.redenen))
            self.fase = "klaar"
            self.afgerond = True
            return
        self.cid = self._cid(self.jm)
        self.log.info("%s: handeldag. Contract %s (%s). Beslissing om 14:30 ET = %s Amsterdam. Historie laden ..."
                      % (d, contract_code(*self.jm), self.cid, nl))
        self.historie = self.laad_historie(d)
        self.log.info("%d geldige dagen historie geladen." % len(self.historie))

    # ================= beslissing 14:30 =================
    def beslis_nu(self, now):
        d = self.dag
        bars = bars_naar_dict(self.broker.bars(self.cid, et(d, "14:00"), et(d, "14:30"), live=self.data_live))
        sp = signaalprijs(bars, self.strat)
        vsl = self._prijzen(self.kal.vorige_handelsdag(d), self.jm)[1]
        self._schrijf_cache()
        dag = dag_uit_prijzen(d, contract_code(*self.jm), sp, None, vsl, self.kal, self.strat)
        b = beslis(dag, self.historie, self.strat, "A")
        self.beslissing = b
        self.rij = {"rod": None if b.rod is None else "%.6f" % b.rod, "mediaan": None if b.mediaan is None else "%.6f" % b.mediaan,
                    "signaal": sp, "richting": b.richting, "limiet": b.limiet, "stop_ticks": b.stop_ticks,
                    "filter": "" if b.mediaan is None else ("sterk" if b.is_trade else "zwak")}
        self.log.info("14:30 ET: signaalprijs %s, ROD %s, mediaan %s -> %s" % (
            in_32ste(sp), "–" if b.rod is None else "%+.4f%%" % (100 * b.rod),
            "–" if b.mediaan is None else "%.4f%%" % (100 * b.mediaan), b.reden or ("LONG" if b.richting > 0 else "SHORT")))
        if not b.is_trade:
            self._signaal_log(status="geen", reden=b.reden)
            self.fase = "klaar"
            return
        if self._week_pnl(d) <= -self.strat["weekstop_usd"]:
            self._signaal_log(status="geen", reden=WEEKSTOP)
            self.log.info("Weekstop: week-P&L <= -$%d, rest van de week niet traden." % self.strat["weekstop_usd"])
            self.fase = "klaar"
            return
        acc = self._virtueel()
        n, reden = contracten(b.stop_ticks, self.strat, acc.afstand_tot_bodem())
        b.contracten = n
        self.rij["contracten"] = n
        if n == 0:
            if reden == "gehalveerd_naar_0":
                self.log.waarschuwing("Virtueel account $%.0f boven de bodem: halveren geeft 0 contracten. Zonder besluit "
                                      "(account opnieuw beginnen) kan de bot niet meer traden." % acc.afstand_tot_bodem())
            self._signaal_log(status="geen", reden=reden)
            self.fase = "klaar"
            return
        stop_t = b.stop_ticks
        self.log.info("SIGNAAL %s %d ZN, limiet %s, stop %d ticks" % ("LONG" if b.richting > 0 else "SHORT", n, in_32ste(b.limiet), stop_t))
        if self.eff_modus == "paper":
            self.papier = TradeSim(b.richting, b.limiet, stop_t, n, self.strat)
            self.fase = "instap_open"
            self.log.info("PAPER: limietorder gesimuleerd (geen order verstuurd).")
        else:
            self._plaats_instap(now)

    # ================= paper =================
    def _paper_stap(self, now, t):
        if not self._mag_pollen(now):
            return
        sim = self.papier
        bars = bars_naar_dict(self.broker.bars(self.cid, et(self.dag, "14:30"), et(self.dag, "15:01"), live=self.data_live))
        for m in sorted(k for k in bars if k > self.gevoerd_tot):
            o, h, l, c = bars[m]
            sim.bar(m, o, h, l, c)
            self.gevoerd_tot = m
            if m <= self.t["laatste_stop_bar"]:
                self._laatste_prijs_papier = c
            if sim.status == OPEN:
                self._noodrem_papier(c)
            if sim.status in (GESLOTEN, NIET_GEVULD):
                break
        if sim.status == WACHT and (self.gevoerd_tot >= self.t["instap_eind"][:5] or t >= "14:36:00"):
            sim.einde_instapvenster()
        if sim.status == OPEN and t >= self.t["controle_flat"]:
            self.log.alarm("Geen 14:59-bar ontvangen: paper-positie gesloten op de laatste koers.")
            sim.einde_data(self._laatste_prijs_papier)
        if sim.status == NIET_GEVULD:
            self.log.info("PAPER: limiet niet gevuld vóór 14:35 ET -> order geannuleerd, geen trade (niet_gevuld).")
            self._signaal_log(status="niet_gevuld")
            self.fase = "klaar"
        elif sim.status == GESLOTEN:
            self._afronden_papier()

    def _noodrem_papier(self, prijs):
        sim = self.papier
        pv = self.strat["instrument"]["punt_waarde"]
        open_pnl = (prijs - sim.instap) * sim.richting * pv * sim.contracten
        acc = self._virtueel()
        if open_pnl <= -self.strat["noodrem_dag_usd"] or acc.saldo + open_pnl <= acc.bodem + self.strat["noodrem_bodem_buffer_usd"]:
            self.log.alarm("NOODREM (paper): open P&L $%.0f. Positie gesloten." % open_pnl)
            sim._sluit(self.gevoerd_tot, prijs - sim.richting * sim.slip, "noodrem")

    def _afronden_papier(self):
        sim = self.papier
        res = sim.resultaat(self.strat["kosten_per_contract_rt"])
        b = self.beslissing
        trade = dict(res, datum=self.dag, variant="A", richting=sim.richting, instap=sim.instap, uitstap=sim.uitstap,
                     stop=sim.stop, limiet=sim.limiet, stop_ticks=sim.stop_ticks, contracten=sim.contracten,
                     instap_bar=sim.instap_bar, uitstap_bar="14:59" if sim.uitstapreden == "tijd" else sim.uitstap_bar_tijd,
                     uitstapreden=sim.uitstapreden, rod=b.rod, mediaan=b.mediaan, veiling=self.kal.is_veilingdag(self.dag),
                     notitie="paper (gesimuleerde fills)")
        self._boek_trade(trade, slippage=0.0)
        self.fase = "klaar"

    # ================= sim: orders =================
    def _plaats_instap(self, now):
        b = self.beslissing
        side = KOOP if b.richting > 0 else VERKOOP
        ok, reden = self.guard.controleer(self._order("instap", LIMIT, side, b.contracten, now), self._toestand())
        if not ok:
            self._signaal_log(status="guard_weigering", reden=reden)
            self.fase = "klaar"
            return
        self.order_tag = "ZN-%s-%s" % (self.dag.strftime("%Y%m%d"), uuid.uuid4().hex[:10])
        self.fase = "instap_onbekend"   # tot de server antwoordt
        r = self.broker.plaats_order(self.account_id, self.cid, LIMIT, side, b.contracten, limiet=op_tick(b.limiet), tag=self.order_tag)
        if not r.get("success"):
            reden = "%s (code %s)" % (r.get("errorMessage") or "geweigerd", r.get("errorCode"))
            self.log.alarm("Server weigert de instaporder: %s. Niet opnieuw proberen." % reden)
            self._signaal_log(status=FIRMA_BEPERKING, reden=reden)
            self._stop_dag(FIRMA_BEPERKING)
            self.fase = "klaar"
            return
        self.order_id = r.get("orderId")
        self.fase = "instap_open"
        self.log.info("SIM: limietorder %s geplaatst (tag %s), geldig tot %s ET." % (self.order_id, self.order_tag, self.t["instap_eind"]))

    def _onze_positie(self, posities):
        mijn = [p for p in posities if p.get("contractId") == self.cid]
        vreemd = [p for p in posities if p.get("contractId") != self.cid]
        return (mijn[0] if mijn else None), vreemd

    def _getekend(self, p):
        return 0 if p is None else (p["size"] if p.get("type") == POS_LONG else -p["size"])

    def _sim_stap(self, now, t):
        if self.fase == "instap_onbekend":
            return  # wacht op herstel
        if not self._mag_pollen(now) and not (self.fase == "positie" and t >= self.t["uitstap"]) \
                and not (self.fase == "instap_open" and t > self.t["instap_eind"]):
            return
        pos, vreemd = self._onze_positie(self.broker.posities(self.account_id))
        if vreemd:
            self._onbekend("onbekende positie op %s" % ", ".join(p.get("contractId", "?") for p in vreemd))
            return
        if self.fase == "instap_open":
            if pos is not None:
                self._bij_fill(pos, now)
            elif t > self.t["instap_eind"]:
                self.broker.annuleer(self.account_id, self.order_id)
                pos, _ = self._onze_positie(self.broker.posities(self.account_id))
                if pos is not None:   # net op het laatste moment gevuld
                    self._bij_fill(pos, now)
                else:
                    self.log.info("SIM: niet gevuld vóór 14:35 ET -> order %s geannuleerd (niet_gevuld)." % self.order_id)
                    self._signaal_log(status="niet_gevuld")
                    self.order_id = None
                    self.fase = "klaar"
            return
        if self.fase == "positie":
            if pos is None:
                self._positie_weg(now)
                return
            if self._getekend(pos) != self.positie:
                self._onbekend("positie %+d op de server, verwacht %+d" % (self._getekend(pos), self.positie))
                return
            if t >= self.t["uitstap"]:
                self._uitstap_tijd(now)
                return
            self._bewaak_open(now)

    def _bij_fill(self, pos, now):
        b = self.beslissing
        # een eventueel nog openstaand restant van de instaporder annuleren (gedeeltelijke fill)
        for o in self.broker.open_orders(self.account_id):
            if o.get("id") == self.order_id:
                self.broker.annuleer(self.account_id, self.order_id)
        self.positie = self._getekend(pos)
        self.instap = float(pos["averagePrice"])
        self.instap_tijd = now.strftime("%H:%M")
        self.slechtste = self.beste = self.instap
        self.trades_vandaag += 1
        richting = 1 if self.positie > 0 else -1
        self.stop_prijs = op_tick(self.instap - richting * b.stop_ticks * TICK)
        self.log.info("SIM: gevuld %+d ZN op %s. Stop-order op %s plaatsen." % (self.positie, in_32ste(self.instap), in_32ste(self.stop_prijs)))
        side = VERKOOP if richting > 0 else KOOP
        ok, reden = self.guard.controleer(self._order("stop", STOP, side, abs(self.positie), now), self._toestand())
        r = None
        if ok:
            try:
                r = self.broker.plaats_order(self.account_id, self.cid, STOP, side, abs(self.positie), stop=self.stop_prijs,
                                             tag=self.order_tag + "-stop")
            except VerbindingsFout:
                r = None
        if not r or not r.get("success"):
            self.log.alarm("Stop-order kon niet worden geplaatst (%s). Positie direct sluiten, rest van de dag stoppen."
                           % (reden or (r or {}).get("errorMessage") or "geen antwoord"))
            self._sluit_alles("stop-order mislukt", stop_dag=True)
            self.fase = "klaar"
            return
        self.stop_order_id = r.get("orderId")
        self.fase = "positie"

    def _laatste_prijs(self, now):
        bars = self.broker.bars(self.cid, now - dt.timedelta(minutes=3), now + dt.timedelta(minutes=1), partieel=True, live=self.data_live)
        return bars[-1]["c"] if bars else None

    def _bewaak_open(self, now):
        p = self._laatste_prijs(now)
        if p is None:
            return
        richting = 1 if self.positie > 0 else -1
        self.slechtste = min(self.slechtste, p) if richting > 0 else max(self.slechtste, p)
        self.beste = max(self.beste, p) if richting > 0 else min(self.beste, p)
        open_pnl = (p - self.instap) * richting * self.strat["instrument"]["punt_waarde"] * abs(self.positie)
        acc = self._virtueel()
        if open_pnl <= -self.strat["noodrem_dag_usd"]:
            self.log.alarm("NOODREM DAG: dag-P&L incl. open $%.0f <= -$%d. Alles sluiten." % (open_pnl, self.strat["noodrem_dag_usd"]))
            self._sluit_en_boek(now, "noodrem_dag")
        elif acc.saldo + open_pnl <= acc.bodem + self.strat["noodrem_bodem_buffer_usd"]:
            self.log.alarm("NOODREM BODEM: saldo + open P&L $%.0f <= bodem + $%d." % (acc.saldo + open_pnl, self.strat["noodrem_bodem_buffer_usd"]))
            self._sluit_en_boek(now, "noodrem_bodem")

    def _uitstap_tijd(self, now):
        self.log.info("14:59:00 ET: tijdsuitstap.")
        self._sluit_en_boek(now, "tijd")

    def _sluit_en_boek(self, now, reden):
        aantal = abs(self.positie)
        self._sluit_alles(reden, stop_dag=(reden != "tijd"))
        self._boek_sim(now, reden, aantal)

    def _positie_weg(self, now):
        """Positie is weg terwijl we er een hadden: de stop is geraakt."""
        aantal = abs(self.positie)
        for o in self.broker.open_orders(self.account_id):
            self.broker.annuleer(self.account_id, o["id"])
        self.log.info("SIM: positie gesloten door de stop-order.")
        self.positie = 0
        self._boek_sim(now, "stop", aantal)

    def _uitstapprijs(self, now):
        start = et(self.dag, "14:00")
        trades = [x for x in self.broker.trades(self.account_id, start) if x.get("contractId") == self.cid]
        return float(trades[-1]["price"]) if trades and trades[-1].get("price") is not None else None

    def _boek_sim(self, now, reden, aantal):
        b = self.beslissing
        uit = self._uitstapprijs(now)
        if uit is None or self.instap is None:
            self.log.alarm("Uitstapprijs onbekend; trade niet in het journal. Controleer TopstepX.")
            self.fase = "klaar"
            return
        richting = b.richting
        pv, tw = self.strat["instrument"]["punt_waarde"], self.strat["instrument"]["tick_waarde"]
        bruto = (uit - self.instap) * richting * pv * aantal
        kosten = self.strat["kosten_per_contract_rt"] * aantal
        risico = b.stop_ticks * tw * aantal
        netto = bruto - kosten
        slechtste = min(self.slechtste, uit) if richting > 0 else max(self.slechtste, uit)
        # slippage t.o.v. de aanname (in ticks, positief = slechter): instap vs limiet, uitstap vs stop − 1 tick / koers 14:59 − 1 tick
        slip = (self.instap - b.limiet) * richting / TICK
        if reden == "stop":
            aanname = self.stop_prijs - richting * self.strat["fill"]["slippage_ticks"] * TICK
            slip += (aanname - uit) * richting / TICK
        elif reden == "tijd":
            o1459 = self._open_1459()
            if o1459 is not None:
                aanname = o1459 - richting * self.strat["fill"]["slippage_ticks"] * TICK
                slip += (aanname - uit) * richting / TICK
        trade = {"datum": self.dag, "variant": "A", "richting": richting, "instap": self.instap, "uitstap": uit,
                 "stop": self.stop_prijs, "limiet": b.limiet, "stop_ticks": b.stop_ticks, "contracten": aantal,
                 "instap_bar": self.instap_tijd, "uitstap_bar": now.strftime("%H:%M"), "uitstapreden": reden,
                 "rod": b.rod, "mediaan": b.mediaan, "veiling": self.kal.is_veilingdag(self.dag), "bruto": bruto,
                 "kosten": kosten, "netto": netto, "risico": risico, "R": netto / risico if risico else None,
                 "mae": min(0.0, (slechtste - self.instap) * richting * pv * aantal, netto),
                 "mfe": max(0.0, (self.beste - self.instap) * richting * pv * aantal),
                 "notitie": "sim; slippage %+.1f ticks" % slip}
        self._boek_trade(trade, slippage=slip)
        self.fase = "klaar"

    def _open_1459(self):
        bars = bars_naar_dict(self.broker.bars(self.cid, et(self.dag, "14:59"), et(self.dag, "15:00"), partieel=True, live=self.data_live))
        return bars["14:59"][0] if "14:59" in bars else None

    def _sluit_alles(self, reden, stop_dag=False):
        """Annuleert alle open orders en sluit alle posities op het account (alleen sim)."""
        now = dt.datetime.now(ET)
        for o in self.broker.open_orders(self.account_id):
            self.broker.annuleer(self.account_id, o["id"])
        for p in self.broker.posities(self.account_id):
            sym = "ZN" if p.get("contractId") == self.cid else p.get("contractId", "?")
            order = self._order("sluit", 2, VERKOOP if p.get("type") == POS_LONG else KOOP, p["size"], now, sym)
            ok, _ = self.guard.controleer(order, dict(self._toestand(), positie=self._getekend(p)))
            if ok:
                r = self.broker.sluit_positie(self.account_id, p["contractId"])
                self.log.info("Positie %s gesloten (%s): %s" % (p.get("contractId"), reden, "ok" if r.get("success") else r))
        self.positie = 0
        if stop_dag:
            self._stop_dag(reden)

    def _onbekend(self, wat):
        self.log.alarm("ONBEKEND: %s. Sluiten en stoppen voor vandaag." % wat)
        self._sluit_alles("onbekende positie/order", stop_dag=True)
        self.fase = "klaar"

    # ================= controles =================
    def _controle_flat(self, now):
        self.controle_1505 = True
        if self.eff_modus != "sim" or self.modus != "sim":
            return
        pos = self.broker.posities(self.account_id)
        oo = self.broker.open_orders(self.account_id)
        if pos or oo:
            self.log.alarm("15:05 ET CONTROLE: nog %d positie(s) en %d order(s) open. Nu sluiten!" % (len(pos), len(oo)))
            self._sluit_alles("controle 15:05", stop_dag=True)
            if self.fase != "klaar":
                self.fase = "klaar"

    def herstel(self, now):
        """Na een verbroken verbinding: eerst de server vragen wat er is, dan pas handelen. Nooit blind opnieuw versturen."""
        if self.modus != "sim" or self.eff_modus != "sim":
            self.verbinding_verloren = False
            self.log.info("Verbinding hersteld.")
            return
        try:
            posities = self.broker.posities(self.account_id)
            oo = self.broker.open_orders(self.account_id)
        except VerbindingsFout:
            return
        self.verbinding_verloren = False
        self.log.info("Verbinding hersteld: %d positie(s), %d open order(s) op de server." % (len(posities), len(oo)))
        if self.dag is None or not hasattr(self, "fase"):
            if posities:
                self._onbekend("positie na herstel zonder lopende trade")
            return
        pos, vreemd = self._onze_positie(posities)
        if vreemd:
            self._onbekend("onbekende positie op %s" % ", ".join(p.get("contractId", "?") for p in vreemd))
            return
        bekend = {self.order_id, self.stop_order_id} - {None}
        if self.fase == "instap_onbekend":
            gevonden = [o for o in self.broker.orders_zoek(self.account_id, et(self.dag, "14:00"))
                        if o.get("customTag") == self.order_tag]
            if gevonden:
                self.order_id = gevonden[0]["id"]
                bekend.add(self.order_id)
                self.fase = "instap_open"
                self.log.info("Instaporder %s gevonden op de server (tag %s); niet opnieuw versturen." % (self.order_id, self.order_tag))
            elif pos is not None:
                self.fase = "instap_open"
            else:
                self.log.info("Instaporder niet op de server gevonden.")
                if hms(now) <= self.t["instap_eind"] and self.herplaatsingen < 1:
                    self.herplaatsingen += 1
                    self._plaats_instap(now)
                else:
                    self._signaal_log(status="niet_gevuld", reden="verbinding")
                    self.fase = "klaar"
                return
        onbekende_orders = [o for o in oo if o.get("id") not in bekend]
        if onbekende_orders:
            self._onbekend("%d onbekende order(s)" % len(onbekende_orders))
            return
        if self.fase == "instap_open" and pos is not None:
            self._bij_fill(pos, now)
        elif self.fase == "positie":
            if pos is None:
                self._positie_weg(now)
            elif self._getekend(pos) != self.positie:
                self._onbekend("positie %+d, verwacht %+d" % (self._getekend(pos), self.positie))
            elif not any(o.get("id") == self.stop_order_id for o in oo):
                self.log.alarm("Stop-order ontbreekt na herstel: positie sluiten.")
                self._sluit_en_boek(now, "stop_ontbrak")
        elif pos is not None:
            self._onbekend("positie %+d terwijl de bot flat hoort te zijn" % self._getekend(pos))

    # ================= boekhouding =================
    def _signaal_log(self, status, reden="", **extra):
        rij = dict(self.rij, datum=self.dag.isoformat(), account=self.account, variant="A", status=status, reden=reden,
                   tijd_et=self.log.klok().astimezone(ET).strftime("%H:%M:%S"),
                   tijd_nl=self.log.klok().astimezone(NL).strftime("%H:%M:%S"))
        rij.update(extra)
        self.log.signaal(rij)
        if status in ("niet_gevuld",):
            self._bewaking()

    def _boek_trade(self, trade, slippage):
        voeg_live_trade_toe(trade, self.account, pad=self.journal_pad)
        self.log.info("TRADE %s: %s %d ZN, in %s uit %s (%s), netto $%.2f = %+.2fR" % (
            self.account, "long" if trade["richting"] > 0 else "short", trade["contracten"], in_32ste(trade["instap"]),
            in_32ste(trade["uitstap"]), trade["uitstapreden"], trade["netto"], trade["R"] or 0))
        self.rij.update({"instap": trade["instap"], "uitstap": trade["uitstap"], "uitstapreden": trade["uitstapreden"],
                         "netto": "%.2f" % trade["netto"], "R": "%.3f" % (trade["R"] or 0), "slippage_ticks": "%.2f" % slippage})
        self._signaal_log(status="gevuld")
        self._bewaking()

    def _bewaking(self):
        rows = lees_signalen(self.signalen_map, self.account)
        sig = [r for r in rows if r.get("status") in ("gevuld", "niet_gevuld")]
        gevuld = [r for r in sig if r["status"] == "gevuld"]
        slips = [float(r["slippage_ticks"]) for r in gevuld if r.get("slippage_ticks")]
        rs = [r for _, _, _, r in live_trades(self.account, self.journal_pad) if r is not None]
        bewaking.bijwerken(self.account, rs, len(sig), len(gevuld), slips, self.strat, self.log,
                           status_pad=self.status_pad, rapport_pad=self.map / "reports" / "live_vs_backtest.html",
                           backtest_pad=self.map / "reports" / "backtest_samenvatting.json")


# ======================= opstarten =======================
def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from .broker import ProjectXClient
    from .instellingen import BOT, ConfigFout, andere_bot_ids, lees_env, load_calendar, load_config, load_firm, load_strategy, valideer_config
    from .kalender_zn import Kalender
    from .logboek import Logboek
    ap = argparse.ArgumentParser()
    ap.add_argument("--modus", choices=None, default=None, help="paper (standaard) of sim")
    a = ap.parse_args(argv)
    try:
        cfg = load_config()
        if a.modus:
            cfg = valideer_config(dict(cfg, modus=a.modus))
    except ConfigFout as e:
        print("CONFIG GEWEIGERD: %s" % e)
        return 2
    strat, kal = load_strategy(), Kalender(load_calendar(), load_strategy())
    firm = load_firm(cfg.get("firma", "topstep_50k"))
    log = Logboek("zn_%s" % cfg["modus"])
    if cfg["modus"] == "sim":
        print("MODUS SIM: er gaan echte orders naar het practice-account %s." % cfg["account_id"])
        if input("Typ het account-ID ter bevestiging: ").strip() != str(cfg["account_id"]):
            print("Account-ID klopt niet. Gestopt.")
            return 2
    env = lees_env()
    if not env.get("PROJECTX_USERNAME") or not env.get("PROJECTX_API_KEY"):
        print("PROJECTX_USERNAME en PROJECTX_API_KEY ontbreken in .env (daytrading-map).")
        return 2
    broker = ProjectXClient(env["PROJECTX_USERNAME"], env["PROJECTX_API_KEY"], cfg.get("api_basis", "https://api.topstepx.com"),
                            per_seconde=strat["live"]["max_verzoeken_per_seconde"])
    broker.login()
    runner = ZNRunner(broker, strat, cfg, kal, firm, log, BOT, andere_bot_ids(cfg))
    if not runner.start():
        return 1
    log.info("Draait. Stoppen: stop_zn.bat (maakt het bestand STOP) of dit venster sluiten na 15:05 ET.")
    try:
        while not runner.gestopt:
            try:
                broker.houd_sessie_vast()
            except (VerbindingsFout, ApiFout) as e:
                log.waarschuwing("Sessie vernieuwen mislukt: %s" % e)
            runner.tick(dt.datetime.now(ET))
            time.sleep(1)
    except KeyboardInterrupt:
        runner.kill("Ctrl+C")
    log.info("Bot gestopt: %s" % (runner.stopreden or "klaar"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
