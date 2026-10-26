"""TikTok: Bild-Beitraege (Foto-Modus) ueber die Content Posting API.

Ablauf je Beitrag (TikTok-Doku, Stand 26.10.2026):
  1. Bild als JPEG in den oeffentlichen Ordner (wie Instagram) -> https://whalesqueeze.com/medien/<name>.jpg
     (die Domain whalesqueeze.com ist in der TikTok-App per DNS bestaetigt, PULL_FROM_URL ist erlaubt)
  2. POST /v2/post/publish/content/init/  (media_type PHOTO, source PULL_FROM_URL)
  3. POST /v2/post/publish/status/fetch/  bis TikTok das Bild geholt hat, dann Datei loeschen

Modus (config.yaml tiktok.modus):
  - "inbox"  = MEDIA_UPLOAD: der Beitrag landet als Entwurf in der TikTok-App (Benachrichtigung), Tobias
               tippt dort auf Posten und kann Musik waehlen. Geht ohne TikTok-Pruefung.
  - "direkt" = DIRECT_POST: sofort veroeffentlicht. Vor der TikTok-Pruefung nur privat (SELF_ONLY).

Zugang: einmalig mit tools/tiktok_verbinden.py (Login Kit, Redirect https://whalesqueeze.com/tiktok/).
Access-Token gilt 24 Std., Refresh-Token 365 Tage; wird hier und taeglich um 04:00 erneuert.
"""
from __future__ import annotations

import os
import secrets as _zufall
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
import yaml

API = "https://open.tiktokapis.com/v2"
AUTH = "https://www.tiktok.com/v2/auth/authorize/"
REDIRECT = "https://whalesqueeze.com/tiktok/"
SCOPES = "user.info.basic,video.upload,video.publish"
TITEL_MAX, TEXT_MAX = 90, 4000
FERTIG = {"SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"}


class TikTokFehler(RuntimeError):
    pass


def geheim_datei() -> Path:
    return Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social")) / "secrets.yaml"


def speichern(geheim: dict, neu: dict, datei: Path | None = None) -> None:
    """Neue Tokens in secrets.yaml schreiben (atomar, nur fuer den Besitzer lesbar)."""
    datei = datei or geheim_datei()
    alt = (yaml.safe_load(datei.read_text()) if datei.exists() else {}) or {}
    alt.update(neu)
    geheim.update(neu)
    tmp = datei.with_suffix(".tmp")
    tmp.write_text(yaml.safe_dump(alt, allow_unicode=True))
    os.chmod(tmp, 0o600)
    tmp.replace(datei)


# ---------------------------------------------------------------- Zugang

def login_link(client_key: str, state: str) -> str:
    return AUTH + "?" + urlencode({"client_key": client_key, "scope": SCOPES, "response_type": "code",
                                   "redirect_uri": REDIRECT, "state": state})


def code_aus_adresse(adresse: str, state: str) -> str:
    """Aus der Adresse nach dem Login (https://whalesqueeze.com/tiktok/?code=...&state=...) den Code holen."""
    q = parse_qs(urlparse(adresse.strip()).query)
    if q.get("error"):
        raise TikTokFehler(f"TikTok meldet: {q.get('error_description', q['error'])[0]}")
    if (q.get("state") or [""])[0] != state:
        raise TikTokFehler("Die Adresse passt nicht zu diesem Login (state). Bitte neu starten.")
    if not q.get("code"):
        raise TikTokFehler("In der Adresse steht kein code=…")
    return q["code"][0]


def _token(daten: dict, post=requests.post) -> dict:
    r = post(f"{API}/oauth/token/", data=daten, headers={"Content-Type": "application/x-www-form-urlencoded"},
             timeout=30)
    j = r.json() if r.content else {}
    if r.status_code >= 300 or "access_token" not in j:
        raise TikTokFehler(j.get("error_description") or j.get("error") or r.text[:200])
    jetzt = int(time.time())
    return {"tiktok_access_token": j["access_token"], "tiktok_refresh_token": j["refresh_token"],
            "tiktok_bis": jetzt + int(j.get("expires_in", 86400)),
            "tiktok_refresh_bis": jetzt + int(j.get("refresh_expires_in", 31536000)),
            "tiktok_open_id": j.get("open_id")}


def code_tauschen(geheim: dict, code: str, post=requests.post) -> dict:
    return _token({"client_key": geheim["tiktok_client_key"], "client_secret": geheim["tiktok_client_secret"],
                   "code": code, "grant_type": "authorization_code", "redirect_uri": REDIRECT}, post)


def erneuern(geheim: dict, post=requests.post) -> dict:
    return _token({"client_key": geheim["tiktok_client_key"], "client_secret": geheim["tiktok_client_secret"],
                   "grant_type": "refresh_token", "refresh_token": geheim["tiktok_refresh_token"]}, post)


def gueltiger_token(geheim: dict, post=requests.post, sichern=speichern) -> str:
    """Access-Token, bei Bedarf vorher erneuert (gilt nur 24 Std.)."""
    if (geheim.get("tiktok_bis") or 0) - time.time() < 600:
        sichern(geheim, erneuern(geheim, post))
    return geheim["tiktok_access_token"]


# ---------------------------------------------------------------- Posten

def _api(pfad: str, token: str, body: dict, post=requests.post) -> dict:
    r = post(f"{API}/{pfad}", json=body, timeout=60,
             headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    j = r.json() if r.content else {}
    fehler = (j.get("error") or {})
    if r.status_code >= 300 or (fehler.get("code") not in (None, "ok")):
        raise TikTokFehler(f"{pfad.split('/')[-2] or pfad}: {fehler.get('code')} {fehler.get('message', '')}".strip())
    return j.get("data") or {}


def titel_und_text(tg_text: str, lang: str = "en") -> tuple[str, str]:
    """Titel (max. 90) und Beschreibung (max. 4000) aus dem Telegram-Text; Links sind auf TikTok nicht klickbar."""
    import html
    import re
    zeilen = []
    for z in tg_text.splitlines():
        if z.startswith("🔗") or ("whalesqueeze.com/" in z and "utm_" in z):
            zeilen.append("🔗 More data: link in bio" if lang == "en" else "🔗 Mehr Daten: Link im Profil")
            continue
        zeilen.append(html.unescape(re.sub(r"<[^>]+>", "", z)))
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(zeilen)).strip()
    titel = text.splitlines()[0] if text else "WhaleSqueeze"
    tags = "#crypto #bitcoin #altcoins #cryptonews #whalesqueeze" if lang == "en" else \
        "#krypto #bitcoin #altcoins #whalesqueeze"
    return titel[:TITEL_MAX], (text[:TEXT_MAX - len(tags) - 2].rstrip() + "\n\n" + tags)


def foto_posten(geheim: dict, bild_url: str, tg_text: str, modus: str = "inbox", lang: str = "en",
                post=requests.post, warten=time.sleep, sichern=speichern) -> str:
    """Bild-Beitrag anlegen. Rueckgabe: Meldung fuer Tobias."""
    token = gueltiger_token(geheim, post, sichern)
    titel, text = titel_und_text(tg_text, lang)
    info = {"title": titel, "description": text}
    if modus == "direkt":
        optionen = _api("post/publish/creator_info/query/", token, {}, post).get("privacy_level_options") or []
        info.update({"privacy_level": "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in optionen else "SELF_ONLY",
                     "disable_comment": False, "auto_add_music": True,
                     "brand_content_toggle": False, "brand_organic_toggle": False})
    pid = _api("post/publish/content/init/", token, {
        "media_type": "PHOTO", "post_mode": "DIRECT_POST" if modus == "direkt" else "MEDIA_UPLOAD",
        "post_info": info,
        "source_info": {"source": "PULL_FROM_URL", "photo_images": [bild_url], "photo_cover_index": 0},
    }, post)["publish_id"]
    status = ""
    for _ in range(20):   # TikTok holt das Bild meist in wenigen Sekunden
        d = _api("post/publish/status/fetch/", token, {"publish_id": pid}, post)
        status = d.get("status", "")
        if status in FERTIG:
            break
        if status == "FAILED":
            raise TikTokFehler(f"TikTok konnte den Beitrag nicht anlegen ({d.get('fail_reason', 'unbekannt')})")
        warten(3)
    if status == "SEND_TO_USER_INBOX":
        return "Entwurf in der TikTok-App: Benachrichtigung öffnen → „Posten“ (Musik kannst du dort wählen)"
    if status == "PUBLISH_COMPLETE":
        privat = info.get("privacy_level") == "SELF_ONLY"
        return "veröffentlicht" + (" (nur privat, bis TikTok die App geprüft hat)" if privat else "")
    return f"angelegt, TikTok verarbeitet noch (Status {status or 'unbekannt'})"


def neuer_state() -> str:
    return _zufall.token_urlsafe(16)
