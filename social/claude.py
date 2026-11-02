"""Gemeinsamer Aufruf der Claude-API mit verlaesslicher JSON-Antwort.

Fehler 02.11.2026: Kommentar-Assistent und Coin-Check scheiterten taeglich mit „Expecting value“ /
„Expecting ',' delimiter“ – die Antwort war abgeschnitten (max_tokens zu knapp) oder ohne JSON.
Darum: grosszuegiges Token-Budget, bei Abbruch einmal mit doppeltem Budget neu, Code-Zaeune entfernen,
nur das erste vollstaendige JSON-Objekt lesen, und bei Fehler den Grund (stop_reason, Anfang der Antwort) nennen.
"""
from __future__ import annotations

import json

import requests

API = "https://api.anthropic.com/v1/messages"


class ClaudeFehler(RuntimeError):
    pass


def json_aus_text(txt: str) -> dict:
    t = txt.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    start = t.find("{")
    if start < 0:
        raise ClaudeFehler(f"keine JSON-Antwort: {txt[:120]!r}")
    obj, _ = json.JSONDecoder().raw_decode(t[start:])
    return obj


def json_antwort(system: str, inhalt: str, cfg: dict, api_key: str, max_tokens: int = 3000,
                 post=requests.post, timeout: int = 120) -> dict:
    letzter = ""
    for budget in (max_tokens, max_tokens * 2):
        r = post(API, headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                               "content-type": "application/json"},
                 json={"model": cfg["text"]["modell"], "max_tokens": budget, "system": system,
                       "messages": [{"role": "user", "content": inhalt}]}, timeout=timeout)
        r.raise_for_status()
        j = r.json()
        txt = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type", "text") == "text")
        try:
            return json_aus_text(txt)
        except (ValueError, ClaudeFehler) as e:
            letzter = f"{e} (stop_reason={j.get('stop_reason')}, {len(txt)} Zeichen)"
            if j.get("stop_reason") != "max_tokens":
                break
    raise ClaudeFehler(letzter)
