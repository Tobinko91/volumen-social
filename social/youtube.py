"""YouTube Shorts (Punkt A, Wunsch Tobias 01.11.2026): 9:16-Videos ueber die YouTube Data API hochladen.

Wichtig (Stand 2026): Apps ohne Google-Pruefung („audit“) duerfen nur PRIVAT hochladen. Darum:
- Bis zur Pruefung: config youtube.sichtbarkeit = private -> Tobias stellt das Video in der YouTube-Studio-App mit
  einem Tipp auf „Oeffentlich“. Pruefungsantrag: Formular „YouTube API Services – Audit and Quota Extension“.
- Danach: sichtbarkeit = public.
Ein Short erkennt YouTube an 9:16 und hoechstens 3 Minuten; „#Shorts“ im Titel hilft zusaetzlich.

Zugang: Google-Cloud-Projekt mit „YouTube Data API v3“, OAuth-Client „Webanwendung“,
Weiterleitung https://whalesqueeze.com/youtube/ ; einmalig tools/youtube_verbinden.py.
Den OAuth-Zustimmungsbildschirm auf „In Produktion“ stellen: im Modus „Test“ laeuft der Zugang nach 7 Tagen ab.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
REDIRECT = "https://whalesqueeze.com/youtube/"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
TITEL_MAX = 100


class YouTubeFehler(RuntimeError):
    pass


def login_link(client_id: str, state: str) -> str:
    return AUTH + "?" + urlencode({"client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
                                   "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state})


def code_aus_adresse(adresse: str, state: str) -> str:
    q = parse_qs(urlparse(adresse.strip()).query)
    if q.get("error"):
        raise YouTubeFehler(f"Google meldet: {q['error'][0]}")
    if (q.get("state") or [""])[0] != state:
        raise YouTubeFehler("Die Adresse passt nicht zu diesem Login (state). Bitte neu starten.")
    if not q.get("code"):
        raise YouTubeFehler("In der Adresse steht kein code=…")
    return q["code"][0]


def _token(daten: dict, post=requests.post) -> dict:
    r = post(TOKEN, data=daten, timeout=30)
    j = r.json() if r.content else {}
    if r.status_code >= 300 or "access_token" not in j:
        raise YouTubeFehler(j.get("error_description") or j.get("error") or r.text[:200])
    out = {"youtube_access_token": j["access_token"], "youtube_bis": int(time.time()) + int(j.get("expires_in", 3600))}
    if j.get("refresh_token"):
        out["youtube_refresh_token"] = j["refresh_token"]
    return out


def code_tauschen(geheim: dict, code: str, post=requests.post) -> dict:
    return _token({"client_id": geheim["youtube_client_id"], "client_secret": geheim["youtube_client_secret"],
                   "code": code, "grant_type": "authorization_code", "redirect_uri": REDIRECT}, post)


def gueltiger_token(geheim: dict, post=requests.post, sichern=None) -> str:
    if (geheim.get("youtube_bis") or 0) - time.time() < 120:
        neu = _token({"client_id": geheim["youtube_client_id"], "client_secret": geheim["youtube_client_secret"],
                      "refresh_token": geheim["youtube_refresh_token"], "grant_type": "refresh_token"}, post)
        from . import tiktok
        (sichern or tiktok.speichern)(geheim, neu)
    return geheim["youtube_access_token"]


def titel_und_text(tg_text: str, lang: str = "en") -> tuple[str, str]:
    """Titel (max. 100, mit #Shorts) und Beschreibung aus dem Telegram-Text."""
    from . import tiktok
    titel, text = tiktok.titel_und_text(tg_text, lang)
    zusatz = " #Shorts"
    titel = titel.replace("<", "").replace(">", "")
    return titel[:TITEL_MAX - len(zusatz)].rstrip() + zusatz, text.replace("<", "").replace(">", "")[:4900]


def hochladen(geheim: dict, video: Path, tg_text: str, sichtbarkeit: str = "private", lang: str = "en",
              post=requests.post, put=requests.put, sichern=None) -> str:
    """Resumable Upload in einem Stueck (unsere Videos sind wenige MB). Rueckgabe: Link zum Short."""
    token = gueltiger_token(geheim, post, sichern)
    titel, text = titel_und_text(tg_text, lang)
    daten = video.read_bytes()
    meta = {"snippet": {"title": titel, "description": text, "categoryId": "25",   # 25 = News & Politics
                        "defaultLanguage": lang, "defaultAudioLanguage": lang},
            "status": {"privacyStatus": sichtbarkeit, "selfDeclaredMadeForKids": False}}
    r = post(UPLOAD + "?uploadType=resumable&part=snippet,status", data=json.dumps(meta), timeout=60,
             headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                      "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(daten))})
    if r.status_code >= 300 or not r.headers.get("Location"):
        raise YouTubeFehler(f"Upload-Start: {r.status_code} {r.text[:200]}")
    r2 = put(r.headers["Location"], data=daten, timeout=600,
             headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"})
    if r2.status_code not in (200, 201):
        raise YouTubeFehler(f"Upload: {r2.status_code} {r2.text[:200]}")
    vid = r2.json()["id"]
    link = f"https://youtube.com/shorts/{vid}"
    if sichtbarkeit != "public":
        link += " (privat: in der YouTube-Studio-App auf „Öffentlich“ stellen, bis Google die App geprüft hat)"
    return link
