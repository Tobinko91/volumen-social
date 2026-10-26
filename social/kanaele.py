"""Veroeffentlichen auf den Kanaelen. Schluessel nur aus secrets.yaml auf dem Server.

Telegram-Kanal: der Redaktions-Bot ist Admin im Kanal und postet dort.
X: API v2 mit OAuth 1.0a (Konto-Schluessel aus dem X-Entwicklerportal).
Instagram und TikTok folgen (brauchen Meta-App bzw. TikTok-Pruefung).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets as _zufall
import time
import urllib.parse
from pathlib import Path

import requests

TG = "https://api.telegram.org/bot{token}/{methode}"
X_MEDIA = "https://api.x.com/2/media/upload"
X_TWEET = "https://api.x.com/2/tweets"


class NichtEingerichtet(Exception):
    pass


def verfuegbar(geheim: dict) -> dict[str, bool]:
    return {
        "telegram": bool(geheim.get("telegram_token") and geheim.get("telegram_kanal")),
        "x": all(geheim.get(k) for k in ("x_api_key", "x_api_secret", "x_access_token", "x_access_secret")),
    }


# ---------------------------------------------------------------- Telegram-Kanal

def telegram_kanal(geheim: dict, bild: Path, text: str) -> str:
    if not verfuegbar(geheim)["telegram"]:
        raise NichtEingerichtet("Telegram-Kanal fehlt (schluessel.py, Punkt 4)")
    from .telegram import teilen
    kopf, rest = teilen(text)   # ueber 1024 Zeichen: Bild mit Schlagzeile, ganzer Text direkt darunter
    with open(bild, "rb") as fh:
        r = requests.post(TG.format(token=geheim["telegram_token"], methode="sendPhoto"),
                          data={"chat_id": geheim["telegram_kanal"], "caption": kopf, "parse_mode": "HTML"},
                          files={"photo": (bild.name, fh, "image/png")}, timeout=60)
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(j.get("description", "Telegram-Fehler"))
    m = j["result"]
    if rest:
        r2 = requests.post(TG.format(token=geheim["telegram_token"], methode="sendMessage"),
                           data={"chat_id": geheim["telegram_kanal"], "text": rest[:4096], "parse_mode": "HTML",
                                 "disable_web_page_preview": "true"}, timeout=30).json()
        if not r2.get("ok"):
            raise RuntimeError(r2.get("description", "Telegram-Fehler"))
    kanal = str(geheim["telegram_kanal"]).lstrip("@")
    return f"https://t.me/{kanal}/{m['message_id']}"


# ---------------------------------------------------------------- X (OAuth 1.0a)

def _q(s: str) -> str:
    return urllib.parse.quote(str(s), safe="~-._")


def oauth_kopf(methode: str, url: str, geheim: dict, params: dict | None = None,
               nonce: str | None = None, ts: str | None = None) -> str:
    """OAuth-1.0a-Signatur (HMAC-SHA1). params: nur Query-/Formularfelder, nicht JSON- oder Multipart-Inhalt."""
    o = {
        "oauth_consumer_key": geheim["x_api_key"],
        "oauth_nonce": nonce or _zufall.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": ts or str(int(time.time())),
        "oauth_token": geheim["x_access_token"],
        "oauth_version": "1.0",
    }
    alle = {**(params or {}), **o}
    norm = "&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(alle.items()))
    basis = "&".join([methode.upper(), _q(url), _q(norm)])
    key = f"{_q(geheim['x_api_secret'])}&{_q(geheim['x_access_secret'])}"
    o["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), basis.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_q(k)}="{_q(v)}"' for k, v in sorted(o.items()))


def x_posten(geheim: dict, bild: Path, text: str) -> str:
    if not verfuegbar(geheim)["x"]:
        raise NichtEingerichtet("X-Schluessel fehlen (schluessel.py, Punkte 5-8)")
    with open(bild, "rb") as fh:
        r = requests.post(X_MEDIA, headers={"Authorization": oauth_kopf("POST", X_MEDIA, geheim)},
                          files={"media": (bild.name, fh, "image/png")},
                          data={"media_category": "tweet_image"}, timeout=120)
    if r.status_code >= 300:
        raise RuntimeError(f"X-Bild: {r.status_code} {r.text[:200]}")
    j = r.json()
    media_id = (j.get("data") or {}).get("id") or j.get("media_id_string")
    r = requests.post(X_TWEET, headers={"Authorization": oauth_kopf("POST", X_TWEET, geheim)},
                      json={"text": text[:280], "media": {"media_ids": [str(media_id)]}}, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"X-Post: {r.status_code} {r.text[:200]}")
    return f"https://x.com/i/web/status/{r.json()['data']['id']}"


POSTER = {"telegram": telegram_kanal, "x": x_posten}
