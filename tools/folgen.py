"""Taegliche Folge-Liste an Tobias (Redaktions-Bot). Aufruf aus plan.sh:
    python3 tools/folgen.py --senden
X: ein Knopf "allen folgen" (freigabe.py fuehrt es aus). Instagram/TikTok/YouTube: Links zum Selbst-Antippen.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import folgen  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))
STAND = AUSGABE / "folgen_stand.json"


def main(senden=None) -> int:
    cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
    f = cfg.get("folgen") or {}
    stand = folgen.stand_laden(STAND)
    a = folgen.auswahl(folgen.liste(), stand, int(f.get("x_pro_tag", 10)), int(f.get("andere_pro_tag", 5)))
    datum = folgen.heute()
    stand.setdefault("heute", {})[datum] = {"x": [k["name"] for k in a["x"]],
                                           "andere": [f"{k['plattform']}:{k['name'].lower()}" for k in a["andere"]]}
    stand["heute"] = dict(list(stand["heute"].items())[-14:])
    text, knoepfe = folgen.nachricht(a, datum)
    print(text)
    if "--senden" in sys.argv or senden:
        gp = BASIS / "secrets.yaml"
        g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
        if g.get("telegram_token") and g.get("telegram_chat_id"):
            daten = {"chat_id": g["telegram_chat_id"], "text": text, "parse_mode": "HTML",
                     "disable_web_page_preview": "true"}
            if knoepfe:
                daten["reply_markup"] = json.dumps(knoepfe)
            (senden or requests.post)(f"https://api.telegram.org/bot{g['telegram_token']}/sendMessage",
                                      data=daten, timeout=30)
    AUSGABE.mkdir(parents=True, exist_ok=True)
    folgen.stand_speichern(STAND, stand)
    return 0


if __name__ == "__main__":
    sys.exit(main())
