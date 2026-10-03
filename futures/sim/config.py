"""Laadt de instellingen-bestanden (config, persoonlijke regels, kalender, firma's)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_config():
    return _load(ROOT / "config.json")


def load_personal():
    return _load(ROOT / "rules" / "personal.json")


def load_calendar():
    return _load(ROOT / "calendar.json")


def load_firm(name_or_path):
    p = Path(name_or_path)
    if not p.exists():
        p = ROOT / "firms" / (str(name_or_path) + ".json")
    return _load(p)


def list_firms():
    return sorted(p.stem for p in (ROOT / "firms").glob("*.json"))
