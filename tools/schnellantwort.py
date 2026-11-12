"""Schnell-Antworten unter grossen Posts (Wunsch Tobias 12.11.2026: „Wir brauchen schnellere Reichweite“).

Fuer kleine Konten bringt auf X nichts so viele Profilbesuche wie eine gute Antwort in den ersten Minuten unter
einem grossen Post. Der Kommentar-Assistent (15:30/20:30) kommt dafuer zu spaet. Darum: alle 10 Minuten (live.sh)
neue Posts weniger, grosser Konten holen und sofort einen Antwort-Vorschlag mit unseren Daten an Tobias schicken.
Tobias postet SELBST (automatisches Antworten verbieten die Plattformen -> Sperrgefahr).

Kosten: eine X-Suche je Lauf, nur Posts seit dem letzten Lauf (ca. 0,005 $ je gelesenem Post). Bei rund 60 Posts
der Zielkonten am Tag etwa 0,30 $ am Tag. Ruhezeit nachts, hoechstens schnellantwort.max_pro_tag Vorschlaege.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import daten, kommentare, kommentiert  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))


def nachricht(k: dict, minuten: int) -> str:
    import html
    e = html.escape
    return "\n".join([
        f"⚡ <b>Schnell-Antwort</b> · @{e(k['konto'])} · Post ist {minuten} Min. alt",
        "Jetzt antworten = am meisten gesehen. Text antippen = kopiert · Link öffnen · einfügen · posten", "",
        f"<i>{e(k['text'][:160].strip())}{'…' if len(k['text']) > 160 else ''}</i>",
        f"🔗 {e(k['link'])}", "",
        f"<code>{e(k['kommentar'])}</code>",
        f"DE: {e(k.get('deutsch', ''))}"])


def main(posts_holen=None, schreiber=None, markt="auto", senden=None, jetzt: float | None = None) -> int:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    s = cfg.get("schnellantwort") or {}
    if not s.get("aktiv"):
        return 0
    jetzt = jetzt or time.time()
    stunde = int(time.strftime("%H", time.localtime(jetzt)))
    von, bis = s.get("ruhe", [23, 7])
    if stunde >= von or stunde < bis:
        return 0
    gp = BASIS / "secrets.yaml"
    g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    sp = BASIS / "sperrliste.txt"
    sperr = {z.split("#")[0].strip().upper() for z in (sp.read_text().splitlines() if sp.exists() else [])
             if z.split("#")[0].strip()}
    stand_p = AUSGABE / "schnellantwort_stand.json"
    try:
        stand = json.loads(stand_p.read_text())
    except Exception:
        stand = {}
    tag = time.strftime("%Y-%m-%d", time.localtime(jetzt))
    heute = stand.get("anzahl", {}).get(tag, 0)
    if heute >= int(s.get("max_pro_tag", 12)):
        return 0
    # nur Posts seit dem letzten Lauf (spart Kosten), hoechstens schnellantwort.minuten alt
    letzter = float(stand.get("letzter", 0))
    fenster_min = min(float(s.get("minuten", 15)), max(5.0, (jetzt - letzter) / 60 + 1)) if letzter else s.get("minuten", 15)
    try:
        posts = (posts_holen or (lambda: kommentare.posts_holen(g, s["konten"], float(fenster_min) / 60,
                                                                int(s.get("max_posts", 10)), jetzt)))()
    except Exception as e:
        print("X-Posts nicht geholt (Schnell-Antwort):", e)
        return 1
    stand["letzter"] = jetzt
    k_stand_p = AUSGABE / "kommentare_stand.json"   # gemeinsam mit dem Kommentar-Assistenten: nie doppelt
    try:
        k_stand = json.loads(k_stand_p.read_text())
    except Exception:
        k_stand = {"ids": []}
    min_likes = int(s.get("min_likes", 0))
    posts = [p for p in posts if p["id"] not in k_stand["ids"] and p.get("likes", 0) >= min_likes]
    AUSGABE.mkdir(parents=True, exist_ok=True)
    if not posts:
        stand_p.write_text(json.dumps(stand))
        return 0
    if markt == "auto":
        try:
            markt = daten.marktlage(daten.laden(cfg["daten"]["dir"], cfg["daten"]["max_alter_min"]))
        except Exception:
            markt = None
    fakten = dict(kommentare.fakten_aus_markt(markt), current_events=kommentare.anlaesse())
    try:
        vorschlaege = (schreiber or (lambda ps: kommentare.schreiben(ps, fakten, cfg, g["anthropic_api_key"])))(posts)
    except Exception as e:
        print("Claude-Fehler (Schnell-Antwort):", e)
        stand_p.write_text(json.dumps(stand))
        return 1
    nach_id = {p["id"]: p for p in posts}
    gesendet = 0
    for v in vorschlaege:
        p = nach_id.get(str(v.get("id")))
        if not p or heute + gesendet >= int(s.get("max_pro_tag", 12)):
            continue
        if kommentare.pruefen(v["text"], p["text"], fakten, cfg, sperr):
            continue
        k = dict(p, kommentar=v["text"], deutsch=v.get("deutsch", ""))
        try:
            import datetime as dt
            alter = int((jetzt - dt.datetime.fromisoformat(p["zeit"].replace("Z", "+00:00")).timestamp()) / 60)
        except Exception:
            alter = 0
        text = nachricht(k, max(0, alter))
        print(text)
        if "--senden" in sys.argv or senden:
            from social import telegram
            lauf = "s" + time.strftime("%m%d%H%M", time.localtime(jetzt)) + str(gesendet)
            kommentiert.lauf_merken(AUSGABE / "kommentiert.json", lauf, [dict(k, plattform="X")])
            telegram.an_tobias(g, text, kommentiert.knoepfe(lauf, 1), post=senden or requests.post)
        k_stand["ids"] = (k_stand["ids"] + [p["id"]])[-500:]
        gesendet += 1
    stand.setdefault("anzahl", {})[tag] = heute + gesendet
    stand["anzahl"] = {t: n for t, n in stand["anzahl"].items() if t >= tag}
    stand_p.write_text(json.dumps(stand))
    k_stand_p.write_text(json.dumps(k_stand))
    return 0


if __name__ == "__main__":
    sys.exit(main())
