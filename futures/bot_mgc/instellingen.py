"""Laadt strategy.json, config.json, de gedeelde bestanden (firma, kalender, persoonlijke regels) en de API-keys uit .env."""
import json
import os
from pathlib import Path

BOT = Path(__file__).resolve().parent          # ...\daytrading\bot_mgc
ROOT = BOT.parent                               # ...\daytrading

TOEGESTANE_MODI = ("paper", "sim", "combine")


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


def load_personal():
    return _load(ROOT / "rules" / "personal.json")


def modus_van(cfg):
    return str(cfg.get("mode", cfg.get("modus", "paper"))).strip().lower()


def andere_bot_ids(cfg, root=ROOT):
    """Account-ID's van de MES-bot (bot\\config.json) en de ZN-bot (bot_zn\\config.json), plus wat in onze config staat."""
    ids = set(str(x) for x in (cfg.get("andere_bots_account_ids") or []) if x not in (None, ""))
    for sub in ("bot", "bot_zn"):
        p = Path(root) / sub / "config.json"
        if p.exists():
            try:
                c = _load(p)
                for k in ("account_id", "combine_account_id"):
                    if c.get(k) not in (None, ""):
                        ids.add(str(c[k]))
            except (ValueError, OSError):
                pass
    return ids


def actief_account(cfg):
    m = modus_van(cfg)
    if m == "combine":
        return cfg.get("combine_account_id")
    if m == "sim":
        return cfg.get("account_id")
    return None


def valideer_config(cfg, root=ROOT):
    """Weigert een onbekende modus, een modus zonder account en een account-ID van een andere bot."""
    m = modus_van(cfg)
    if m not in TOEGESTANE_MODI:
        raise ConfigFout("Modus '%s' bestaat niet. Alleen 'paper', 'sim' of 'combine'." % m)
    cfg = dict(cfg)
    cfg["mode"] = m
    if m in ("sim", "combine"):
        acc = actief_account(cfg)
        if acc in (None, ""):
            raise ConfigFout("Modus '%s' heeft een %s nodig in bot_mgc/config.json."
                             % (m, "combine_account_id" if m == "combine" else "account_id"))
        if str(acc) in andere_bot_ids(cfg, root):
            raise ConfigFout("Account %s is ook van de MES- of ZN-bot. Gebruik een apart account." % acc)
    cfg["account_actief"] = actief_account(cfg)
    return cfg


def load_config(path=None, root=ROOT):
    return valideer_config(_load(path or BOT / "config.json"), root)


def lees_env(paden=None):
    """Leest KEY=waarde-regels uit .env (in de daytrading-map, anders in bot_mgc). Waarden komen nooit in logs."""
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
