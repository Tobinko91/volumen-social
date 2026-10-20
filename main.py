"""WhaleSqueeze Redaktion – erzeugt ein Kurzvideo aus den Bot-Daten.

Beispiele:
  python main.py markt                         # Daten aus config.yaml (Server)
  python main.py markt --daten beispieldaten   # Probe mit Beispieldaten
"""
from __future__ import annotations

import argparse
import os
import json
import sys
import time
from pathlib import Path

import yaml

from social import bilder, daten, formate, pruefung, stimme, telegram, texte, video

HIER = Path(__file__).resolve().parent
# Auf dem Server liegen Schluessel und Sperrliste ausserhalb des Codes (/opt/volumen-social),
# damit ein Update sie nie ueberschreibt. Lokal: neben main.py.
GEHEIM_ORDNER = Path(os.environ.get("SOCIAL_GEHEIM", HIER))


def lade_cfg() -> tuple[dict, dict]:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    geheim_p = GEHEIM_ORDNER / "secrets.yaml"
    geheim = yaml.safe_load(geheim_p.read_text(encoding="utf-8")) if geheim_p.exists() else {}
    return cfg, geheim or {}


def lade_sperrliste() -> set[str]:
    p = GEHEIM_ORDNER / "sperrliste.txt"
    if not p.exists():
        return set()
    return {z.split("#")[0].strip().upper() for z in p.read_text(encoding="utf-8").splitlines()
            if z.split("#")[0].strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("format", choices=sorted(formate.FORMATE))
    ap.add_argument("--daten", help="Datenordner (Standard: config.yaml daten.dir)")
    ap.add_argument("--out", default=os.environ.get("SOCIAL_AUSGABE", str(HIER / "ausgabe")))
    ap.add_argument("--senden", action="store_true", help="Video per Telegram an Tobias schicken")
    args = ap.parse_args()

    cfg, geheim = lade_cfg()
    sperr = lade_sperrliste()
    probe = bool(args.daten)
    d = daten.laden(args.daten or cfg["daten"]["dir"],
                    None if probe else cfg["daten"]["max_alter_min"])

    beitrag = formate.FORMATE[args.format](d, sperr, cfg.get("sprache", "de"))
    zeilen, textquelle = texte.schreiben(beitrag, cfg, geheim.get("anthropic_api_key"))
    fehler = pruefung.pruefen(zeilen, beitrag, cfg, sperr)
    if fehler and textquelle == "claude":
        print("Claude-Text fiel durch die Pruefung, nehme Vorlage:", fehler)
        zeilen, textquelle = texte.vorlage(beitrag), "vorlage"
        fehler = pruefung.pruefen(zeilen, beitrag, cfg, sperr)

    stempel = time.strftime("%Y%m%d-%H%M")
    ordner = Path(args.out) / f"{stempel}_{beitrag['format']}"
    ordner.mkdir(parents=True, exist_ok=True)

    bild_dateien = bilder.zeichnen(beitrag, zeilen, ordner / "bilder", cfg)
    toene, dauern, tonquelle = stimme.sprechen(zeilen, ordner / "ton", cfg, geheim.get("elevenlabs_api_key"))
    ziel = video.bauen(bild_dateien, toene, dauern, ordner / f"{beitrag['format']}.mp4", cfg)

    meta = {
        "titel": beitrag["titel"],
        "beschreibung": " ".join(zeilen) + "\n\n" + cfg["hinweise"]["fusszeile"] + "\n"
                        + cfg["hinweise"]["konflikt"] + "\n" + " ".join(beitrag["hashtags"]),
        "zeilen": zeilen, "text": textquelle, "stimme": tonquelle,
        "dauer_s": round(sum(dauern), 1), "pruefung": fehler or "bestanden",
        "fakten": beitrag["fakten"], "video": str(ziel),
    }
    (ordner / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.senden:
        status = "✅ Prüfung bestanden" if not fehler else "⚠️ Prüfung: " + "; ".join(fehler)
        ok = telegram.video_senden(geheim, ziel, f"{beitrag['titel']}\n{status}\nText: {textquelle}, Stimme: {tonquelle}")
        print("Telegram:", "gesendet" if ok else "nicht gesendet (Token/Chat-ID fehlen?)")
    print(json.dumps({k: meta[k] for k in ("titel", "dauer_s", "text", "stimme", "pruefung", "video")},
                     ensure_ascii=False, indent=2))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
