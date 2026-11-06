"""Wochenbericht an Tobias (Punkt E). Laeuft sonntags 18:30 aus plan.sh:
    python3 tools/wochenbericht.py --senden
Ohne --senden nur Ausgabe im Terminal (zum Ausprobieren).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import bericht, telegram  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))


def main(jetzt: float | None = None, x_holen=None, ig_holen=None, tg_holen=None, senden=None) -> str:
    jetzt = jetzt or time.time()
    gp = BASIS / "secrets.yaml"
    g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    prot = bericht.protokoll_laden(AUSGABE / "protokoll.jsonl", seit=jetzt - bericht.WOCHE)
    links_x = [e["link"] for e in prot if e.get("kanal") == "x" and e.get("link")]
    try:
        x, x_f = (x_holen or (lambda: bericht.x_zahlen(g, links_x)))()
    except Exception as e:
        print("X-Zahlen:", e)
        x, x_f = {}, None
    try:
        ig, ig_f = (ig_holen or (lambda: bericht.instagram_zahlen(g)))()
    except Exception as e:
        print("Instagram-Zahlen:", e)
        ig, ig_f = {}, None
    tg_f = (tg_holen or (lambda: bericht.telegram_abonnenten(g)))()
    follower = {"telegram": tg_f, "x": x_f, "instagram": ig_f, "tiktok": None}
    stand_p = AUSGABE / "bericht_stand.json"
    alt = json.loads(stand_p.read_text()) if stand_p.exists() else {}
    formate = bericht.auswerten(prot, x, ig)
    prot4 = bericht.protokoll_laden(AUSGABE / "protokoll.jsonl", seit=jetzt - 4 * bericht.WOCHE)
    t = bericht.text(formate, follower, alt.get("follower", {}), bericht.top_beitraege(prot, x, ig), jetzt,
                     bericht.haltequote(prot4, ig), bericht.haltequote(prot4, ig, "haken"), bericht.bildtest(prot, x),
                     bericht.bildtest(prot, x, "titelbild"))
    print(t)
    if "--senden" in sys.argv or senden:
        (senden or telegram.text_senden)(g, t)
        AUSGABE.mkdir(parents=True, exist_ok=True)
        stand_p.write_text(json.dumps({"ts": int(jetzt), "follower": follower}))
    return t


if __name__ == "__main__":
    main()
