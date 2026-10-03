"""Bouwstenen: prijzen op een tijdstip, VWAP, 5-minuutbars, positiegrootte en de gesimuleerde fill van één trade.

bars = {'HH:MM' (ET, begintijd van de 1-minuutbar): (open, hoog, laag, slot, volume)}.
Alles is conservatief (plan-MES §8): market-instap op de opening + 1 tick, stop op stop − 1 tick (of de opening als
die al voorbij de stop ligt), doel alleen gevuld als de koers 1 tick voorbij het doel handelt, stop en doel in
dezelfde minuut → de stop telt, tijdsuitstap op de opening van die minuut − 1 tick.
"""
import math


def plus_min(hhmm, minuten):
    h, m = (int(x) for x in hhmm.split(":"))
    t = h * 60 + m + minuten
    return "%02d:%02d" % (t // 60, t % 60)


def prijs_om(bars, hhmm, vanaf):
    """Prijs op tijdstip hhmm = slot van de laatste bar die vóór hhmm begon (niet eerder dan 'vanaf')."""
    ks = [k for k in bars if vanaf <= k < hhmm]
    return bars[max(ks)][3] if ks else None


def open_vanaf(bars, hhmm, tot):
    """(minuut, opening) van de eerste bar vanaf hhmm (t/m tot); None als die er niet is."""
    ks = sorted(k for k in bars if hhmm <= k <= tot)
    return (ks[0], bars[ks[0]][0]) if ks else (None, None)


def op_tick(x, tick):
    return round(math.floor(x / tick + 0.5) * tick, 6)


def vijf_minuten(bars, van="09:30", tot="15:59"):
    """5-minuutbars uit 1-minuutbars, beginnend op :00, :05, ... -> {'HH:MM': (o, h, l, c, v)}."""
    out = {}
    for k in sorted(x for x in bars if van <= x <= tot):
        h, m = k.split(":")
        s = "%s:%02d" % (h, int(m) // 5 * 5)
        o, hi, lo, c, v = bars[k]
        if s in out:
            o0, h0, l0, _, v0 = out[s]
            out[s] = (o0, max(h0, hi), min(l0, lo), c, v0 + v)
        else:
            out[s] = (o, hi, lo, c, v)
    return out


def vwap_reeks(bars, van="09:30", tot="15:59"):
    """{'HH:MM': VWAP t/m die 1-minuutbar}, vanaf 09:30. Typische prijs = (hoog + laag + slot) / 3.
    Zonder volume (ontbrekende data) telt elke minuut even zwaar."""
    out, som_pv, som_v, som_p, n = {}, 0.0, 0.0, 0.0, 0
    for k in sorted(x for x in bars if van <= x <= tot):
        o, h, l, c, v = bars[k]
        tp = (h + l + c) / 3.0
        som_pv += tp * (v or 0)
        som_v += v or 0
        som_p += tp
        n += 1
        out[k] = som_pv / som_v if som_v > 0 else som_p / n
    return out


def contracten(stop_punten, strat, afstand_tot_bodem=None):
    """(aantal, reden): floor($200 / (stop × $5)), max 5; halveren als saldo − bodem < $600."""
    n = int(math.floor(strat["risico_per_trade"] / (stop_punten * strat["instrument"]["punt_waarde"]) + 1e-9))
    n = min(n, strat["max_contracten"])
    if n <= 0:
        return 0, "stop_te_groot"
    if afstand_tot_bodem is not None and afstand_tot_bodem < strat["halveren_binnen_usd_van_bodem"]:
        n //= 2
        if n <= 0:
            return 0, "gehalveerd_naar_0"
    return n, ""


def simuleer_trade(bars, richting, instap_minuut, instap, stop, doel, uitstap_tijd, contracten_, strat):
    """Volgt één trade op 1-minuutbars vanaf de instapminuut. -> dict met uitstap, reden en resultaat."""
    tick = strat["instrument"]["tick"]
    slip = strat["slippage_ticks"] * tick
    door = strat["doel_doorbraak_ticks"] * tick
    pv = strat["instrument"]["punt_waarde"]
    slechtste = beste = instap
    uit = reden = uit_min = None
    for k in sorted(x for x in bars if instap_minuut <= x):
        o, h, l, c, v = bars[k]
        if k >= uitstap_tijd:
            uit, reden, uit_min = o - richting * slip, "tijd", k
            break
        geraakt_stop = (l <= stop) if richting > 0 else (h >= stop)
        if geraakt_stop:
            basis = stop if k == instap_minuut else (min(o, stop) if richting > 0 else max(o, stop))
            uit, reden, uit_min = basis - richting * slip, "stop", k
            slechtste = uit if richting > 0 else uit
            break
        if doel is not None and ((h >= doel + door) if richting > 0 else (l <= doel - door)):
            uit, reden, uit_min = doel, "doel", k
            beste = doel
            break
        if richting > 0:
            slechtste, beste = min(slechtste, l), max(beste, h)
        else:
            slechtste, beste = max(slechtste, h), min(beste, l)
    if uit is None:   # geen bar meer (ontbrekende data): laatste koers
        ks = sorted(x for x in bars if instap_minuut <= x)
        if not ks:
            return None
        uit, reden, uit_min = bars[ks[-1]][3] - richting * slip, "tijd_geen_bar", ks[-1]
    bruto = (uit - instap) * richting * pv * contracten_
    kosten = strat["kosten_per_contract_rt"] * contracten_
    risico = abs(instap - stop) * pv * contracten_
    netto = bruto - kosten
    mae = min(0.0, (slechtste - instap) * richting * pv * contracten_, netto)
    return {"richting": richting, "instap_minuut": instap_minuut, "instap": round(instap, 6), "stop": round(stop, 6),
            "doel": None if doel is None else round(doel, 6), "uitstap_minuut": uit_min, "uitstap": round(uit, 6),
            "uitstapreden": reden, "contracten": contracten_, "bruto": bruto, "kosten": kosten, "netto": netto,
            "risico": risico, "R": netto / risico if risico else None, "mae": mae,
            "mfe": max(0.0, (beste - instap) * richting * pv * contracten_)}
