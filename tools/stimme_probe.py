"""Hoerproben der Google-Stimme (Chirp 3 HD) an Tobias im Redaktions-Bot schicken.

    sudo -u redaktion env SOCIAL_GEHEIM=/opt/volumen-social python3 tools/stimme_probe.py

Schickt je Stimme eine kurze Probe. Tobias waehlt, die Redaktion traegt sie in config.yaml (stimme.google_stimme) ein.
Prueft dabei auch, ob der Schluessel funktioniert (sonst Fehlermeldung mit dem Grund von Google).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import requests
import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import stimme, telegram  # noqa: E402

STIMMEN = {
    "openai": [("cedar", "A – männlich, ruhig"), ("ash", "B – männlich, kräftig"), ("marin", "C – weiblich, klar"),
               ("coral", "D – weiblich, warm")],
    "google": [("en-US-Chirp3-HD-Charon", "A – männlich, ruhig"), ("en-US-Chirp3-HD-Fenrir", "B – männlich, kräftig"),
               ("en-US-Chirp3-HD-Kore", "C – weiblich, klar"), ("en-US-Chirp3-HD-Aoede", "D – weiblich, warm")],
}
FELD = {"openai": "openai_stimme", "google": "google_stimme"}
TEXT = ("Bitcoin just moved +3.2% in one hour. Whales bought 4,000 BTC on exchanges. "
        "Here is what it means. Follow WhaleSqueeze for daily data. Not financial advice.")


def main() -> int:
    basis = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
    geheim = yaml.safe_load((basis / "secrets.yaml").read_text()) or {}
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    anbieter = cfg["stimme"].get("anbieter", "openai")
    if anbieter not in STIMMEN:
        print("Hoerproben gibt es fuer openai und google")
        return 1
    key = stimme.schluessel(cfg, geheim)
    if not key:
        print(f"{stimme.SCHLUESSEL[anbieter]} fehlt: erst python3 tools/schluessel.py")
        return 1
    erzeuger = getattr(stimme, stimme.ERZEUGER[anbieter])
    with tempfile.TemporaryDirectory() as d:
        for name, label in STIMMEN[anbieter]:
            f = Path(d) / f"{name}.mp3"
            try:
                erzeuger(TEXT, f, dict(cfg, stimme=dict(cfg["stimme"], **{FELD[anbieter]: name})), key)
            except Exception as e:
                print("Fehler:", e)
                telegram.text_senden(geheim, f"🎙 Stimme ({anbieter}) geht noch nicht: {e}")
                return 1
            with open(f, "rb") as fh:
                requests.post(telegram.API.format(token=geheim["telegram_token"], methode="sendAudio"),
                              data={"chat_id": geheim["telegram_chat_id"], "title": f"Stimme {label}",
                                    "caption": f"🎙 Stimme {label}"},
                              files={"audio": (f.name, fh, "audio/mpeg")}, timeout=60)
            print("gesendet:", label)
    telegram.text_senden(geheim, "🎙 Welche Stimme? Schreib im Redaktions-Chat A, B, C oder D.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
