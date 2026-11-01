"""YouTube-Kanal einmalig mit der App verbinden (OAuth). Aufruf als root:
    python3 /opt/volumen-social/app/tools/youtube_verbinden.py

1. Das Skript zeigt einen Link. Den im Browser oeffnen, in dem du mit dem Google-Konto des Kanals angemeldet bist.
2. Kanal @whalesqueeze waehlen, bei „Google hat diese App nicht ueberprueft“ auf „Erweitert“ -> „Weiter zu …“,
   dann „Zulassen“.
3. Google leitet auf https://whalesqueeze.com/youtube/?code=… weiter. Die Seite selbst ist egal – kopiere die GANZE
   Adresse aus der Adresszeile und fuege sie hier ein (innerhalb weniger Minuten).
Die Schluessel landen nur in secrets.yaml.
"""
from __future__ import annotations

import getpass
import secrets
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import tiktok, youtube  # noqa: E402


def main() -> int:
    p = tiktok.geheim_datei()
    g = (yaml.safe_load(p.read_text()) if p.exists() else {}) or {}
    if not (g.get("youtube_client_id") and g.get("youtube_client_secret")):
        print("Zuerst Client-ID und Client secret eintragen: schluessel.py, Punkte 12 und 13.")
        return 1
    state = secrets.token_urlsafe(16)
    print("\n1) Diesen Link im Browser oeffnen (Google-Konto des Kanals) und erlauben:\n")
    print(youtube.login_link(g["youtube_client_id"], state))
    print("\n2) Danach die GANZE Adresse aus der Adresszeile kopieren (beginnt mit https://whalesqueeze.com/youtube/).")
    adresse = getpass.getpass("   Hier einfuegen (unsichtbar), dann Enter: ")
    try:
        neu = youtube.code_tauschen(g, youtube.code_aus_adresse(adresse, state))
    except youtube.YouTubeFehler as e:
        print(f"!! {e}")
        return 1
    if "youtube_refresh_token" not in neu:
        print("!! Google hat keinen dauerhaften Zugang geschickt. Bitte unter myaccount.google.com/permissions den "
              "Zugriff der App entfernen und neu verbinden.")
        return 1
    tiktok.speichern(g, neu)
    try:
        import os
        import pwd
        u = pwd.getpwnam("redaktion")
        os.chown(p, u.pw_uid, u.pw_gid)
    except (KeyError, PermissionError):
        pass
    print("Verbunden. Im Redaktions-Bot /status schreiben: dort muss jetzt „YouTube ✅“ stehen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
