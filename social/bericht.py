"""Wochenbericht (Punkt E, Wunsch Tobias 01.11.2026): Was hat funktioniert?

Grundlage:
- protokoll.jsonl (dauerhaft, schreibt freigabe.py bei jedem Posten/Verwerfen): wann, welches Format, welcher Kanal, Link.
- Zahlen der Plattformen:
  - X: Aufrufe, Likes, Reposts, Antworten je Post (GET /2/tweets, public_metrics) + Follower.
  - Instagram: Aufrufe, Reichweite, Speicherungen, Teilungen je Beitrag (Insights) + Follower.
  - Telegram: Abonnenten (Aufrufe je Beitrag liefert die Bot-Schnittstelle nicht).
  - TikTok: erst mit dem Zusatz-Zugang user.info.stats (nach der App-Pruefung).
Ergebnis: Telegram-Nachricht an Tobias (Deutsch) mit Followern, Zahlen je Format und einer Empfehlung.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import statistics
import time
from pathlib import Path

import requests

WOCHE = 7 * 86400


# ---------------------------------------------------------------- Protokoll

def format_aus_ordner(name: str) -> str:
    """'20261101-1430_markt_30s_video' -> 'markt_video', '20261101-1900_wal_BAT' -> 'wal',
    'chat_20261030-binance-hack' -> 'redaktion'."""
    if name.startswith("chat_"):
        return "redaktion"
    rest = re.sub(r"^\d{8}-\d{4}_", "", name)
    video = rest.endswith("_video")
    basis = rest.split("_")[0] if rest else "unbekannt"
    return basis + ("_video" if video else "")


def protokollieren(datei: Path, ordner: str, ereignis: str, kanal: str | None = None, link: str | None = None,
                   jetzt: float | None = None) -> None:
    """Eine Zeile anhaengen. ereignis: gepostet | verworfen | fehler. Bei Videos zusaetzlich Laenge und Art der
    Untertitel aus <ordner>/video_info.json (fuer die Haltequote im Wochenbericht; Ordner werden nach 3 Tagen
    geloescht, das Protokoll bleibt)."""
    datei.parent.mkdir(parents=True, exist_ok=True)
    e = {"ts": int(jetzt or time.time()), "ordner": ordner, "format": format_aus_ordner(ordner),
         "ereignis": ereignis, "kanal": kanal, "link": link}
    try:
        e["video"] = json.loads((datei.parent / Path(ordner).name / "video_info.json").read_text())
    except Exception:
        pass
    with open(datei, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")


def protokoll_laden(datei: Path, seit: float = 0) -> list[dict]:
    if not datei.exists():
        return []
    out = []
    for z in datei.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(z)
        except ValueError:
            continue
        if e.get("ts", 0) >= seit:
            out.append(e)
    return out


# ---------------------------------------------------------------- Zahlen holen

def x_zahlen(geheim: dict, links: list[str], get=requests.request) -> tuple[dict, int | None]:
    """{link: {aufrufe, likes, reposts, antworten}}, Follower. Ein Abruf fuer bis zu 100 Posts."""
    from . import kanaele
    ids = {re.search(r"/status/(\d+)", l).group(1): l for l in links if re.search(r"/status/(\d+)", l)}
    out, follower = {}, None
    if not kanaele.verfuegbar(geheim)["x"]:
        return out, follower

    def abruf(url, params):
        voll = url + "?" + "&".join(f"{kanaele._q(k)}={kanaele._q(v)}" for k, v in sorted(params.items()))
        r = get("GET", voll, headers={"Authorization": kanaele.oauth_kopf("GET", url, geheim, params)}, timeout=30)
        return r.json() if r.status_code < 300 else {}
    if ids:
        j = abruf("https://api.x.com/2/tweets", {"ids": ",".join(list(ids)[:100]), "tweet.fields": "public_metrics"})
        for t in j.get("data") or []:
            m = t.get("public_metrics") or {}
            out[ids[t["id"]]] = {"aufrufe": m.get("impression_count"), "likes": m.get("like_count"),
                                 "reposts": m.get("retweet_count"), "antworten": m.get("reply_count")}
    j = abruf("https://api.x.com/2/users/me", {"user.fields": "public_metrics"})
    follower = ((j.get("data") or {}).get("public_metrics") or {}).get("followers_count")
    return out, follower


def instagram_zahlen(geheim: dict, ig=None) -> tuple[dict, int | None]:
    """{permalink: {aufrufe, reichweite, gespeichert, geteilt, likes}}, Follower."""
    from . import kanaele
    if not kanaele.verfuegbar(geheim)["instagram"]:
        return {}, None
    ig = ig or kanaele._ig
    tok = geheim["instagram_token"]
    me = ig("GET", "me", tok, fields="user_id,followers_count")
    uid = geheim.get("instagram_user_id") or me.get("user_id")
    medien = ig("GET", f"{uid}/media", tok, fields="id,permalink,timestamp,like_count,media_product_type",
                limit="50").get("data") or []
    out = {}
    for m in medien:
        try:
            ins = ig("GET", f"{m['id']}/insights", tok, metric="views,reach,saved,shares").get("data") or []
        except Exception:
            ins = []
        w = {i["name"]: (i.get("values") or [{}])[0].get("value", i.get("total_value", {}).get("value")) for i in ins}
        schnitt = None
        if m.get("media_product_type") == "REELS":   # eigene Abfrage: bei Bildern wuerde die Metrik alles kippen
            try:
                r = ig("GET", f"{m['id']}/insights", tok, metric="ig_reels_avg_watch_time").get("data") or []
                schnitt = (r[0].get("values") or [{}])[0].get("value", (r[0].get("total_value") or {}).get("value"))
            except Exception:
                pass
        out[m.get("permalink")] = {"aufrufe": w.get("views"), "reichweite": w.get("reach"),
                                   "gespeichert": w.get("saved"), "geteilt": w.get("shares"),
                                   "likes": m.get("like_count"), "schnitt_ms": schnitt}
    return out, me.get("followers_count")


def telegram_abonnenten(geheim: dict, post=requests.post) -> int | None:
    if not (geheim.get("telegram_token") and geheim.get("telegram_kanal")):
        return None
    try:
        j = post(f"https://api.telegram.org/bot{geheim['telegram_token']}/getChatMemberCount",
                 data={"chat_id": geheim["telegram_kanal"]}, timeout=30).json()
        return j.get("result") if j.get("ok") else None
    except Exception:
        return None


# ---------------------------------------------------------------- Auswerten

NAMEN = {"markt": "Markt (Bild)", "markt_video": "Markt (Video)", "news": "News", "coincheck": "Coin-Check",
         "wal": "Wal des Tages", "wal_video": "Wal (Video)", "wissen": "Lernen", "redaktion": "Redaktion (Hand)",
         "karussell": "Wal-Karussell", "wissen_video": "Lernen (Video)", "termine": "Termine der Woche", "warum_video": "Why did it move? (Video)",
         "formation_video": "Formation des Tages (Video)"}


def auswerten(protokoll: list[dict], x: dict, ig: dict) -> dict:
    """Je Format: Vorschlaege gepostet/verworfen, Mittelwerte Aufrufe (X, Instagram), Speicherungen."""
    formate: dict[str, dict] = {}
    for e in protokoll:
        f = formate.setdefault(e["format"], {"gepostet": set(), "verworfen": 0, "x": [], "ig": [], "ig_saves": []})
        if e["ereignis"] == "verworfen":
            f["verworfen"] += 1
        elif e["ereignis"] == "gepostet":
            f["gepostet"].add(e["ordner"])
            if e["kanal"] == "x" and e.get("link") in x and x[e["link"]].get("aufrufe") is not None:
                f["x"].append(x[e["link"]]["aufrufe"])
            if e["kanal"] == "instagram" and e.get("link") in ig:
                z = ig[e["link"]]
                if z.get("aufrufe") is not None:
                    f["ig"].append(z["aufrufe"])
                if z.get("gespeichert") is not None:
                    f["ig_saves"].append(z["gespeichert"])
    out = {}
    for name, f in formate.items():
        out[name] = {"beitraege": len(f["gepostet"]), "verworfen": f["verworfen"],
                     "x_mittel": round(statistics.mean(f["x"])) if f["x"] else None,
                     "ig_mittel": round(statistics.mean(f["ig"])) if f["ig"] else None,
                     "ig_saves": sum(f["ig_saves"]) if f["ig_saves"] else None,
                     "reichweite": round(statistics.mean(f["x"] + f["ig"])) if (f["x"] or f["ig"]) else None}
    return out


def haltequote(protokoll: list[dict], ig: dict, nach: str = "untertitel") -> dict:
    """Instagram-Reels: Ø angesehene Zeit / Videolaenge.
    nach='untertitel': 'wort' (seit 04.11.2026) gegen 'vorher' (fester Satz-Kasten oder keine Angabe).
    nach='haken': A/B-Test des Einstiegs, 'frage' gegen 'zahl' (Videos ohne Angabe zaehlen nicht)."""
    out: dict[str, list[float]] = {"wort": [], "vorher": []} if nach == "untertitel" else {"frage": [], "zahl": []}
    for e in protokoll:
        if e.get("ereignis") != "gepostet" or e.get("kanal") != "instagram" or e.get("link") not in ig:
            continue
        info = e.get("video") or {}
        ms, dauer = ig[e["link"]].get("schnitt_ms"), info.get("dauer")
        if ms is None or not dauer:
            continue
        if nach == "untertitel":
            art = "wort" if info.get("untertitel") == "wort" else "vorher"
        else:
            art = info.get("haken")
            if art not in out:
                continue
        out[art].append(min(1.0, ms / 1000 / dauer))
    return out


NAMEN_HALTE = {"wort": "Wort-Untertitel", "vorher": "vorher", "frage": "Einstieg Frage", "zahl": "Einstieg Zahl"}


def haltequote_text(h: dict, titel: str = "Haltequote Instagram-Reels (Ø angesehen / Videolänge):") -> list[str]:
    def teil(xs):
        return f"{round(statistics.mean(xs) * 100)} % (n = {len(xs)})" if xs else "– (n = 0)"
    a, b = list(h)
    z = ["", titel, f"• {NAMEN_HALTE[a]}: {teil(h[a])}", f"• {NAMEN_HALTE[b]}: {teil(h[b])}"]
    if len(h[a]) >= 3 and len(h[b]) >= 3:
        d = round((statistics.mean(h[a]) - statistics.mean(h[b])) * 100)
        z.append(f"→ {NAMEN_HALTE[a]} {'+' if d >= 0 else ''}{d} Prozentpunkte. Ziel bei 20-Sek.-Videos: über 70 %.")
    else:
        z.append("→ Noch zu wenige Reels für einen Vergleich (je mindestens 3).")
    return z


def empfehlung(formate: dict) -> list[str]:
    """Ausbauen: hoechste mittlere Reichweite. Pruefen: niedrigste (mind. 3 Beitraege) oder oft verworfen."""
    z = []
    mit = {k: v for k, v in formate.items() if v["reichweite"] is not None and v["beitraege"] >= 2}
    if len(mit) >= 2:
        best = max(mit, key=lambda k: mit[k]["reichweite"])
        z.append(f"📈 Ausbauen: {NAMEN.get(best, best)} (Ø {mit[best]['reichweite']} Aufrufe je Beitrag). "
                 "Mehr davon, ggf. zu einer zweiten Uhrzeit.")
        schwach = [k for k in mit if mit[k]["beitraege"] >= 3 and k != best]
        if schwach:
            w = min(schwach, key=lambda k: mit[k]["reichweite"])
            z.append(f"📉 Prüfen: {NAMEN.get(w, w)} (Ø {mit[w]['reichweite']}). Neuer Einstieg/Aufbau oder seltener posten.")
    for k, v in formate.items():
        if v["verworfen"] >= 3 and v["verworfen"] >= v["beitraege"]:
            z.append(f"🗑 {NAMEN.get(k, k)}: {v['verworfen']}× verworfen, {v['beitraege']}× gepostet. "
                     "Sag mir, was nicht passt, dann ändere ich das Format.")
    if not z:
        z.append("Noch zu wenige Zahlen für eine Empfehlung. Nächste Woche wird es aussagekräftiger.")
    return z


def _zahl(n) -> str:
    return "–" if n is None else f"{n:,}".replace(",", ".")


def _diff(jetzt, vorher) -> str:
    if jetzt is None or vorher is None:
        return ""
    d = jetzt - vorher
    return f" ({'+' if d >= 0 else ''}{_zahl(d)})"


def text(formate: dict, follower: dict, follower_alt: dict, top: list[tuple[str, str, int]],
         jetzt: float | None = None, halte: dict | None = None, haken: dict | None = None) -> str:
    d = dt.datetime.fromtimestamp(jetzt or time.time())
    z = [f"📊 Wochenbericht bis {d.day}.{d.month}.{d.year}", "", "Follower (Veränderung zur Vorwoche):"]
    for k, name in (("telegram", "Telegram"), ("x", "X"), ("instagram", "Instagram"), ("tiktok", "TikTok")):
        z.append(f"• {name}: {_zahl(follower.get(k))}{_diff(follower.get(k), follower_alt.get(k))}"
                 + (" (Zahlen nach der TikTok-Prüfung)" if k == "tiktok" and follower.get(k) is None else ""))
    z += ["", "Formate (gepostet · Ø Aufrufe X · Ø Aufrufe Instagram · Speicherungen):"]
    for k, v in sorted(formate.items(), key=lambda kv: -(kv[1]["reichweite"] or -1)):
        z.append(f"• {NAMEN.get(k, k)}: {v['beitraege']} · {_zahl(v['x_mittel'])} · {_zahl(v['ig_mittel'])} · "
                 f"{_zahl(v['ig_saves'])}" + (f" · {v['verworfen']}× verworfen" if v["verworfen"] else ""))
    if top:
        z += ["", "Top-Beiträge der Woche:"]
        z += [f"{i}. {NAMEN.get(f, f)}, {_zahl(n)} Aufrufe: {l}" for i, (f, l, n) in enumerate(top[:3], 1)]
    if halte is not None:
        z += haltequote_text(halte)
    if haken is not None:
        z += haltequote_text(haken, "A/B-Test Einstieg (Instagram-Reels, Ø angesehen / Videolänge):")
    z += ["", "Empfehlung:"] + empfehlung(formate)
    return "\n".join(z)


def top_beitraege(protokoll: list[dict], x: dict, ig: dict) -> list[tuple[str, str, int]]:
    alle = []
    for e in protokoll:
        if e["ereignis"] != "gepostet" or not e.get("link"):
            continue
        n = (x.get(e["link"]) or ig.get(e["link"]) or {}).get("aufrufe")
        if n is not None:
            alle.append((e["format"], e["link"], n))
    return sorted(alle, key=lambda t: -t[2])
