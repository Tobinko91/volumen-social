"""Veroeffentlichen auf den Kanaelen. Schluessel nur aus secrets.yaml auf dem Server.

Telegram-Kanal: der Redaktions-Bot ist Admin im Kanal und postet dort.
X: API v2 mit OAuth 1.0a (Konto-Schluessel aus dem X-Entwicklerportal).
Instagram: Instagram API mit Instagram-Login (Meta-App "WhaleSqueeze Redaktion", Entwicklungsmodus).
  Instagram holt das Bild selbst ab, darum liegt es kurz als JPEG in einem oeffentlichen Ordner
  (/opt/volumen-social/oeffentlich -> https://whalesqueeze.com/medien/, Caddy der Website) und wird danach geloescht.
TikTok: Foto-Beitrag ueber die Content Posting API (social/tiktok.py), Bild ebenfalls ueber /medien/.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import os
import re
import secrets as _zufall
import time
import urllib.parse
from pathlib import Path

import requests

TG = "https://api.telegram.org/bot{token}/{methode}"
X_MEDIA = "https://api.x.com/2/media/upload"
X_TWEET = "https://api.x.com/2/tweets"
IG = "https://graph.instagram.com/v26.0"
IG_ORDNER = Path(os.environ.get("SOCIAL_OEFFENTLICH", "/opt/volumen-social/oeffentlich"))
IG_URL = os.environ.get("SOCIAL_MEDIEN_URL", "https://whalesqueeze.com/medien/")
IG_MAX = 2200   # Zeichen in der Bildunterschrift
IG_TAGS = {"de": "#krypto #bitcoin #altcoins #kryptowährung #whalesqueeze",
           "en": "#crypto #bitcoin #altcoins #cryptonews #whalesqueeze"}


class NichtEingerichtet(Exception):
    pass


def verfuegbar(geheim: dict) -> dict[str, bool]:
    return {
        "telegram": bool(geheim.get("telegram_token") and geheim.get("telegram_kanal")),
        "x": all(geheim.get(k) for k in ("x_api_key", "x_api_secret", "x_access_token", "x_access_secret")),
        "instagram": bool(geheim.get("instagram_token")),
        "tiktok": all(geheim.get(k) for k in ("tiktok_client_key", "tiktok_client_secret", "tiktok_refresh_token")),
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


# ---------------------------------------------------------------- Instagram

def instagram_text(tg_text: str) -> str:
    """Bildunterschrift aus dem Telegram-Text: ohne HTML, Links sind auf Instagram nicht klickbar -> Hinweis aufs Profil."""
    from . import design
    lang = design.SPRACHE
    tags = IG_TAGS.get(lang, IG_TAGS["en"])
    zeilen = []
    for z in tg_text.splitlines():
        if "whalesqueeze.com/" in z and "utm_" in z or z.startswith("🔗"):
            zeilen.append("🔗 Mehr Daten: Link im Profil" if lang == "de" else "🔗 More data: link in bio")
            continue
        zeilen.append(html.unescape(re.sub(r"<[^>]+>", "", z)))
    text = "\n".join(zeilen).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return (text[:IG_MAX - len(tags) - 2].rstrip() + "\n\n" + tags)


def _ig(methode: str, pfad: str, token: str, **params) -> dict:
    params["access_token"] = token
    r = requests.request(methode, f"{IG}/{pfad}", params=params if methode == "GET" else None,
                         data=params if methode != "GET" else None, timeout=60)
    j = r.json() if r.content else {}
    if r.status_code >= 300 or "error" in j:
        msg = (j.get("error") or {}).get("message") or r.text[:200]
        raise RuntimeError(f"Instagram {pfad.split('/')[-1]}: {r.status_code} {msg}")
    return j


def instagram_posten(geheim: dict, bild: Path, text: str, warten=time.sleep, pruefen_url=None) -> str:
    """Bild + Unterschrift auf Instagram veroeffentlichen. text = Telegram-Text (wird umgewandelt)."""
    if not verfuegbar(geheim)["instagram"]:
        raise NichtEingerichtet("Instagram-Token fehlt (schluessel.py, Punkt 9)")
    from PIL import Image
    token = geheim["instagram_token"]
    IG_ORDNER.mkdir(parents=True, exist_ok=True)
    name = _zufall.token_hex(16) + ".jpg"            # nicht erratbar, nur fuer Minuten oeffentlich
    datei = IG_ORDNER / name
    Image.open(bild).convert("RGB").save(datei, "JPEG", quality=92)   # Instagram nimmt nur JPEG
    os.chmod(datei, 0o644)
    url = IG_URL + name
    try:
        r = (pruefen_url or (lambda u: requests.head(u, timeout=20).status_code))(url)
        if r != 200:
            raise NichtEingerichtet(f"Bild-Ordner {IG_URL} ist noch nicht öffentlich erreichbar ({r}). "
                                    "Das richtet der Website-Chat ein (Wunsch Nr. 13).")
        uid = geheim.get("instagram_user_id") or _ig("GET", "me", token, fields="user_id,username")["user_id"]
        c = _ig("POST", f"{uid}/media", token, image_url=url, caption=instagram_text(text))["id"]
        for _ in range(10):   # Bilder sind meist sofort fertig
            s = _ig("GET", c, token, fields="status_code").get("status_code")
            if s == "FINISHED":
                break
            if s in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram: Bild nicht verarbeitet ({s})")
            warten(3)
        mid = _ig("POST", f"{uid}/media_publish", token, creation_id=c)["id"]
        try:
            return _ig("GET", mid, token, fields="permalink").get("permalink") or f"Instagram-Beitrag {mid}"
        except Exception:
            return f"Instagram-Beitrag {mid}"
    finally:
        datei.unlink(missing_ok=True)


def instagram_token_erneuern(token: str) -> tuple[str, int]:
    """Langzeit-Token verlaengern (wieder 60 Tage gueltig). Rueckgabe (neuer Token, Sekunden gueltig)."""
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    j = r.json()
    if r.status_code >= 300 or "access_token" not in j:
        raise RuntimeError((j.get("error") or {}).get("message") or r.text[:200])
    return j["access_token"], int(j.get("expires_in", 0))


# ---------------------------------------------------------------- TikTok

def _cfg() -> dict:
    import yaml
    return yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))


def tiktok_posten(geheim: dict, bild: Path, text: str, pruefen_url=None, **kw) -> str:
    """Bild als TikTok-Foto-Beitrag (Entwurf in der App oder direkt, je nach config tiktok.modus)."""
    if not verfuegbar(geheim)["tiktok"]:
        raise NichtEingerichtet("TikTok ist noch nicht verbunden (schluessel.py 10+11, dann tiktok_verbinden.py)")
    from PIL import Image
    from . import tiktok
    cfg = _cfg()
    IG_ORDNER.mkdir(parents=True, exist_ok=True)
    datei = IG_ORDNER / (_zufall.token_hex(16) + ".jpg")
    Image.open(bild).convert("RGB").save(datei, "JPEG", quality=92)
    os.chmod(datei, 0o644)
    url = IG_URL + datei.name
    try:
        r = (pruefen_url or (lambda u: requests.head(u, timeout=20).status_code))(url)
        if r != 200:
            raise NichtEingerichtet(f"Bild-Ordner {IG_URL} ist nicht öffentlich erreichbar ({r}).")
        return tiktok.foto_posten(geheim, url, text, (cfg.get("tiktok") or {}).get("modus", "inbox"),
                                  cfg.get("sprache", "en"), **kw)
    finally:
        datei.unlink(missing_ok=True)


POSTER = {"telegram": telegram_kanal, "x": x_posten, "instagram": instagram_posten, "tiktok": tiktok_posten}
