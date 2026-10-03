"""Kalender: mag ik vandaag traden, en in welk venster?"""
import datetime as dt


def _in(d, van, tot):
    return dt.date.fromisoformat(van) <= d <= dt.date.fromisoformat(tot)


def is_dst_mismatch(d, cal):
    return any(_in(d, p["van"], p["tot"]) for p in cal.get("dst_mismatch", []))


def day_info(d, cal, config):
    iso = d.isoformat()
    redenen = []
    if d.weekday() >= 5:
        redenen.append("weekend")
    for p in cal.get("geen_trade_periodes", []):
        if _in(d, p["van"], p["tot"]):
            redenen.append(p["reden"])
    for h in cal.get("us_feestdagen", []):
        if h["datum"] == iso:
            redenen.append("US-feestdag: " + h["reden"])
    for v in cal.get("vervroegde_sluiting", []):
        if v["datum"] == iso:
            redenen.append("vervroegde sluiting: " + v["reden"])
    if iso in cal.get("fomc", {}).get("dagen", []):
        redenen.append("FOMC-rentebesluit (controleer op federalreserve.gov)")
    dst = is_dst_mismatch(d, cal)
    v = config["handelsvenster_dst_mismatch" if dst else "handelsvenster"]
    return {
        "datum": d,
        "traden": not redenen,
        "redenen": redenen,
        "venster": (v["start"], v["eind"]),
        "dst": dst,
    }


def in_window(tijd, info):
    """tijd = 'HH:MM'. Strings met voorloopnul zijn alfabetisch te vergelijken."""
    start, eind = info["venster"]
    return start <= tijd.strip()[:5].zfill(5) <= eind


def tekst(info):
    s, e = info["venster"]
    dst = " (DST-mismatchweek: alles 1 uur eerder)" if info["dst"] else ""
    if info["traden"]:
        return "Vandaag: WEL traden, venster %s–%s%s" % (s, e, dst)
    return "Vandaag: NIET traden (%s)%s" % ("; ".join(info["redenen"]), dst)
