"""Kommentar-Bilanz an Tobias (Wunsch 06.11.2026), sonntags 18:30 aus plan.sh:
    python3 tools/kommentar_bilanz.py --senden
Zaehlt die per „✅ Nummer“ gemerkten Kommentare und misst auf X die Wirkung unserer Antworten je Zielkonto
(eine X-Suche, hoechstens 100 Posts, ca. 0,50 $). Die Wirkung landet in kommentiert.json ("wert") und sortiert
ab dann den Kommentar-Assistenten.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import kommentiert  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))


def main(x_holen=None, senden=None, jetzt=None) -> str:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    gp = BASIS / "secrets.yaml"
    g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    konto = (cfg.get("kommentare") or {}).get("eigenes_konto", "whalesqueeze")
    try:
        x = (x_holen or (lambda: kommentiert.x_antworten(g, konto, jetzt=jetzt)))()
    except Exception as e:
        print("X-Antworten nicht gelesen:", e)
        x = None
    p = AUSGABE / "kommentiert.json"
    s = kommentiert.laden(p)
    text, wert = kommentiert.bilanz(s, x, jetzt=jetzt)
    if wert:
        s["wert"] = wert
        kommentiert.speichern(p, s)
    print(text)
    if "--senden" in sys.argv or senden:
        from social import telegram
        print("Gesendet:", telegram.an_tobias(g, text, post=senden or requests.post))
    return text


if __name__ == "__main__":
    main()
