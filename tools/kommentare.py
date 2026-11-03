"""Kommentar-Vorschlaege an Tobias (Punkt D). Aus plan.sh um 15:30 und 20:30:
    python3 tools/kommentare.py --senden
Kosten: eine X-Suche je Lauf (ca. 0,005 $ je gelesenem Post, hoechstens kommentare.max_posts) + ein Claude-Aufruf.
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
from social import daten, kommentare  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))


def _melden(g: dict, senden, text: str) -> None:
    """Auch „nichts gefunden“ und Fehler an Tobias (02.11.2026: er bekam nie etwas und wusste nicht warum)."""
    if "--senden" in sys.argv or senden:
        from social import telegram
        telegram.an_tobias(g, text, post=senden or requests.post)


def main(posts_holen=None, schreiber=None, markt="auto", senden=None) -> int:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    k = cfg.get("kommentare") or {}
    if not k.get("aktiv", True):
        return 0
    gp = BASIS / "secrets.yaml"
    g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    sp = BASIS / "sperrliste.txt"
    sperr = {z.split("#")[0].strip().upper() for z in (sp.read_text().splitlines() if sp.exists() else [])
             if z.split("#")[0].strip()}
    stand_p = AUSGABE / "kommentare_stand.json"
    stand = json.loads(stand_p.read_text()) if stand_p.exists() else {"ids": []}
    if markt == "auto":
        try:
            markt = daten.marktlage(daten.laden(cfg["daten"]["dir"], cfg["daten"]["max_alter_min"]))
        except Exception:
            markt = None
    fakten = dict(kommentare.fakten_aus_markt(markt), current_events=kommentare.anlaesse())
    try:
        posts = (posts_holen or (lambda: kommentare.posts_holen(g, k["konten"], k.get("stunden", 3),
                                                                k.get("max_posts", 30))))()
    except Exception as e:
        print("X-Posts nicht geholt:", e)
        _melden(g, senden, f"💬 Kommentar-Assistent: keine Vorschläge, X-Abfrage fehlgeschlagen ({str(e)[:200]}). "
                           "Häufigster Grund: X-Guthaben leer (developer.x.com → Billing).")
        return 1
    posts = [p for p in posts if p["id"] not in stand["ids"]][: int(k.get("anzahl", 5)) + 3]
    if not posts:
        print("Keine neuen Posts.")
        _melden(g, senden, f"💬 Kommentar-Assistent: keine neuen Posts der Zielkonten in den letzten "
                           f"{k.get('stunden', 3)} Std. Nächster Versuch beim nächsten Termin.")
        return 0
    try:
        vorschlaege = (schreiber or (lambda ps: kommentare.schreiben(ps, fakten, cfg, g["anthropic_api_key"])))(posts)
    except Exception as e:
        print("Claude-Fehler:", e)
        _melden(g, senden, f"💬 Kommentar-Assistent: Fehler beim Schreiben ({str(e)[:200]}).")
        return 1
    nach_id = {p["id"]: p for p in posts}
    fertig = []
    for v in vorschlaege:
        p = nach_id.get(str(v.get("id")))
        if not p:
            continue
        fehler = kommentare.pruefen(v["text"], p["text"], fakten, cfg, sperr)
        if fehler:
            print("Verworfen:", p["link"], fehler)
            continue
        fertig.append(dict(p, kommentar=v["text"], deutsch=v.get("deutsch", "")))
        if len(fertig) >= int(k.get("anzahl", 5)):
            break
    if not fertig:
        print("Kein Kommentar hat die Prüfung bestanden.")
        _melden(g, senden, f"💬 Kommentar-Assistent: {len(posts)} Posts gefunden, aber kein Vorschlag hat die "
                           "Prüfung bestanden (Zahlen/Regeln). Nichts zu tun.")
        return 0
    text = kommentare.nachricht(fertig)
    print(text)
    if "--senden" in sys.argv or senden:
        from social import telegram
        print("Gesendet:", telegram.an_tobias(g, text, post=senden or requests.post))
        stand["ids"] = (stand["ids"] + [p["id"] for p in fertig])[-500:]
        AUSGABE.mkdir(parents=True, exist_ok=True)
        stand_p.write_text(json.dumps(stand))
    return 0


if __name__ == "__main__":
    sys.exit(main())
