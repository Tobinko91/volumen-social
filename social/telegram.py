"""Telegram fuer die Redaktion: eigener Bot (nicht der Signal-Bot), schickt Vorschlaege an Tobias.
Jeder Vorschlag kommt mit Knoepfen: auf Telegram-Kanal und/oder X posten oder verwerfen (tools/freigabe.py)."""
from __future__ import annotations

from pathlib import Path

import requests

API = "https://api.telegram.org/bot{token}/{methode}"
BILDTEXT_MAX = 1024   # Telegram: Text unter einem Bild (sichtbare Zeichen)


def sichtbar(text: str) -> int:
    """Laenge so, wie Telegram sie zaehlt (ohne HTML-Tags, &amp; = 1 Zeichen)."""
    import html
    import re
    return len(html.unescape(re.sub(r"<[^>]+>", "", text)))


def teilen(text: str) -> tuple[str, str | None]:
    """Langer Beitrag: Bildtext = erster Absatz (Schlagzeile), Rest als eigene Nachricht direkt danach.
    Kurzer Beitrag: alles unter das Bild."""
    if sichtbar(text) <= BILDTEXT_MAX:
        return text, None
    kopf, _, rest = text.partition("\n\n")
    if not rest or sichtbar(kopf) > BILDTEXT_MAX:
        return "", text
    return kopf, rest


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


def knoepfe(beitrag_id: str) -> dict:
    """Inline-Knoepfe fuer die Freigabe. callback_data hoechstens 64 Zeichen."""
    def k(text, ziel):
        return {"text": text, "callback_data": f"p|{ziel}|{beitrag_id}"[:64]}
    return {"inline_keyboard": [[k("📢 Telegram-Kanal", "tg"), k("𝕏 X", "x")],
                                [k("📸 Instagram", "ig"), k("🎵 TikTok", "tt")],
                                [k("✅ Alle Kanäle", "alle"), k("🗑 Verwerfen", "nein")]]}


def vorschlag_senden(geheim: dict, ordner: Path, hinweis: str = "") -> bool:
    """Bild + Telegram-Text mit Freigabe-Knoepfen, danach der X-Text zum Lesen."""
    import json
    token, chat = geheim.get("telegram_token"), geheim.get("telegram_chat_id")
    if not (token and chat):
        return False
    bild = ordner / "post.png"
    tg = (ordner / "post_telegram.txt").read_text(encoding="utf-8")
    x = (ordner / "post_x.txt").read_text(encoding="utf-8")
    kopf, rest = teilen(tg)
    if rest:   # langer Beitrag: so, wie er spaeter im Kanal erscheint (Bild + Text darunter), Knoepfe am Ende
        with open(bild, "rb") as fh:
            requests.post(API.format(token=token, methode="sendPhoto"),
                          data={"chat_id": chat, "caption": kopf, "parse_mode": "HTML"},
                          files={"photo": (bild.name, fh, "image/png")}, timeout=60)
        r = requests.post(API.format(token=token, methode="sendMessage"),
                          data={"chat_id": chat, "text": rest[:4096], "parse_mode": "HTML",
                                "disable_web_page_preview": "true",
                                "reply_markup": json.dumps(knoepfe(ordner.name))}, timeout=30)
    else:
        with open(bild, "rb") as fh:
            r = requests.post(API.format(token=token, methode="sendPhoto"),
                              data={"chat_id": chat, "caption": tg, "parse_mode": "HTML",
                                    "reply_markup": json.dumps(knoepfe(ordner.name))},
                              files={"photo": (bild.name, fh, "image/png")}, timeout=60)
    text_senden(geheim, (hinweis + "\n\n" if hinweis else "") + f"X-Text ({len(x)} Zeichen):\n\n" + x)
    return r.ok
