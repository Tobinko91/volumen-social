"""Instagram-Token taeglich verlaengern (Langzeit-Token gilt 60 Tage ab der letzten Verlaengerung).
Laeuft aus plan.sh um 04:00 als Benutzer "redaktion". Ohne Token passiert nichts.
Schlaegt die Verlaengerung fehl, bekommt Tobias eine Nachricht im Redaktions-Bot."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import kanaele, telegram  # noqa: E402

DATEI = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social")) / "secrets.yaml"


def main(erneuern=kanaele.instagram_token_erneuern, melden=telegram.text_senden) -> int:
    g = (yaml.safe_load(DATEI.read_text()) if DATEI.exists() else {}) or {}
    if not g.get("instagram_token"):
        return 0
    try:
        neu, sekunden = erneuern(g["instagram_token"])
    except Exception as e:
        melden(g, f"⚠️ Instagram-Token konnte nicht verlängert werden: {e}\n"
                  "Bitte in der Meta-App einen neuen Token erzeugen und mit schluessel.py (Punkt 9) eintragen.")
        return 1
    g["instagram_token"] = neu
    g["instagram_token_bis"] = int(time.time()) + sekunden
    tmp = DATEI.with_suffix(".tmp")
    tmp.write_text(yaml.safe_dump(g, allow_unicode=True))
    os.chmod(tmp, 0o600)
    tmp.replace(DATEI)
    print(f"Instagram-Token verlängert, gültig noch {sekunden // 86400} Tage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
