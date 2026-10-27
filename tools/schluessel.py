"""Schluessel sicher auf dem Server eintragen (Eingabe unsichtbar, nie im Chat).
Aufruf als root:  python3 /opt/volumen-social/app/tools/schluessel.py"""
import getpass
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import telegram  # noqa: E402

DATEI = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social")) / "secrets.yaml"
FELDER = [
    ("anthropic_api_key", "Claude-API-Schluessel (beginnt mit sk-ant-)"),
    ("elevenlabs_api_key", "ElevenLabs-Schluessel (beginnt mit sk_)"),
    ("telegram_token", "Token des Redaktions-Bots von @BotFather (Zahlen:Buchstaben)"),
    ("telegram_kanal", "Telegram-Kanal, z. B. @whalesqueeze (Redaktions-Bot muss dort Admin sein)"),
    ("x_api_key", "X: API Key (Consumer Key)"),
    ("x_api_secret", "X: API Key Secret (Consumer Secret)"),
    ("x_access_token", "X: Access Token"),
    ("x_access_secret", "X: Access Token Secret"),
    ("instagram_token", "Instagram: Access Token (Meta-App -> API-Einrichtung mit Instagram-Login -> Generate token)"),
    ("tiktok_client_key", "TikTok: Client key (developers.tiktok.com -> App -> Credentials)"),
    ("tiktok_client_secret", "TikTok: Client secret"),
]
OFFEN = {"telegram_kanal", "tiktok_client_key"}   # kein Geheimnis: Eingabe sichtbar


def main():
    daten = yaml.safe_load(DATEI.read_text()) if DATEI.exists() else {}
    daten = daten or {}
    print("Welchen Schluessel eintragen? Enter = ueberspringen.\n")
    for i, (k, text) in enumerate(FELDER, 1):
        status = "gesetzt" if daten.get(k) else "fehlt"
        print(f"  {i}) {text}  [{status}]")
    wahl = input("\nNummer: ").strip()
    if not wahl.isdigit() or not 1 <= int(wahl) <= len(FELDER):
        print("Nichts geaendert."); return
    k, text = FELDER[int(wahl) - 1]
    if k in OFFEN:
        wert = input(f"{text}: ").strip()
    else:
        wert = getpass.getpass(f"{text} einfuegen (unsichtbar), dann Enter: ").strip()
    if not wert:
        print("Leer – nichts geaendert."); return
    daten[k] = wert
    if k == "telegram_token":
        input("Schreib dem Redaktions-Bot in Telegram jetzt /start, dann hier Enter ... ")
        chat = telegram.chat_id_finden(wert)
        if chat:
            daten["telegram_chat_id"] = chat
            print("Chat gefunden.")
        else:
            print("!! Keine Nachricht gefunden. /start schicken und dieses Skript noch einmal starten.")
    DATEI.write_text(yaml.safe_dump(daten, allow_unicode=True))
    os.chmod(DATEI, 0o600)
    try:
        import pwd
        u = pwd.getpwnam("redaktion")
        os.chown(DATEI, u.pw_uid, u.pw_gid)
    except KeyError:
        pass
    print(f"Gespeichert ({k}). Datei nur fuer den Benutzer 'redaktion' lesbar.")


if __name__ == "__main__":
    main()
