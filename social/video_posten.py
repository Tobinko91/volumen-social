"""Videos posten (Wunsch Tobias 01.11.2026: Reels, TikTok-Videos, X-Videos statt nur Bilder).

Jede Funktion hat dieselbe Form wie die Bild-Poster in kanaele.py: (geheim, video, text) -> Link/Meldung.
text = Telegram-Text des Beitrags (wird je Kanal umgewandelt).
- Telegram-Kanal: sendVideo.
- X: Video-Upload in Teilen (v2 media upload: initialize / append / finalize / Status), dann Post.
- Instagram: Reel (media_type REELS) ueber die oeffentliche Adresse /medien/<zufall>.mp4.
- TikTok: Video per PULL_FROM_URL, im Modus inbox als Entwurf in der App (dort Sound waehlen), sonst direkt.
- YouTube: Short per Data API (bis zur Google-Pruefung privat, siehe youtube.py).
"""
from __future__ import annotations

import os
import secrets as _zufall
import time
from pathlib import Path

import requests

from . import kanaele
from .kanaele import IG_ORDNER, IG_URL, NichtEingerichtet, verfuegbar

X_UPLOAD = "https://api.x.com/2/media/upload"
TEIL = 4 * 1024 * 1024   # 4 MB je Teil


def _oeffentlich(video: Path) -> tuple[Path, str]:
    """Kopie unter nicht erratbarem Namen in den oeffentlichen Ordner (Website /medien/, Aufraeumen nach 60 Min.)."""
    IG_ORDNER.mkdir(parents=True, exist_ok=True)
    ziel = IG_ORDNER / (_zufall.token_hex(16) + ".mp4")
    ziel.write_bytes(video.read_bytes())
    os.chmod(ziel, 0o644)
    return ziel, IG_URL + ziel.name


def _erreichbar(url: str, pruefen_url=None) -> None:
    r = (pruefen_url or (lambda u: requests.head(u, timeout=20).status_code))(url)
    if r != 200:
        raise NichtEingerichtet(f"Medien-Ordner {IG_URL} ist nicht öffentlich erreichbar ({r}).")


# ---------------------------------------------------------------- Telegram

def telegram(geheim: dict, video: Path, text: str, post=requests.post) -> str:
    if not verfuegbar(geheim)["telegram"]:
        raise NichtEingerichtet("Telegram-Kanal fehlt (schluessel.py, Punkt 4)")
    from .telegram import teilen
    kopf, rest = teilen(text)
    token, kanal = geheim["telegram_token"], geheim["telegram_kanal"]
    with open(video, "rb") as fh:
        j = post(kanaele.TG.format(token=token, methode="sendVideo"),
                 data={"chat_id": kanal, "caption": kopf, "parse_mode": "HTML", "supports_streaming": "true"},
                 files={"video": (video.name, fh, "video/mp4")}, timeout=180).json()
    if not j.get("ok"):
        raise RuntimeError(j.get("description", "Telegram-Fehler"))
    if rest:
        post(kanaele.TG.format(token=token, methode="sendMessage"),
             data={"chat_id": kanal, "text": rest[:4096], "parse_mode": "HTML", "disable_web_page_preview": "true"},
             timeout=30)
    return f"https://t.me/{str(kanal).lstrip('@')}/{j['result']['message_id']}"


# ---------------------------------------------------------------- X

def _x(methode: str, url: str, geheim: dict, anfrage, params: dict | None = None, **kw) -> dict:
    voll = url + ("?" + "&".join(f"{kanaele._q(k)}={kanaele._q(v)}" for k, v in sorted(params.items()))
                  if params else "")
    r = anfrage(methode, voll, headers={"Authorization": kanaele.oauth_kopf(methode, url, geheim, params)},
                timeout=120, **kw)
    if r.status_code >= 300:
        raise RuntimeError(f"X-Video {url.rsplit('/', 1)[-1]}: {r.status_code} {r.text[:200]}")
    return (r.json() if r.content else {}).get("data") or {}


def x(geheim: dict, video: Path, text: str, anfrage=requests.request, warten=time.sleep) -> str:
    if not verfuegbar(geheim)["x"]:
        raise NichtEingerichtet("X-Schluessel fehlen (schluessel.py, Punkte 5-8)")
    daten = video.read_bytes()
    mid = _x("POST", f"{X_UPLOAD}/initialize", geheim, anfrage,
             json={"media_type": "video/mp4", "total_bytes": len(daten), "media_category": "tweet_video"})["id"]
    for i in range(0, len(daten), TEIL):
        _x("POST", f"{X_UPLOAD}/{mid}/append", geheim, anfrage,
           files={"media": ("video.mp4", daten[i:i + TEIL], "application/octet-stream")},
           data={"segment_index": str(i // TEIL)})
    info = _x("POST", f"{X_UPLOAD}/{mid}/finalize", geheim, anfrage).get("processing_info")
    for _ in range(40):   # X verarbeitet Videos einige Sekunden
        if not info or info.get("state") == "succeeded":
            break
        if info.get("state") == "failed":
            raise RuntimeError(f"X-Video nicht verarbeitet: {(info.get('error') or {}).get('message', '')}")
        warten(int(info.get("check_after_secs") or 3))
        info = _x("GET", X_UPLOAD, geheim, anfrage, {"command": "STATUS", "media_id": mid}).get("processing_info")
    r = _x("POST", kanaele.X_TWEET, geheim, anfrage, json={"text": kanaele.ein_cashtag(text)[:280], "media": {"media_ids": [str(mid)]}})
    return f"https://x.com/i/web/status/{r['id']}"


# ---------------------------------------------------------------- Instagram Reel

def instagram(geheim: dict, video: Path, text: str, warten=time.sleep, pruefen_url=None) -> str:
    if not verfuegbar(geheim)["instagram"]:
        raise NichtEingerichtet("Instagram-Token fehlt (schluessel.py, Punkt 9)")
    token = geheim["instagram_token"]
    datei, url = _oeffentlich(video)
    try:
        _erreichbar(url, pruefen_url)
        uid = geheim.get("instagram_user_id") or kanaele._ig("GET", "me", token, fields="user_id")["user_id"]
        c = kanaele._ig("POST", f"{uid}/media", token, media_type="REELS", video_url=url,
                        caption=kanaele.instagram_text(text), share_to_feed="true")["id"]
        for _ in range(36):   # Reels brauchen meist 20-90 Sekunden
            s = kanaele._ig("GET", c, token, fields="status_code").get("status_code")
            if s == "FINISHED":
                break
            if s in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram: Reel nicht verarbeitet ({s})")
            warten(10)
        else:
            raise RuntimeError("Instagram: Reel nach 6 Minuten noch nicht fertig, bitte später erneut tippen")
        mid = kanaele._ig("POST", f"{uid}/media_publish", token, creation_id=c)["id"]
        try:
            return kanaele._ig("GET", mid, token, fields="permalink").get("permalink") or f"Instagram-Reel {mid}"
        except Exception:
            return f"Instagram-Reel {mid}"
    finally:
        datei.unlink(missing_ok=True)


# ---------------------------------------------------------------- TikTok

def tiktok(geheim: dict, video: Path, text: str, pruefen_url=None, **kw) -> str:
    if not verfuegbar(geheim)["tiktok"]:
        raise NichtEingerichtet("TikTok ist noch nicht verbunden (schluessel.py 10+11, dann tiktok_verbinden.py)")
    from . import tiktok as tt
    cfg = kanaele._cfg()
    datei, url = _oeffentlich(video)
    try:
        _erreichbar(url, pruefen_url)
        return tt.video_posten(geheim, url, text, (cfg.get("tiktok") or {}).get("modus", "inbox"),
                               cfg.get("sprache", "en"), **kw)
    finally:
        datei.unlink(missing_ok=True)


# ---------------------------------------------------------------- YouTube Shorts

def youtube(geheim: dict, video: Path, text: str, **kw) -> str:
    if not verfuegbar(geheim).get("youtube"):
        raise NichtEingerichtet("YouTube ist noch nicht verbunden (schluessel.py 12+13, dann youtube_verbinden.py)")
    from . import youtube as yt
    cfg = kanaele._cfg()
    return yt.hochladen(geheim, video, text, (cfg.get("youtube") or {}).get("sichtbarkeit", "private"),
                        cfg.get("sprache", "en"), **kw)


POSTER = {"telegram": telegram, "x": x, "instagram": instagram, "tiktok": tiktok, "youtube": youtube}
