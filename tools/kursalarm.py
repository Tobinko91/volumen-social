"""Alle 10 Minuten (tools/live.sh): BTC/ETH +-4 % in 60 Minuten -> Eilmeldung als Bild + Reel an Tobias."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import kursalarm, kurse, reel, telegram  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))


def main() -> int:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    if not (cfg.get("kursalarm") or {}).get("aktiv", True):
        return 0
    g = yaml.safe_load((BASIS / "secrets.yaml").read_text()) or {}
    sp = AUSGABE / "kursalarm_stand.json"
    stand = json.loads(sp.read_text()) if sp.exists() else {}
    alarme = kursalarm.pruefen(lambda b, i, n: kurse.kerzen(b, i, n), stand)
    sp.write_text(json.dumps(stand))
    if not alarme:
        return 0
    bo, ro = kursalarm.bauen(alarme, AUSGABE, cfg)
    print("Kurs-Alarm:", [(a["base"], round(a["chg1h"], 1)) for a in alarme])
    if "--senden" in sys.argv:
        telegram.vorschlag_senden(g, bo, "🚨 Kurs-Alarm (automatisch, echte Bitunix-Kurse). Das Warum folgt als Hot Topic.")
        try:
            ton = reel.bauen(ro, cfg, g)
            telegram.vorschlag_senden(g, ro, f"🚨 Kurs-Alarm als Reel · 🎙 Ton: {ton}")
        except Exception as e:
            telegram.text_senden(g, f"⚠️ Kurs-Alarm-Reel nicht gebaut: {str(e)[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
