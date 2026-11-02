"""S31 Zeitversetzt posten (Entscheidung Tobias 02.11.2026): einmal freigeben, jeder Kanal zu seiner Zeit.

- Telegram und X sofort (Telegram zuerst: „Live alerts first on Telegram“ bleibt wahr).
- Instagram, TikTok, YouTube zur US-Hauptzeit (Fenster in deutscher Zeit, config zeitplan.fenster).
  Freigabe innerhalb des Fensters: sofort. Davor: wartet bis Fensterbeginn. Danach: naechster Tag.
- News und Redaktions-Beitraege (Eilmeldungen, Wahl) gehen ueberall sofort raus (zeitplan.sofort_formate).
- TikTok bei „Alle Kanäle“ nur Videos und Bilderserien (zeitplan.nur_video), einzeln per Knopf geht alles.
Nur fuer „Alle Kanäle“ und das Freigabe-Tor; ein einzelner Kanal-Knopf postet immer sofort.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


def faellig(fenster: str, jetzt: float, ende: str = "23:59") -> float:
    """Zeitpunkt (Unix), zu dem in diesem Fenster gepostet wird: jetzt, wenn wir drin sind, sonst Fensterbeginn."""
    t = dt.datetime.fromtimestamp(jetzt, BERLIN)
    h, m = map(int, fenster.split(":"))
    eh, em = map(int, ende.split(":"))
    start = t.replace(hour=h, minute=m, second=0, microsecond=0)
    schluss = t.replace(hour=eh, minute=em, second=59, microsecond=0)
    if start <= t <= schluss:
        return jetzt
    if t < start:
        return start.timestamp()
    return (start + dt.timedelta(days=1)).timestamp()


def aufteilen(ziele: list[str], format_: str, ist_bild: bool, cfg: dict, jetzt: float) -> tuple[list[str], dict]:
    """-> (jetzt posten, {kanal: zeitpunkt} spaeter). ist_bild = einzelnes Bild (kein Video, keine Bilderserie)."""
    z = cfg.get("zeitplan") or {}
    if not z.get("aktiv"):
        return ziele, {}
    if ist_bild:
        ziele = [k for k in ziele if k not in (z.get("nur_video") or [])]
    if format_ in (z.get("sofort_formate") or []):
        return ziele, {}
    sofort, spaeter = [], {}
    for k in ziele:
        f = (z.get("fenster") or {}).get(k)
        wann = faellig(f, jetzt, z.get("ende", "23:59")) if f else jetzt
        if wann <= jetzt:
            sofort.append(k)
        else:
            spaeter[k] = wann
    return sofort, spaeter


def uhr(ts: float) -> str:
    t = dt.datetime.fromtimestamp(ts, BERLIN)
    heute = dt.datetime.now(BERLIN).date()
    return t.strftime("%H:%M") + ("" if t.date() == heute else " (morgen)" if t.date() == heute + dt.timedelta(days=1)
                                  else t.strftime(" (%d.%m.)"))
