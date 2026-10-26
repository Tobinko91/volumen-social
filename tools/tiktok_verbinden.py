"""TikTok-Konto einmalig mit der App verbinden (Login Kit). Aufruf als root:
    python3 /opt/volumen-social/app/tools/tiktok_verbinden.py

1. Das Skript zeigt einen Link. Den im Browser oeffnen, in dem du bei TikTok als @whalesqueeze angemeldet bist.
2. Bei TikTok „Authorize“ / „Erlauben“ tippen.
3. TikTok leitet auf https://whalesqueeze.com/tiktok/?code=… weiter. Die Seite selbst ist egal (sie kann leer sein
   oder nach dem Website-Passwort fragen) – kopiere die GANZE Adresse aus der Adresszeile und fuege sie hier ein.
Die Tokens landen nur in secrets.yaml (nur fuer den Benutzer "redaktion" lesbar).

    python3 tiktok_verbinden.py --erneuern   (taeglich aus plan.sh: Zugang verlaengern, still)
"""
from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import telegram, tiktok  # noqa: E402


def laden() -> dict:
    p = tiktok.geheim_datei()
    return (yaml.safe_load(p.read_text()) if p.exists() else {}) or {}


def besitzer_redaktion() -> None:
    try:
        import pwd
        u = pwd.getpwnam("redaktion")
        os.chown(tiktok.geheim_datei(), u.pw_uid, u.pw_gid)
    except (KeyError, PermissionError):
        pass


def erneuern_still(post=None) -> int:
    g = laden()
    if not g.get("tiktok_refresh_token"):
        return 0
    try:
        tiktok.speichern(g, tiktok.erneuern(g, **({"post": post} if post else {})))
    except Exception as e:
        telegram.text_senden(g, f"⚠️ TikTok-Zugang konnte nicht verlängert werden: {e}\n"
                                "Bitte einmal neu verbinden: tiktok_verbinden.py (Anleitung im Redaktions-Chat).")
        return 1
    return 0


def main() -> int:
    if "--erneuern" in sys.argv:
        return erneuern_still()
    g = laden()
    if not (g.get("tiktok_client_key") and g.get("tiktok_client_secret")):
        print("Zuerst Client key und Client secret eintragen: schluessel.py, Punkte 10 und 11.")
        return 1
    state = tiktok.neuer_state()
    print("\n1) Diesen Link im Browser oeffnen (angemeldet als @whalesqueeze) und erlauben:\n")
    print(tiktok.login_link(g["tiktok_client_key"], state))
    print("\n2) Danach die GANZE Adresse aus der Adresszeile kopieren (beginnt mit https://whalesqueeze.com/tiktok/).")
    adresse = getpass.getpass("   Hier einfuegen (unsichtbar), dann Enter: ")
    try:
        code = tiktok.code_aus_adresse(adresse, state)
        tiktok.speichern(g, tiktok.code_tauschen(g, code))
    except tiktok.TikTokFehler as e:
        print(f"!! {e}")
        return 1
    besitzer_redaktion()
    print("Verbunden. Im Redaktions-Bot /status schreiben: dort muss jetzt „TikTok ✅“ stehen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
