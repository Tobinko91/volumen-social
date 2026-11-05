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
    "elevenlabs": [("Brian", "A – männlich, ruhig (deine Wahl vom 26.10.)"), ("George", "B – männlich, warm"),
                   ("Bill", "C – männlich, sachlich"), ("Alice", "D – weiblich, klar")],
    "openai": [("cedar", "A – männlich, ruhig"), ("ash", "B – männlich, kräftig"), ("marin", "C – weiblich, klar"),
               ("coral", "D – weiblich, warm")],
    "google": [("en-US-Chirp3-HD-Charon", "A – männlich, ruhig"), ("en-US-Chirp3-HD-Fenrir", "B – männlich, kräftig"),
               ("en-US-Chirp3-HD-Kore", "C – weiblich, klar"), ("en-US-Chirp3-HD-Aoede", "D – weiblich, warm")],
}
FELD = {"openai": "openai_stimme", "google": "google_stimme", "elevenlabs": "voice_name"}
TEXT = ("Bitcoin just moved +3.2% in one hour. Whales bought 4,000 BTC on exchanges. "
        "Here is what it means. Follow WhaleSqueeze for daily data. Not financial advice.")


PROBE_ZAHLEN = ("From $14.23 to a high of $23.90 in 24 hours. Now $23.23, 2.8% below the high. "
                "Open interest rose 17.1% with funding at -0.29%. Volume was 6.0x the daily average. "
                "Long/short ratio: 1.5, up from 0.8 a day ago. A small coin at $0.04512.")


def kurz(text: str) -> int:
    """/hoerprobe im Redaktions-Bot (Wunsch Tobias 05.11.2026): den Text mit der eingestellten Stimme sprechen,
    genau wie im Video (Preise sprechbar), und als Sprachnachricht schicken."""
    basis = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
    geheim = yaml.safe_load((basis / "secrets.yaml").read_text()) or {}
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    key = stimme.schluessel(cfg, geheim)
    if not key:
        telegram.text_senden(geheim, "🎙 Hörprobe geht nicht: Stimmen-Schlüssel fehlt.")
        return 1
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "hoerprobe.mp3"
        try:
            getattr(stimme, stimme.ERZEUGER[cfg["stimme"].get("anbieter", "elevenlabs")])(text, f, cfg, key)
        except Exception as e:
            telegram.text_senden(geheim, f"🎙 Hörprobe fehlgeschlagen: {e}")
            return 1
        gesprochen, _ = stimme.sprechbar(text)
        with open(f, "rb") as fh:
            requests.post(telegram.API.format(token=geheim["telegram_token"], methode="sendAudio"),
                          data={"chat_id": geheim["telegram_chat_id"], "title": "Hörprobe",
                                "caption": ("🎙 Hörprobe. Untertitel: " + text)[:1000]
                                + ("\n\nGesprochen: " + gesprochen)[:1000] if gesprochen != text else ""},
                          files={"audio": (f.name, fh, "audio/mpeg")}, timeout=60)
    return 0


def main() -> int:
    if "--text" in sys.argv:
        i = sys.argv.index("--text")
        return kurz(" ".join(sys.argv[i + 1:]).strip() or PROBE_ZAHLEN)
    basis = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
    geheim = yaml.safe_load((basis / "secrets.yaml").read_text()) or {}
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    anbieter = cfg["stimme"].get("anbieter", "openai")
    if anbieter not in STIMMEN:
        print("Hoerproben gibt es fuer elevenlabs, openai und google")
        return 1
    key = stimme.schluessel(cfg, geheim)
    if not key:
        print(f"{stimme.SCHLUESSEL[anbieter]} fehlt: erst python3 tools/schluessel.py")
        return 1
    erzeuger = getattr(stimme, stimme.ERZEUGER[anbieter])
    if anbieter == "elevenlabs":   # Tarif und Guthaben gleich mitmelden
        try:
            gh = stimme.elevenlabs_guthaben(key)
            rest = (gh["limit"] or 0) - (gh["verbraucht"] or 0)
            info = f"🎙 ElevenLabs-Tarif: {gh['tarif']} · noch {rest:,} von {gh['limit']:,} Credits diesen Monat".replace(",", ".")
            if str(gh["tarif"]).lower() == "free":
                info += "\n⚠️ Im Free-Tarif dürfen die Videos nicht kommerziell genutzt werden – bitte auf Starter (5 $) wechseln."
            telegram.text_senden(geheim, info)
            print(info)
        except Exception as e:
            print("Guthaben nicht abrufbar:", e)
    with tempfile.TemporaryDirectory() as d:
        for name, label in STIMMEN[anbieter]:
            f = Path(d) / f"{name}.mp3"
            try:
                erzeuger(TEXT, f, dict(cfg, stimme=dict(cfg["stimme"], voice_id=None, **{FELD[anbieter]: name})), key)
            except stimme.StimmeFehlt as e:   # z. B. Stimme nicht in der Bibliothek: ueberspringen statt abbrechen
                print("Uebersprungen:", label, e)
                continue
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
