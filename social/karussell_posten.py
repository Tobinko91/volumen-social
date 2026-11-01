"""Karussell posten (S11): mehrere Bilder in einem Beitrag. Gleiche Form wie die anderen Poster:
(geheim, medium, text) -> Link/Meldung; medium = post.png (oder der Ordner) eines Vorschlags mit karussell.json.
- Telegram: Album (sendMediaGroup, bis 10 Bilder), Text unter dem ersten Bild bzw. danach.
- X: die ersten 4 Folien in einem Post (X erlaubt hoechstens 4 Bilder).
- Instagram: Karussell (Kinder-Container is_carousel_item, dann CAROUSEL), bis 10 Bilder.
- TikTok: Fotoserie (photo_images), Entwurf in der App bzw. direkt.
"""
from __future__ import annotations

import json
import os
import secrets as _zufall
import time
from pathlib import Path

import requests
from PIL import Image

from . import kanaele, karussell
from .kanaele import NichtEingerichtet, verfuegbar


def _ordner(medium: Path) -> Path:
    return medium if medium.is_dir() else medium.parent


def telegram(geheim: dict, ordner: Path, text: str, post=requests.post) -> str:
    if not verfuegbar(geheim)["telegram"]:
        raise NichtEingerichtet("Telegram-Kanal fehlt (schluessel.py, Punkt 4)")
    from .telegram import teilen
    kopf, rest = teilen(text)
    bilder = karussell.folien(_ordner(ordner))[:10]
    medien = [{"type": "photo", "media": f"attach://f{i}", **({"caption": kopf, "parse_mode": "HTML"} if i == 0 else {})}
              for i in range(len(bilder))]
    dateien = {f"f{i}": (b.name, open(b, "rb"), "image/png") for i, b in enumerate(bilder)}
    try:
        j = post(kanaele.TG.format(token=geheim["telegram_token"], methode="sendMediaGroup"),
                 data={"chat_id": geheim["telegram_kanal"], "media": json.dumps(medien)}, files=dateien,
                 timeout=180).json()
    finally:
        for _, fh, _ in dateien.values():
            fh.close()
    if not j.get("ok"):
        raise RuntimeError(j.get("description", "Telegram-Fehler"))
    if rest:
        post(kanaele.TG.format(token=geheim["telegram_token"], methode="sendMessage"),
             data={"chat_id": geheim["telegram_kanal"], "text": rest[:4096], "parse_mode": "HTML",
                   "disable_web_page_preview": "true"}, timeout=30)
    return f"https://t.me/{str(geheim['telegram_kanal']).lstrip('@')}/{j['result'][0]['message_id']}"


def x(geheim: dict, ordner: Path, text: str, post=requests.post) -> str:
    if not verfuegbar(geheim)["x"]:
        raise NichtEingerichtet("X-Schluessel fehlen (schluessel.py, Punkte 5-8)")
    ids = []
    for b in karussell.folien(_ordner(ordner))[:4]:
        with open(b, "rb") as fh:
            r = post(kanaele.X_MEDIA, headers={"Authorization": kanaele.oauth_kopf("POST", kanaele.X_MEDIA, geheim)},
                     files={"media": (b.name, fh, "image/png")}, data={"media_category": "tweet_image"}, timeout=120)
        if r.status_code >= 300:
            raise RuntimeError(f"X-Bild: {r.status_code} {r.text[:200]}")
        j = r.json()
        ids.append(str((j.get("data") or {}).get("id") or j.get("media_id_string")))
    r = post(kanaele.X_TWEET, headers={"Authorization": kanaele.oauth_kopf("POST", kanaele.X_TWEET, geheim)},
             json={"text": text[:280], "media": {"media_ids": ids}}, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"X-Post: {r.status_code} {r.text[:200]}")
    return f"https://x.com/i/web/status/{r.json()['data']['id']}"


def _oeffentlich(ordner: Path) -> list[Path]:
    """JPEG-Kopien unter Zufallsnamen in den oeffentlichen Ordner (Instagram/TikTok holen sie ab)."""
    kanaele.IG_ORDNER.mkdir(parents=True, exist_ok=True)
    out = []
    for b in karussell.folien(_ordner(ordner))[:10]:
        z = kanaele.IG_ORDNER / (_zufall.token_hex(16) + ".jpg")
        Image.open(b).convert("RGB").save(z, "JPEG", quality=92)
        os.chmod(z, 0o644)
        out.append(z)
    return out


def _pruefen(urls: list[str], pruefen_url) -> None:
    r = (pruefen_url or (lambda u: requests.head(u, timeout=20).status_code))(urls[0])
    if r != 200:
        raise NichtEingerichtet(f"Medien-Ordner nicht erreichbar ({r})")


def instagram(geheim: dict, ordner: Path, text: str, warten=time.sleep, pruefen_url=None) -> str:
    if not verfuegbar(geheim)["instagram"]:
        raise NichtEingerichtet("Instagram-Token fehlt (schluessel.py, Punkt 9)")
    token = geheim["instagram_token"]
    dateien = _oeffentlich(ordner)
    urls = [kanaele.IG_URL + d.name for d in dateien]
    try:
        _pruefen(urls, pruefen_url)
        uid = geheim.get("instagram_user_id") or kanaele._ig("GET", "me", token, fields="user_id")["user_id"]
        kinder = [kanaele._ig("POST", f"{uid}/media", token, image_url=u, is_carousel_item="true")["id"] for u in urls]
        c = kanaele._ig("POST", f"{uid}/media", token, media_type="CAROUSEL", children=",".join(kinder),
                        caption=kanaele.instagram_text(text))["id"]
        for _ in range(20):
            s = kanaele._ig("GET", c, token, fields="status_code").get("status_code")
            if s == "FINISHED":
                break
            if s in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram: Karussell nicht verarbeitet ({s})")
            warten(3)
        mid = kanaele._ig("POST", f"{uid}/media_publish", token, creation_id=c)["id"]
        try:
            return kanaele._ig("GET", mid, token, fields="permalink").get("permalink") or f"Instagram-Karussell {mid}"
        except Exception:
            return f"Instagram-Karussell {mid}"
    finally:
        for d in dateien:
            d.unlink(missing_ok=True)


def tiktok(geheim: dict, ordner: Path, text: str, pruefen_url=None, **kw) -> str:
    if not verfuegbar(geheim)["tiktok"]:
        raise NichtEingerichtet("TikTok ist noch nicht verbunden (schluessel.py 10+11, dann tiktok_verbinden.py)")
    from . import tiktok as tt
    cfg = kanaele._cfg()
    dateien = _oeffentlich(ordner)
    urls = [kanaele.IG_URL + d.name for d in dateien]
    try:
        _pruefen(urls, pruefen_url)
        return tt.foto_posten(geheim, urls, text, (cfg.get("tiktok") or {}).get("modus", "inbox"),
                              cfg.get("sprache", "en"), **kw)
    finally:
        for d in dateien:
            d.unlink(missing_ok=True)


def youtube(geheim: dict, ordner: Path, text: str) -> str:
    raise NichtEingerichtet("YouTube nimmt keine Bilderserien, nur Videos (Shorts).")


POSTER = {"telegram": telegram, "x": x, "instagram": instagram, "tiktok": tiktok, "youtube": youtube}
