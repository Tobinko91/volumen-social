"""Stuendlich (tools/plan.sh, Slot :00): Funding/Open Interest aller Coins mitschreiben (social/verlauf.py)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import daten, verlauf  # noqa: E402

AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social")) / "ausgabe"))

if __name__ == "__main__":
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    d = daten.laden(cfg["daten"]["dir"], None)
    print("Verlauf:", verlauf.speichern(d.coins, AUSGABE / "verlauf"), "Coins")
