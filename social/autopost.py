"""Freigabe-Tor (Wunsch Tobias 01.11.2026): Routine-Formate posten automatisch, wenn sie sich bewaehrt haben.

Ein Format darf automatisch posten, wenn ALLES gilt:
- es steht in autopost.formate (News und Eilmeldungen nie, die bleiben immer bei Tobias' Knopfdruck),
- das Protokoll reicht mindestens autopost.saubere_tage (14) zurueck,
- Tobias hat in diesen Tagen mindestens autopost.min_freigaben (10) Beitraege dieses Formats freigegeben,
- und keinen einzigen verworfen (ein Verwerfen schliesst das Tor fuer dieses Format sofort wieder),
- die automatische Pruefung des einzelnen Beitrags ist bestanden,
- Tobias hat es nicht mit /auto aus abgeschaltet (Datei ausgabe/.autopost_aus).
Tobias bekommt jeden automatischen Post als Nachricht mit Links (kann ihn dort sehen und notfalls loeschen).
"""
from __future__ import annotations

import time
from pathlib import Path

from . import bericht

TAG = 86400


def erlaubt(format: str, protokoll: list[dict], cfg: dict, aus: bool = False,
            jetzt: float | None = None) -> tuple[bool, str]:
    a = cfg.get("autopost") or {}
    jetzt = jetzt or time.time()
    if not a.get("aktiv", False):
        return False, "Freigabe-Tor ist in config.yaml aus"
    if aus:
        return False, "mit /auto aus gestoppt"
    if format not in (a.get("formate") or []):
        return False, f"{format} bleibt immer bei deiner Freigabe"
    tage = int(a.get("saubere_tage", 14))
    fenster = [e for e in protokoll if e.get("format") == format and e.get("ts", 0) >= jetzt - tage * TAG]
    if not protokoll or min(e.get("ts", jetzt) for e in protokoll) > jetzt - tage * TAG:
        return False, f"Protokoll noch jünger als {tage} Tage"
    verworfen = sum(1 for e in fenster if e.get("ereignis") == "verworfen")
    if verworfen:
        return False, f"{verworfen}× verworfen in {tage} Tagen"
    freigaben = len({e["ordner"] for e in fenster if e.get("ereignis") == "gepostet"})
    if freigaben < int(a.get("min_freigaben", 10)):
        return False, f"erst {freigaben} Freigaben in {tage} Tagen (nötig: {a.get('min_freigaben', 10)})"
    return True, f"{freigaben} Freigaben, 0 verworfen in {tage} Tagen"


def status(protokoll: list[dict], cfg: dict, aus: bool = False, jetzt: float | None = None) -> str:
    """Fuer /auto im Redaktions-Bot."""
    a = cfg.get("autopost") or {}
    z = ["🤖 Freigabe-Tor" + (" (gestoppt mit /auto aus)" if aus else "")]
    for f in a.get("formate") or []:
        ok, grund = erlaubt(f, protokoll, cfg, aus, jetzt)
        z.append(f"{'✅' if ok else '⏳'} {bericht.NAMEN.get(f, f)}: {grund}")
    z.append("News und Eilmeldungen bleiben immer bei deinem Knopfdruck. Stoppen: /auto aus · weiter: /auto an")
    return "\n".join(z)


def aus_datei(ausgabe: Path) -> Path:
    return ausgabe / ".autopost_aus"
