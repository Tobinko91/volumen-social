"""Folge-Liste (Wunsch Tobias 31.10.2026): passende Konten finden und mit einem Knopfdruck folgen.

- X: ueber die offizielle Schnittstelle (POST /2/users/:id/following). Gezielt und in kleiner Zahl (X verbietet
  nur massenhaftes, wahlloses Folgen). Tobias loest es mit EINEM Knopf im Redaktions-Bot aus – keine Automatik.
  Kosten (Pay-per-use, Stand 31.10.2026): ca. 0,01 $ je Nachschlagen + 0,015 $ je Folgen.
- Instagram/TikTok/YouTube: es gibt keine Schnittstelle zum Folgen, Browser-Fernsteuerung ist dort verboten
  (Sperrgefahr) -> nur eine kurze Liste mit direkten Links, Tobias tippt selbst.
Die Konten stehen in inhalte/folgen.yaml (pflegt der Redaktions-Chat). Erledigtes merkt sich folgen_stand.json.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import time
from pathlib import Path

import requests
import yaml

HIER = Path(__file__).resolve().parent.parent
X_API = "https://api.x.com/2"
LINKS = {"x": "https://x.com/{n}", "instagram": "https://www.instagram.com/{n}/",
         "tiktok": "https://www.tiktok.com/@{n}", "youtube": "https://www.youtube.com/@{n}"}
NAMEN = {"x": "X", "instagram": "Instagram", "tiktok": "TikTok", "youtube": "YouTube"}


class FolgenFehler(RuntimeError):
    pass


def liste(datei: Path | None = None) -> list[dict]:
    d = yaml.safe_load((datei or HIER / "inhalte" / "folgen.yaml").read_text(encoding="utf-8")) or []
    return [k for k in d if k.get("plattform") in LINKS and k.get("name")]


def _schluessel(k: dict) -> str:
    return f"{k['plattform']}:{k['name'].lower()}"


def stand_laden(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {"erledigt": {}, "heute": {}}


def stand_speichern(p: Path, s: dict) -> None:
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1))


def _frei(k: dict, stand: dict, heute_d: str | None, sperr_tage: int) -> bool:
    """06.11.2026 Tobias: keine Wiederholungen. Ein Konto erscheint erst wieder, wenn es sperr_tage nicht gezeigt wurde."""
    zuletzt = stand.get("gezeigt", {}).get(_schluessel(k))
    if not (zuletzt and heute_d and sperr_tage):
        return True
    return (dt.date.fromisoformat(heute_d) - dt.date.fromisoformat(zuletzt)).days >= sperr_tage


def auswahl(konten: list[dict], stand: dict, n_x: int = 10, n_andere: int = 5,
            je_plattform: dict | None = None, heute_d: str | None = None, sperr_tage: int = 0) -> dict:
    """Naechste noch nicht erledigte Konten: bis zu n_x auf X; die anderen Plattformen entweder zusammen bis n_andere
    oder (je_plattform, seit 02.11.2026: Tobias will Instagram- und TikTok-Follower) je Plattform eine eigene Zahl."""
    offen = [k for k in konten if _schluessel(k) not in stand.get("erledigt", {}) and _frei(k, stand, heute_d, sperr_tage)]
    x = [k for k in offen if k["plattform"] == "x"][:n_x]
    if je_plattform:
        # Je Plattform zuerst neue Konten (folgen + kommentieren), Rest auffuellen mit Konten, denen wir schon
        # folgen (nur kommentieren), am laengsten nicht gezeigt zuerst (Wunsch Tobias 03.11.2026: 10 je Plattform)
        andere, gezeigt = [], stand.get("gezeigt", {})
        for pl, n in je_plattform.items():
            neu = [k for k in offen if k["plattform"] == pl][:int(n)]
            alt = sorted((k for k in konten if k["plattform"] == pl and k not in offen
                          and _schluessel(k) in stand.get("erledigt", {}) and _frei(k, stand, heute_d, sperr_tage)),
                         key=lambda k: gezeigt.get(_schluessel(k), ""))[:max(0, int(n) - len(neu))]
            andere += neu + [dict(k, schon=True) for k in alt]
    else:
        andere = [k for k in offen if k["plattform"] != "x"][:n_andere]
    return {"x": x, "andere": andere}


KOMMENTAR_SYSTEM = """You write short comments for WhaleSqueeze (crypto data account) that the editor pastes under the
LATEST post of big crypto creators on Instagram, TikTok and YouTube. Goal: replies and likes, a real conversation
(Tobias 03.11.2026: dry statistics get ignored). You cannot see their latest post, but this week it is very likely
about what moves the market right now (current_events).

How a good comment looks:
- Short, warm compliment that fits a market/crypto post ("Great breakdown", "Love that you covered this"),
  then ONE open question to the creator about the current topic.
  Example: "Love that you're covering this. With the midterms tonight, how do you think BTC reacts if the Senate flips?"
- 1 to 2 short sentences, max 200 characters, natural plain English, no hashtags, at most one emoji.
- Numbers only if they come from current_events or our_data and make the question stronger; never invent numbers.
- No links, no "follow us", no price targets, no buy/sell calls, no own predictions (asking for THEIR view is fine).
- Every comment clearly different (different compliment, different angle of the question).
Reply with JSON only: {"kommentare": [{"text": "<comment>", "deutsch": "<short German translation>"}]}"""


def kommentare_schreiben(n: int, fakten: dict, cfg: dict, api_key: str, post=requests.post) -> list[dict]:
    """n verschiedene Kommentare: Lob + Frage zum aktuellen Anlass (Instagram/TikTok/YouTube haben keine Schnittstelle
    zum Lesen fremder Posts). Jede Zahl wird geprueft, Fehlerhafte fliegen raus."""
    from . import claude, pruefung
    if not (n and api_key):
        return []
    d = claude.json_antwort(KOMMENTAR_SYSTEM, json.dumps({"our_data": fakten, "anzahl": n + 2}, ensure_ascii=False),
                            cfg, api_key, 2000, post=post)
    out, gesehen = [], set()
    for k in d.get("kommentare", []):
        t = (k.get("text") or "").strip()
        if not t or t.lower() in gesehen or len(t) > 260 or "http" in t.lower() or "@" in t:
            continue
        if pruefung.pruefen([t], {"fakten": fakten, "szenen": [0]}, cfg, set()):
            continue
        gesehen.add(t.lower())
        out.append({"text": t, "deutsch": k.get("deutsch", "")})
        if len(out) >= n:
            break
    return out


YT_API = "https://www.googleapis.com/youtube/v3"


def youtube_neuestes(handle: str, key: str, get=requests.get, max_tage: float = 7, jetzt: float | None = None) -> dict | None:
    """Neuestes Video eines YouTube-Kanals (Wunsch Tobias 03.11.2026: Kommentar passend zum Video).
    YouTube Data API mit einfachem Schluessel (2 Einheiten von 10.000 am Tag). None, wenn nichts Frisches da ist."""
    import datetime as _dt
    j = get(f"{YT_API}/channels", params={"part": "contentDetails", "forHandle": f"@{handle}", "key": key},
            timeout=20).json()
    items = j.get("items") or []
    if not items:
        return None
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    j = get(f"{YT_API}/playlistItems", params={"part": "snippet", "playlistId": uploads, "maxResults": 1, "key": key},
            timeout=20).json()
    items = j.get("items") or []
    if not items:
        return None
    sn = items[0]["snippet"]
    zeit = _dt.datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")).timestamp()
    if (jetzt or time.time()) - zeit > max_tage * 86400:
        return None
    vid = sn["resourceId"]["videoId"]
    return {"id": vid, "konto": handle, "titel": sn.get("title", ""), "text": f"{sn.get('title', '')}\n\n"
            f"{(sn.get('description') or '')[:500]}", "link": f"https://www.youtube.com/watch?v={vid}", "zeit": zeit,
            "likes": 0, "punkte": 0}


def youtube_suche(key: str, begriffe: list[str], stunden: float = 24, n: int = 10, ausser: set | None = None,
                  get=requests.get, jetzt: float | None = None) -> list[dict]:
    """06.11.2026 Tobias: jeden Tag NEUE Videos zum Kommentieren statt immer derselben Kanaele.
    YouTube-Suche (100 Einheiten je Begriff von 10.000 am Tag): englische Videos der letzten `stunden`, meistgesehen
    zuerst, schon gezeigte (ausser) fallen weg."""
    ab = dt.datetime.fromtimestamp((jetzt or time.time()) - stunden * 3600, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ausser, gefunden = ausser or set(), {}
    for q in begriffe:
        j = get(f"{YT_API}/search", params={"part": "snippet", "q": q, "type": "video", "order": "viewCount",
                                            "publishedAfter": ab, "relevanceLanguage": "en", "maxResults": 15,
                                            "key": key}, timeout=20).json()
        for it in j.get("items") or []:
            vid = (it.get("id") or {}).get("videoId")
            sn = it.get("snippet") or {}
            if not vid or vid in ausser or vid in gefunden:
                continue
            gefunden[vid] = {"id": vid, "konto": sn.get("channelTitle", ""), "titel": html.unescape(sn.get("title", "")),
                             "text": html.unescape(f"{sn.get('title', '')}\n\n{(sn.get('description') or '')[:400]}"),
                             "link": f"https://www.youtube.com/watch?v={vid}", "likes": 0, "punkte": 0, "aufrufe": 0}
    if gefunden:   # Aufrufe fuer die Reihenfolge (1 Einheit je 50 Videos)
        try:
            j = get(f"{YT_API}/videos", params={"part": "statistics", "id": ",".join(list(gefunden)[:50]), "key": key},
                    timeout=20).json()
            for it in j.get("items") or []:
                if it.get("id") in gefunden:
                    gefunden[it["id"]]["aufrufe"] = int((it.get("statistics") or {}).get("viewCount") or 0)
        except Exception:
            pass
    kanaele, out = set(), []
    for v in sorted(gefunden.values(), key=lambda v: -v["aufrufe"]):
        if v["konto"] in kanaele:   # je Kanal nur ein Video, damit die Liste abwechslungsreich ist
            continue
        kanaele.add(v["konto"])
        out.append(v)
    return out[:n]


def begriffe_heute(alle: list[str], datum: str, n: int = 2) -> list[str]:
    """Taeglich wechselnde Suchbegriffe (gleicher Tag = gleiche Begriffe)."""
    if not alle:
        return []
    start = dt.date.fromisoformat(datum).toordinal() * n % len(alle)
    return [alle[(start + i) % len(alle)] for i in range(min(n, len(alle)))]


def suchlinks(begriffe: list[str]) -> list[tuple[str, str, str]]:
    """TikTok/Instagram haben keine Schnittstelle fuer fremde Posts -> Links auf die Suche: zeigen jeden Tag frische Posts.
    Rueckgabe: (Plattform, Begriff, Link)."""
    from urllib.parse import quote
    out = []
    for b in begriffe:
        out.append(("TikTok", b, f"https://www.tiktok.com/search/video?q={quote(b)}"))
    for b in begriffe:
        tag = "".join(ch for ch in b.lower() if ch.isalnum())
        out.append(("Instagram", b, f"https://www.instagram.com/explore/tags/{tag}/"))
    return out


def nachricht(a: dict, datum: str, kommentare: list[dict] | None = None) -> tuple[str, dict | None]:
    """Text (HTML) + Knoepfe fuer den Redaktions-Bot. kommentare: je Instagram/TikTok/YouTube-Konto einer zum Kopieren."""
    e = html.escape
    kommentare = list(kommentare or [])
    z = [f"👥 <b>Folge-Liste {datum}</b>", ""]
    nr = 0   # Nummern fuer die Knoepfe „✅ kommentiert“ (06.11.2026)
    if a["x"]:
        z.append(f"<b>X</b> – ein Tipp auf den Knopf, dann folgt @whalesqueeze allen {len(a['x'])}:")
        z += [f"• <a href=\"{LINKS['x'].format(n=k['name'])}\">@{e(k['name'])}</a> – {e(k.get('warum', ''))}"
              for k in a["x"]]
        z.append("")
    if a["andere"]:
        z.append("<b>Instagram / TikTok / YouTube</b> – selbst antippen, folgen und unter den neuesten Markt-Post "
                 "kommentieren (Kommentar antippen = kopiert):")
        for k in a["andere"]:
            nr += 1
            k["nr"] = nr
            z.append(f"<b>{nr}.</b> {NAMEN[k['plattform']]}: <a href=\"{LINKS[k['plattform']].format(n=k['name'])}\">"
                     f"{e(k['name'])}</a> – {e(k.get('warum', ''))}" + (" · <i>folgst du schon, nur kommentieren</i>"
                                                                         if k.get("schon") else ""))
            if k.get("video") and k.get("kommentar"):   # YouTube: Kommentar passend zum neuesten Video
                z.append(f"  🎬 Neuestes Video: <a href=\"{e(k['video']['link'])}\">{e(k['video']['titel'][:90])}</a>")
                z.append(f"<code>{e(k['kommentar'])}</code>")
            elif kommentare:
                z.append(f"<code>{e(kommentare.pop(0)['text'])}</code>")
        if kommentare:
            z.append("<i>Passt der neueste Post nicht zum Markt (Meme, Werbung), Kommentar weglassen. "
                     "Jeden Text nur einmal verwenden.</i>")
        z.append("")
    if a.get("videos"):
        z.append("<b>🎬 YouTube – frische Videos der letzten 24 Std.</b> (jeden Tag neue, Kommentar antippen = kopiert):")
        for v in a["videos"]:
            nr += 1
            v["nr"] = nr
            z.append(f"<b>{nr}.</b> <a href=\"{e(v['link'])}\">{e(v['titel'][:90])}</a> – {e(v['konto'])}"
                     + (f" · {v['aufrufe']:,} Aufrufe".replace(",", ".") if v.get("aufrufe") else ""))
            if v.get("kommentar"):
                z.append(f"<code>{e(v['kommentar'])}</code>")
        z.append("")
    if a.get("suche"):
        z.append("<b>🔎 Frische Posts auf TikTok und Instagram</b> – Link öffnen, einen der neuesten Posts wählen "
                 "(höchstens 1 Tag alt), Kommentar von oben passend zum Post anpassen:")
        z += [f"• {pl}: <a href=\"{e(link)}\">{e(b)}</a>" for pl, b, link in a["suche"]]
        z.append("")
    if not (a["x"] or a["andere"] or a.get("videos")):
        return "👥 Folge-Liste: alle Konten erledigt. Der Redaktions-Chat ergänzt neue in inhalte/folgen.yaml.", None
    z.append("Danach kommentieren: in der ersten Stunde nach einem Post, eigene Zahl, kein Link.")
    if nr:
        z.append("Nach dem Kommentieren „✅ Nummer“ tippen, dann sehen wir, welche Konten Follower bringen.")
    reihe = []
    if a["x"]:
        reihe.append({"text": f"✅ X: allen {len(a['x'])} folgen", "callback_data": f"f|x|{datum}"})
    if a["andere"]:
        reihe.append({"text": "☑️ Andere erledigt", "callback_data": f"f|ok|{datum}"})
    return "\n".join(z), {"inline_keyboard": [reihe]}


# ---------------------------------------------------------------- X

def _x(methode: str, url: str, geheim: dict, params: dict | None = None, body: dict | None = None,
       anfrage=requests.request) -> dict:
    from . import kanaele
    voll = url + ("?" + "&".join(f"{kanaele._q(k)}={kanaele._q(v)}" for k, v in sorted(params.items()))
                  if params else "")
    r = anfrage(methode, voll, json=body, timeout=30,
                headers={"Authorization": kanaele.oauth_kopf(methode, url, geheim, params)})
    j = r.json() if r.content else {}
    if r.status_code >= 300:
        raise FolgenFehler(f"{r.status_code} {j.get('title') or j.get('detail') or r.text[:150]}")
    return j


def x_folgen(geheim: dict, namen: list[str], stand: dict, anfrage=requests.request, warten=time.sleep) -> list[str]:
    """Folgt den X-Konten. Rueckgabe: Zeilen fuer Tobias. Eigene ID wird gemerkt (spart Abrufe)."""
    from . import kanaele
    if not kanaele.verfuegbar(geheim)["x"]:
        raise FolgenFehler("X-Schlüssel fehlen (schluessel.py, Punkte 5-8)")
    if not stand.get("x_eigene_id"):
        stand["x_eigene_id"] = _x("GET", f"{X_API}/users/me", geheim, anfrage=anfrage)["data"]["id"]
    j = _x("GET", f"{X_API}/users/by", geheim, {"usernames": ",".join(namen[:100])}, anfrage=anfrage)
    ids = {u["username"].lower(): u["id"] for u in j.get("data") or []}
    out = []
    for i, n in enumerate(namen):
        uid = ids.get(n.lower())
        if not uid:
            out.append(f"⚠️ @{n}: nicht gefunden (Name falsch oder Konto gesperrt)")
            stand.setdefault("erledigt", {})[f"x:{n.lower()}"] = "nicht gefunden"
            continue
        try:
            r = _x("POST", f"{X_API}/users/{stand['x_eigene_id']}/following", geheim,
                   body={"target_user_id": uid}, anfrage=anfrage)
            d = r.get("data") or {}
            out.append(f"✅ @{n}" + (" (Anfrage gestellt, privates Konto)" if d.get("pending_follow") else ""))
            stand.setdefault("erledigt", {})[f"x:{n.lower()}"] = int(time.time())
        except FolgenFehler as e:
            out.append(f"❌ @{n}: {e}")
            if str(e).startswith("429"):   # Limit erreicht: Rest morgen
                out.append("X-Limit erreicht, der Rest kommt morgen wieder auf die Liste.")
                break
        if i < len(namen) - 1:
            warten(2)   # ruhig nacheinander, nicht alle in einer Sekunde
    return out


def heute(jetzt: float | None = None) -> str:
    return dt.datetime.fromtimestamp(jetzt or time.time()).strftime("%Y-%m-%d")
