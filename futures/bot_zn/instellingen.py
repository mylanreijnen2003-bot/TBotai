"""Laadt strategy.json, config.json, de gedeelde bestanden (firma, kalender) en de API-keys uit .env."""
import json
import os
from pathlib import Path

BOT = Path(__file__).resolve().parent          # ...\daytrading\bot_zn
ROOT = BOT.parent                               # ...\daytrading

TOEGESTANE_MODI = ("paper", "sim")


class ConfigFout(Exception):
    pass


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_strategy(path=None):
    return _load(path or BOT / "strategy.json")


def load_calendar(path=None):
    return _load(path or ROOT / "calendar.json")


def load_firm(name="topstep_50k"):
    return _load(ROOT / "firms" / (name + ".json"))


def andere_bot_ids(cfg, root=ROOT):
    """Account-ID's van de MES-bot (bot\\config.json) en MGC-bot (bot_mgc\\config.json), plus wat in onze config staat."""
    ids = set(str(x) for x in (cfg.get("andere_bots_account_ids") or []) if x not in (None, ""))
    for sub in ("bot", "bot_mgc"):
        p = Path(root) / sub / "config.json"
        if p.exists():
            try:
                v = _load(p).get("account_id")
                if v not in (None, ""):
                    ids.add(str(v))
            except (ValueError, OSError):
                pass
    return ids


def valideer_config(cfg, root=ROOT):
    """Weigert een onbekende modus (er bestaat geen combine-modus) en een account-ID van een andere bot."""
    modus = str(cfg.get("modus", "paper")).strip().lower()
    if modus not in TOEGESTANE_MODI:
        raise ConfigFout("Modus '%s' bestaat niet. Alleen 'paper' of 'sim' is toegestaan; "
                         "een combine-modus wordt bewust niet gebouwd." % cfg.get("modus"))
    if modus == "sim":
        acc = cfg.get("account_id")
        if acc in (None, ""):
            raise ConfigFout("Modus 'sim' heeft een account_id nodig in bot_zn/config.json.")
        if str(acc) in andere_bot_ids(cfg, root):
            raise ConfigFout("account_id %s is ook van de MES- of MGC-bot. Gebruik een apart account." % acc)
    cfg = dict(cfg)
    cfg["modus"] = modus
    return cfg


def load_config(path=None, root=ROOT):
    return valideer_config(_load(path or BOT / "config.json"), root)


def lees_env(paden=None):
    """Leest KEY=waarde-regels uit .env (in de daytrading-map, anders in bot_zn). Waarden komen nooit in logs."""
    out = {}
    for p in paden or (ROOT / ".env", BOT / ".env"):
        if not Path(p).exists():
            continue
        with open(p, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    for k in ("DATABENTO_API_KEY", "PROJECTX_USERNAME", "PROJECTX_API_KEY"):
        if os.environ.get(k) and k not in out:
            out[k] = os.environ[k]
    return out
