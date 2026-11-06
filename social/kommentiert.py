"""Knopf „✅ kommentiert“ unter den Kommentar-Listen (Wunsch Tobias 06.11.2026).

Jede Liste (X-Kommentare 15:30/20:30, Folge-Liste 17:30) bekommt nummerierte Knoepfe „✅ 1“, „✅ 2“ … Ein Tipp merkt sich,
wo Tobias kommentiert hat. Sonntags zeigt die Kommentar-Bilanz:
- wie oft je Plattform und bei welchen Konten kommentiert wurde,
- auf X die echte Wirkung: Likes und Antworten auf unsere Antworten je Zielkonto (X-Suche from:<eigenes Konto>).
Konten mit der besten Wirkung bekommen im Kommentar-Assistenten Vorrang (stand["wert"]).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

X_SUCHE = "https://api.x.com/2/tweets/search/recent"
TAG = 86400


def laden(p: Path) -> dict:
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def speichern(p: Path, s: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1))


def lauf_merken(p: Path, lauf: str, eintraege: list[dict]) -> None:
    """eintraege: [{plattform, konto, link}] in der Reihenfolge der Nummern 1..n. Letzte 40 Laeufe bleiben."""
    s = laden(p)
    laeufe = s.setdefault("laeufe", {})
    laeufe[lauf] = [{"plattform": e["plattform"], "konto": e.get("konto", ""), "link": e.get("link", "")}
                    for e in eintraege]
    s["laeufe"] = dict(list(laeufe.items())[-40:])
    speichern(p, s)


def knoepfe(lauf: str, n: int, zusatz: list | None = None) -> dict | None:
    """Raster „✅ 1“ … „✅ n“ (je Reihe 5), darunter optionale weitere Knopf-Reihen."""
    reihen = [[{"text": f"✅ {i}", "callback_data": f"k|{lauf}|{i}"} for i in range(a, min(a + 5, n + 1))]
              for a in range(1, n + 1, 5)]
    reihen += zusatz or []
    return {"inline_keyboard": reihen} if reihen else None


def merken(p: Path, lauf: str, nr: str, jetzt: float | None = None) -> str:
    s = laden(p)
    liste = (s.get("laeufe") or {}).get(lauf)
    try:
        e = liste[int(nr) - 1]
    except (TypeError, ValueError, IndexError):
        return "Diese Liste ist zu alt."
    if any(k.get("link") == e["link"] and k.get("link") for k in s.get("kommentiert", [])):
        return f"Schon gemerkt: {nr}"
    s.setdefault("kommentiert", []).append(dict(e, ts=int(jetzt or time.time())))
    s["kommentiert"] = s["kommentiert"][-3000:]
    speichern(p, s)
    return f"✅ Gemerkt: {nr} · {e['konto']}"


def x_antworten(geheim: dict, konto: str, tage: float = 7, jetzt: float | None = None,
                get=requests.request) -> list[dict]:
    """Unsere eigenen Antworten auf X der letzten Tage: [{ziel, likes, antworten}] (ziel = Konto, dem wir antworteten)."""
    import datetime as dt
    from . import kanaele
    start = dt.datetime.fromtimestamp((jetzt or time.time()) - min(tage, 6.9) * TAG, dt.timezone.utc)
    params = {"query": f"from:{konto} is:reply", "max_results": "100", "start_time": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "tweet.fields": "public_metrics,in_reply_to_user_id", "expansions": "in_reply_to_user_id",
              "user.fields": "username"}
    url = X_SUCHE + "?" + "&".join(f"{kanaele._q(k)}={kanaele._q(v)}" for k, v in sorted(params.items()))
    r = get("GET", url, headers={"Authorization": kanaele.oauth_kopf("GET", X_SUCHE, geheim, params)}, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"X-Suche: {r.status_code} {r.text[:150]}")
    j = r.json()
    namen = {u["id"]: u["username"] for u in (j.get("includes") or {}).get("users", [])}
    out = []
    for t in j.get("data") or []:
        ziel = namen.get(t.get("in_reply_to_user_id"))
        if not ziel or ziel.lower() == konto.lower():
            continue
        m = t.get("public_metrics") or {}
        out.append({"ziel": ziel, "likes": m.get("like_count") or 0, "antworten": m.get("reply_count") or 0})
    return out


def bilanz(s: dict, x: list[dict] | None, tage: float = 7, jetzt: float | None = None) -> tuple[str, dict]:
    """-> (Telegram-HTML, wert {konto_klein: Punkte je Kommentar}) fuer die letzten `tage`."""
    import html
    e = html.escape
    jetzt = jetzt or time.time()
    neu = [k for k in s.get("kommentiert", []) if k.get("ts", 0) >= jetzt - tage * TAG]
    z = [f"💬 <b>Kommentar-Bilanz der letzten {int(tage)} Tage</b>", ""]
    je_pl: dict[str, int] = {}
    je_konto: dict[tuple, int] = {}
    for k in neu:
        je_pl[k["plattform"]] = je_pl.get(k["plattform"], 0) + 1
        je_konto[(k["plattform"], k["konto"])] = je_konto.get((k["plattform"], k["konto"]), 0) + 1
    if neu:
        z.append("Per Knopf gemerkt: " + " · ".join(f"{p} {n}" for p, n in sorted(je_pl.items(), key=lambda x: -x[1])))
        top = sorted(je_konto.items(), key=lambda x: -x[1])[:5]
        z.append("Am häufigsten: " + ", ".join(f"{e(k)} ({p}) {n}×" for (p, k), n in top))
    else:
        z.append("Keine Kommentare per Knopf gemerkt. Tipp nach dem Kommentieren auf „✅ Nummer“.")
    wert: dict[str, float] = {}
    if x:
        je: dict[str, list] = {}
        for a in x:
            je.setdefault(a["ziel"], []).append(a["likes"] + 3 * a["antworten"])
        wert = {k.lower(): round(sum(v) / len(v), 1) for k, v in je.items()}
        gut = sorted(je.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))
        z += ["", f"<b>X: Wirkung unserer {len(x)} Antworten</b> (Likes + 3× Antworten je Kommentar)"]
        z += [f"• @{e(k)}: {sum(v) / len(v):.1f} im Schnitt bei {len(v)} Kommentar{'en' if len(v) > 1 else ''}"
              for k, v in gut[:8]]
        if len(gut) > 1:
            z.append(f"→ Mehr bei @{e(gut[0][0])}, weniger bei @{e(gut[-1][0])}. "
                     "Der Kommentar-Assistent zeigt die besten Konten ab jetzt zuerst.")
    elif x is not None:
        z += ["", "X: keine eigenen Antworten in dieser Woche gefunden."]
    return "\n".join(z), wert


def sortieren(posts: list[dict], wert: dict) -> list[dict]:
    """Kommentar-Assistent: Konten mit guter Wirkung zuerst, dann nach Interaktion des Posts."""
    return sorted(posts, key=lambda p: (-wert.get(p["konto"].lower(), 0), -p.get("punkte", 0)))
