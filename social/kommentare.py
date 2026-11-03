"""Kommentar-Assistent (S14 Schritt 2 / Punkt D, Wunsch Tobias 26.10. und 01.11.2026).

Zweimal am Tag: neueste Posts grosser Konten auf X (hoechstens 3 Std. alt, je Konto einer, die mit der meisten
Interaktion), je Post ein englischer Kommentar-Vorschlag mit einer echten Zahl aus unseren Bot-Daten.
Tobias postet SELBST (automatisches Kommentieren verbieten X/Instagram/TikTok -> Sperrgefahr).

Regeln fuer jeden Kommentar (influencer-zielliste, Kommentar-Regeln):
1-3 Saetze, sachlich, eine konkrete Zahl aus unseren Daten oder aus dem Post selbst, kein Link, keine Eigenwerbung,
keine Kauf-/Verkaufsaufforderung, kein Kursziel, kein Hype, nie doppelter Text.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import time

import requests

X_SUCHE = "https://api.x.com/2/tweets/search/recent"

SYSTEM = """You write reply comments on X for WhaleSqueeze, a crypto data account. Goal: start a conversation with the
author and their readers, so the comment gets replies and likes (Tobias 03.11.2026: dry statistics get ignored).

How a good comment looks:
- React to THIS post specifically: pick up its concrete point (name it), agree or add a short thought.
- Then ask ONE open, engaging question to the author about the post's topic. Where it fits, connect it to what moves
  the market right now (see current_events, e.g. an election tonight, a Fed decision this week).
  Example: "Great timing on this. With the midterms tonight, do you expect BTC to move more on the Senate or the House result?"
- 1 to 2 short sentences, max 220 characters, natural plain English, no hashtags, at most one emoji.
- A number is optional: only use one if it makes the comment stronger AND it comes from the post itself, our_data or
  current_events. Never invent or calculate numbers.
- No links, no self-promotion ("follow us", "check our"), no price targets, no buy/sell calls, no own predictions
  (asking the author for THEIR view is fine), no hype, no generic praise only ("great post!" alone is not enough).
- If the post is about scandals, tragedies or anything not about markets, set "skip": true.
- Every comment different.

Reply with JSON only: {"kommentare": [{"id": "<post id>", "skip": false, "text": "<comment>",
"deutsch": "<short German translation for the editor>"}]}"""


def anlaesse(jetzt=None, tage_vorher: int = 1, tage_danach: int = 2) -> list[str]:
    """Was den Markt gerade bewegt (Wunsch Tobias 03.11.2026: Fragen zu Anlaessen wie den Midterms), aus
    inhalte/termine.yaml: Termine von gestern bis uebermorgen, mit „today/tomorrow/yesterday“."""
    import datetime as _dt
    from pathlib import Path as _P
    from . import termine
    heute = (_dt.datetime.fromtimestamp(jetzt) if jetzt else _dt.datetime.now()).date()
    try:
        t = termine.laden(_P(__file__).resolve().parent.parent / "inhalte" / "termine.yaml")
    except Exception:
        return []
    out = []
    for montag in {heute - _dt.timedelta(days=heute.weekday()), heute - _dt.timedelta(days=heute.weekday() + 7)}:
        for e in termine.woche(t, montag, "en"):
            d = _dt.date.fromisoformat(e["datum"])
            diff = (d - heute).days
            if -tage_vorher <= diff <= tage_danach:
                wann = {0: "today", 1: "tomorrow", -1: "yesterday"}.get(diff, f"on {e['tag'].title()}")
                zeit = f", {e['et']} ET" if e["et"] and diff >= 0 else ""
                out.append(f"{e['titel']} {wann}{zeit}")
    return sorted(set(out))


def fakten_aus_markt(m: dict | None) -> dict:
    """Unsere Zahlen fuer Kommentare (aus daten.marktlage / markt.json)."""
    if not m:
        return {}
    f = {"window_hours": 24, "small_caps_tracked": m.get("anzahl"),
         "share_of_small_caps_up_24h_percent": m.get("anteil_plus"),
         "median_small_cap_change_24h_percent": m.get("median_24h")}
    if m.get("btc_24h") is not None:
        f["bitcoin_change_24h_percent"] = m["btc_24h"]
    if m.get("eth_24h") is not None:
        f["ether_change_24h_percent"] = m["eth_24h"]
    return {k: v for k, v in f.items() if v is not None}


def posts_holen(geheim: dict, konten: list[str], stunden: float = 3, max_posts: int = 30,
                jetzt: float | None = None, get=requests.request) -> list[dict]:
    """Eine X-Suche fuer alle Konten (spart Kosten). Rueckgabe: je Konto der Post mit der meisten Interaktion."""
    from . import kanaele
    jetzt = jetzt or time.time()
    start = dt.datetime.fromtimestamp(jetzt - stunden * 3600, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"query": "(" + " OR ".join(f"from:{k}" for k in konten) + ") -is:retweet -is:reply",
              "max_results": str(max(10, min(100, max_posts))), "start_time": start,
              "tweet.fields": "created_at,author_id,public_metrics", "expansions": "author_id",
              "user.fields": "username"}
    url = X_SUCHE + "?" + "&".join(f"{kanaele._q(k)}={kanaele._q(v)}" for k, v in sorted(params.items()))
    r = get("GET", url, headers={"Authorization": kanaele.oauth_kopf("GET", X_SUCHE, geheim, params)}, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"X-Suche: {r.status_code} {r.text[:150]}")
    j = r.json()
    namen = {u["id"]: u["username"] for u in (j.get("includes") or {}).get("users", [])}
    beste: dict[str, dict] = {}
    for t in j.get("data") or []:
        n = namen.get(t.get("author_id"))
        if not n:
            continue
        m = t.get("public_metrics") or {}
        punkte = (m.get("like_count") or 0) + 3 * (m.get("reply_count") or 0) + 2 * (m.get("retweet_count") or 0)
        p = {"id": t["id"], "konto": n, "text": html.unescape(t.get("text", "")), "punkte": punkte,
             "likes": m.get("like_count") or 0, "zeit": t.get("created_at"),
             "link": f"https://x.com/{n}/status/{t['id']}"}
        if n not in beste or punkte > beste[n]["punkte"]:
            beste[n] = p
    return sorted(beste.values(), key=lambda p: -p["punkte"])


def schreiben(posts: list[dict], fakten: dict, cfg: dict, api_key: str, post=requests.post) -> list[dict]:
    eingabe = {"our_data": fakten, "posts": [{"id": p["id"], "account": p["konto"], "text": p["text"][:600]}
                                             for p in posts]}
    from . import claude
    d = claude.json_antwort(SYSTEM, json.dumps(eingabe, ensure_ascii=False), cfg, api_key, 3000, post=post)
    return [k for k in d.get("kommentare", []) if not k.get("skip") and k.get("text")]


def pruefen(kommentar: str, post_text: str, fakten: dict, cfg: dict, sperr: set[str]) -> list[str]:
    """Gleiche Pruefung wie bei Beitraegen: jede Zahl muss in unseren Daten oder im Post stehen; dazu Kommentar-Regeln."""
    from . import pruefung
    f = pruefung.pruefen([kommentar], {"fakten": [fakten, post_text], "szenen": [0]}, cfg, sperr)
    klein = kommentar.lower()
    if re.search(r"https?://|www\.|\.com\b", klein):
        f.append("Link im Kommentar")
    if re.search(r"\b(follow us|check (out )?our|our channel|our telegram|dm us)\b", klein):
        f.append("Eigenwerbung")
    if len(kommentar) > 280:
        f.append("zu lang für X")
    return f


def nachricht(eintraege: list[dict], jetzt: float | None = None) -> str:
    """Telegram-HTML an Tobias. <code> = beim Antippen kopiert."""
    e = html.escape
    z = ["💬 <b>Kommentar-Vorschläge</b> (am besten in der nächsten Stunde)",
         "Kommentar antippen = kopiert · Link öffnen · einfügen · posten", ""]
    for i, k in enumerate(eintraege, 1):
        z += [f"<b>{i}. @{e(k['konto'])}</b> · {k['likes']} Likes",
              f"<i>{e(k['text'][:140].strip())}{'…' if len(k['text']) > 140 else ''}</i>",
              f"🔗 {e(k['link'])}",
              f"<code>{e(k['kommentar'])}</code>",
              f"DE: {e(k.get('deutsch', ''))}", ""]
    z.append("Regeln: höchstens ca. 20 am Tag, nicht alle in einer Minute, bei Widerspruch einmal sachlich antworten.")
    return "\n".join(z)
