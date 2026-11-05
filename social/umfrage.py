"""Umfrage unter Hot Topics (Wunsch Tobias 05.11.2026): Abstimmen braucht nur einen Tipp und bringt Klicks.

Liegt im Beitragsordner `umfrage.json` ({"frage": "Deal or more strikes?", "optionen": ["Deal", "More strikes"],
"stunden": 24}), dann
- Telegram: direkt nach dem Beitrag eine Umfrage im Kanal (sendPoll, anonym),
- X: als Antwort auf den eigenen Post (X erlaubt keine Umfrage zusammen mit einem Bild).
Fehler der Umfrage stoppen nie den eigentlichen Beitrag.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

TG = "https://api.telegram.org/bot{token}/{methode}"


def laden(ordner: Path) -> dict | None:
    p = ordner / "umfrage.json"
    if not p.exists():
        return None
    u = json.loads(p.read_text(encoding="utf-8"))
    opt = [str(o)[:25] for o in u.get("optionen", [])][:4]   # X: hoechstens 4 Optionen je 25 Zeichen
    if not u.get("frage") or len(opt) < 2:
        return None
    return {"frage": str(u["frage"])[:280], "optionen": opt, "stunden": int(u.get("stunden", 24))}


def telegram(geheim: dict, u: dict, post=requests.post) -> str:
    j = post(TG.format(token=geheim["telegram_token"], methode="sendPoll"),
             data={"chat_id": geheim["telegram_kanal"], "question": u["frage"][:300],
                   "options": json.dumps(u["optionen"]), "is_anonymous": "true"}, timeout=30).json()
    if not j.get("ok"):
        raise RuntimeError(j.get("description", "Telegram-Umfrage abgelehnt"))
    return f"https://t.me/{str(geheim['telegram_kanal']).lstrip('@')}/{j['result']['message_id']}"


def x(geheim: dict, u: dict, antwort_auf_link: str, post=requests.post) -> str:
    from .kanaele import X_TWEET, oauth_kopf
    tweet_id = antwort_auf_link.rstrip("/").split("/")[-1]
    r = post(X_TWEET, headers={"Authorization": oauth_kopf("POST", X_TWEET, geheim)},
             json={"text": u["frage"], "reply": {"in_reply_to_tweet_id": tweet_id},
                   "poll": {"options": u["optionen"], "duration_minutes": max(5, min(10080, u["stunden"] * 60))}},
             timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"X-Umfrage: {r.status_code} {r.text[:200]}")
    return f"https://x.com/i/web/status/{r.json()['data']['id']}"
