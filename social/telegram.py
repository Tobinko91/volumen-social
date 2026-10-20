"""Telegram fuer die Redaktion: eigener Bot (nicht der Signal-Bot), schickt Videos an Tobias.
Spaeter (Phase 2) kommen die Knoepfe "Posten" und "Verwerfen" dazu."""
from __future__ import annotations

from pathlib import Path

import requests

API = "https://api.telegram.org/bot{token}/{methode}"


def video_senden(geheim: dict, datei: Path, text: str) -> bool:
    token, chat = geheim.get("telegram_token"), geheim.get("telegram_chat_id")
    if not (token and chat):
        return False
    with open(datei, "rb") as fh:
        r = requests.post(API.format(token=token, methode="sendVideo"),
                          data={"chat_id": chat, "caption": text[:1000], "supports_streaming": "true"},
                          files={"video": (datei.name, fh, "video/mp4")}, timeout=120)
    return r.ok


def chat_id_finden(token: str) -> str | None:
    """Liest die Chat-ID aus der letzten Nachricht an den Bot (Tobias schreibt vorher /start)."""
    r = requests.get(API.format(token=token, methode="getUpdates"), timeout=30)
    r.raise_for_status()
    for u in reversed(r.json().get("result", [])):
        msg = u.get("message") or {}
        if msg.get("chat", {}).get("type") == "private":
            return str(msg["chat"]["id"])
    return None


def bild_senden(geheim: dict, datei: Path, text: str) -> bool:
    """Bild mit Text (HTML) an Tobias – so sieht der spaetere Telegram-Beitrag aus."""
    token, chat = geheim.get("telegram_token"), geheim.get("telegram_chat_id")
    if not (token and chat):
        return False
    with open(datei, "rb") as fh:
        r = requests.post(API.format(token=token, methode="sendPhoto"),
                          data={"chat_id": chat, "caption": text[:1024], "parse_mode": "HTML"},
                          files={"photo": (datei.name, fh, "image/png")}, timeout=60)
    return r.ok


def text_senden(geheim: dict, text: str) -> bool:
    token, chat = geheim.get("telegram_token"), geheim.get("telegram_chat_id")
    if not (token and chat):
        return False
    r = requests.post(API.format(token=token, methode="sendMessage"),
                      data={"chat_id": chat, "text": text[:4000], "disable_web_page_preview": "true"}, timeout=30)
    return r.ok
