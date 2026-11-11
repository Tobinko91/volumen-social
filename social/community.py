"""Community-Tipp zur Formation des Tages (Entscheidung Tobias 10.11.2026).

Das Video endet nach dem Countdown, die Aufloesung kommt am naechsten Tag. Vorher zaehlt der Server die Kommentare
unter dem gestrigen Video: BUY oder SELL. Quellen: YouTube (oeffentliche Kommentare, API-Schluessel) und Instagram
(Graph-API, Token). TikTok gibt Kommentare ueber die Schnittstelle nicht heraus, X kostet je Abfrage Geld.
Unter der Mindestzahl (config formation.community_min, Standard 20) zeigen wir keine Prozentzahl.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

KAUF = re.compile(r"\b(buy|long|bull|bullish)\b|📈|🟢|🚀", re.I)
VERKAUF = re.compile(r"\b(sell|short|bear|bearish)\b|📉|🔴", re.I)
YT_API = "https://www.googleapis.com/youtube/v3/commentThreads"


def stimme(text: str) -> str | None:
    """'buy', 'sell' oder None (beides oder nichts erkannt)."""
    k, v = bool(KAUF.search(text or "")), bool(VERKAUF.search(text or ""))
    return "buy" if k and not v else "sell" if v and not k else None


def zaehlen(eintraege: list[tuple[str, str]]) -> dict:
    """eintraege = [(Autor, Text)]. Je Autor zaehlt nur der erste eindeutige Tipp."""
    gesehen, z = set(), {"buy": 0, "sell": 0}
    for autor, text in eintraege:
        s = stimme(text)
        if s and autor not in gesehen:
            gesehen.add(autor)
            z[s] += 1
    return z


def ergebnis(z: dict, minimum: int = 20) -> dict | None:
    n = z.get("buy", 0) + z.get("sell", 0)
    if n < minimum or z["buy"] == z["sell"]:
        return None
    m = "buy" if z["buy"] > z["sell"] else "sell"
    return {"n": n, "mehrheit": m, "pct": round(z[m] / n * 100)}


def youtube_id(link: str) -> str | None:
    m = re.search(r"(?:shorts/|watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})", link or "")
    return m.group(1) if m else None


def youtube(video_id: str, key: str, get=requests.get) -> list[tuple[str, str]]:
    out, token = [], None
    for _ in range(5):   # hoechstens 500 Kommentare
        p = {"part": "snippet", "videoId": video_id, "maxResults": 100, "textFormat": "plainText", "key": key}
        if token:
            p["pageToken"] = token
        j = get(YT_API, params=p, timeout=20).json()
        for it in j.get("items") or []:
            sn = ((it.get("snippet") or {}).get("topLevelComment") or {}).get("snippet") or {}
            out.append(("yt:" + str(sn.get("authorChannelId", {}).get("value") or sn.get("authorDisplayName")),
                        sn.get("textOriginal") or sn.get("textDisplay") or ""))
        token = j.get("nextPageToken")
        if not token:
            break
    return out


def instagram(permalink: str, geheim: dict, ig=None) -> list[tuple[str, str]]:
    """Reel ueber den Permalink unter den letzten 25 Beitraegen finden, dann die Kommentare holen."""
    from . import kanaele
    ig = ig or kanaele._ig
    token = geheim["instagram_token"]
    uid = geheim.get("instagram_user_id") or ig("GET", "me", token, fields="user_id")["user_id"]
    ziel = (permalink or "").rstrip("/")
    mid = next((m["id"] for m in ig("GET", f"{uid}/media", token, fields="id,permalink", limit=25).get("data") or []
                if str(m.get("permalink", "")).rstrip("/") == ziel), None)
    if not mid:
        return []
    daten = ig("GET", f"{mid}/comments", token, fields="text,username", limit=100).get("data") or []
    return [("ig:" + str(c.get("username") or c.get("id")), c.get("text") or "") for c in daten]


def holen(ordner: Path, geheim: dict, cfg: dict, get=requests.get, ig=None) -> tuple[dict | None, str]:
    """Community-Ergebnis zum Video in ordner (gepostet.json). -> (ergebnis oder None, Hinweis fuer Tobias)."""
    try:
        gepostet = json.loads((Path(ordner) / "gepostet.json").read_text())
    except Exception:
        return None, "Community: gestriges Video nicht gepostet"
    eintraege, quellen = [], []
    vid = youtube_id(str(gepostet.get("youtube", "")))
    if vid and geheim.get("youtube_api_key"):
        try:
            e = youtube(vid, geheim["youtube_api_key"], get)
            eintraege += e
            quellen.append(f"YouTube {len(e)}")
        except Exception as ex:
            quellen.append(f"YouTube Fehler {str(ex)[:40]}")
    if gepostet.get("instagram") and geheim.get("instagram_token"):
        try:
            e = instagram(str(gepostet["instagram"]), geheim, ig)
            eintraege += e
            quellen.append(f"Instagram {len(e)}")
        except Exception as ex:
            quellen.append(f"Instagram Fehler {str(ex)[:40]}")
    z = zaehlen(eintraege)
    minimum = int((cfg.get("formation") or {}).get("community_min", 20))
    erg = ergebnis(z, minimum)
    hinweis = (f"Community: {z['buy']} BUY / {z['sell']} SELL ({', '.join(quellen) or 'keine Quelle'})"
               + ("" if erg else f", unter {minimum} oder unentschieden: keine Prozentzahl im Video"))
    return erg, hinweis
