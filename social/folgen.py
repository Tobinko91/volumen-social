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


def auswahl(konten: list[dict], stand: dict, n_x: int = 10, n_andere: int = 5,
            je_plattform: dict | None = None) -> dict:
    """Naechste noch nicht erledigte Konten: bis zu n_x auf X; die anderen Plattformen entweder zusammen bis n_andere
    oder (je_plattform, seit 02.11.2026: Tobias will Instagram- und TikTok-Follower) je Plattform eine eigene Zahl."""
    offen = [k for k in konten if _schluessel(k) not in stand.get("erledigt", {})]
    x = [k for k in offen if k["plattform"] == "x"][:n_x]
    if je_plattform:
        andere = []
        for pl, n in je_plattform.items():
            andere += [k for k in offen if k["plattform"] == pl][:int(n)]
    else:
        andere = [k for k in offen if k["plattform"] != "x"][:n_andere]
    return {"x": x, "andere": andere}


KOMMENTAR_SYSTEM = """You write short comments for WhaleSqueeze (faceless crypto data account: on-chain whale data,
small-cap market breadth) that the editor pastes under the LATEST market or crypto-news post of big Instagram,
TikTok and YouTube creators. You do not see their posts, so each comment must fit any post about today's crypto market.

Rules:
- 1 to 2 short sentences, friendly and factual, plain English, max 200 characters, no hashtags, at most one emoji.
- Exactly one concrete number from OUR DATA (never invent or calculate numbers).
- No links, no "follow us", no price targets, no buy/sell calls, no predictions, no hype.
- Every comment different in wording and number. Ending with a short question to the creator is welcome.
Reply with JSON only: {"kommentare": [{"text": "<comment>", "deutsch": "<short German translation>"}]}"""


def kommentare_schreiben(n: int, fakten: dict, cfg: dict, api_key: str, post=requests.post) -> list[dict]:
    """n verschiedene Kommentare mit unseren Zahlen (Instagram/TikTok/YouTube haben keine Schnittstelle zum Lesen
    fremder Posts, darum passend zu „heute am Markt“). Jede Zahl wird geprueft, Fehlerhafte fliegen raus."""
    from . import claude, pruefung
    if not (n and fakten and api_key):
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


def nachricht(a: dict, datum: str, kommentare: list[dict] | None = None) -> tuple[str, dict | None]:
    """Text (HTML) + Knoepfe fuer den Redaktions-Bot. kommentare: je Instagram/TikTok/YouTube-Konto einer zum Kopieren."""
    e = html.escape
    kommentare = list(kommentare or [])
    z = [f"👥 <b>Folge-Liste {datum}</b>", ""]
    if a["x"]:
        z.append(f"<b>X</b> – ein Tipp auf den Knopf, dann folgt @whalesqueeze allen {len(a['x'])}:")
        z += [f"• <a href=\"{LINKS['x'].format(n=k['name'])}\">@{e(k['name'])}</a> – {e(k.get('warum', ''))}"
              for k in a["x"]]
        z.append("")
    if a["andere"]:
        z.append("<b>Instagram / TikTok / YouTube</b> – selbst antippen, folgen und unter den neuesten Markt-Post "
                 "kommentieren (Kommentar antippen = kopiert):")
        for i, k in enumerate(a["andere"]):
            z.append(f"• {NAMEN[k['plattform']]}: <a href=\"{LINKS[k['plattform']].format(n=k['name'])}\">"
                     f"{e(k['name'])}</a> – {e(k.get('warum', ''))}")
            if i < len(kommentare):
                z.append(f"<code>{e(kommentare[i]['text'])}</code>")
        if kommentare:
            z.append("<i>Passt der neueste Post nicht zum Markt (Meme, Werbung), Kommentar weglassen. "
                     "Jeden Text nur einmal verwenden.</i>")
        z.append("")
    if not (a["x"] or a["andere"]):
        return "👥 Folge-Liste: alle Konten erledigt. Der Redaktions-Chat ergänzt neue in inhalte/folgen.yaml.", None
    z.append("Danach kommentieren: in der ersten Stunde nach einem Post, eigene Zahl, kein Link.")
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
