"""Kalender van de cijfers om 10:00 ET voor strategie E, afgeleid uit vaste regels (geen download nodig).

- ISM Manufacturing:        1e werkdag van de maand
- ISM Services (vroeger Non-Manufacturing): 3e werkdag van de maand
- Conference Board Consumer Confidence:      laatste dinsdag van de maand
Werkdag = maandag t/m vrijdag, geen Amerikaanse (obligatie)feestdag. Uitzonderingen in het verleden (verschoven
publicaties) worden zo niet gevangen; dat staat als beperking in de README.
"""
import datetime as dt


def _werkdagen_van_maand(jaar, maand, kal):
    d = dt.date(jaar, maand, 1)
    out = []
    while d.month == maand:
        if kal.is_handelsdag(d):
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def releases_10u(jaar_van, jaar_tot, kal):
    """-> {datum: 'ISM Manufacturing' | 'ISM Services' | 'Conference Board'} (bij samenvallen samengevoegd)."""
    out = {}
    for j in range(jaar_van, jaar_tot + 1):
        for m in range(1, 13):
            w = _werkdagen_van_maand(j, m, kal)
            if len(w) >= 3:
                out.setdefault(w[0], []).append("ISM Manufacturing")
                out.setdefault(w[2], []).append("ISM Services")
            laatste = dt.date(j + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
            while laatste.weekday() != 1:
                laatste -= dt.timedelta(days=1)
            out.setdefault(laatste, []).append("Conference Board")
    return {d: " + ".join(v) for d, v in out.items()}
