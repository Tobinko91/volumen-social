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

SYSTEM = """You write reply comments on X for WhaleSqueeze, a factual crypto data account (on-chain whale data,
small-cap market breadth). For each post you get the post text and our own current data.

Rules:
- 1 to 3 short sentences, calm and factual, plain English, no emojis, no hashtags.
- Add real value: include exactly one concrete number from OUR DATA (preferred) or from the post itself.
  Never invent numbers, never calculate new ones.
- No links, no self-promotion ("follow us", "check our"), no price targets, no buy/sell calls, no predictions, no hype.
- Relate our number to the post's topic. If our data does not fit the post, comment with a factual question or
  observation using a number from the post.
- If the post is about politics, scandals, tragedies or anything not about markets, set "skip": true.
- Every comment must be different. Ending with a short open question is welcome when it fits.

Reply with JSON only: {"kommentare": [{"id": "<post id>", "skip": false, "text": "<comment>",
"deutsch": "<short German translation for the editor>"}]}"""


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
    r = post("https://api.anthropic.com/v1/messages",
             headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
             json={"model": cfg["text"]["modell"], "max_tokens": 1500, "system": SYSTEM,
                   "messages": [{"role": "user", "content": json.dumps(eingabe, ensure_ascii=False)}]}, timeout=90)
    r.raise_for_status()
    txt = "".join(b.get("text", "") for b in r.json().get("content", []))
    d = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
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
