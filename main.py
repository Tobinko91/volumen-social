"""WhaleSqueeze Redaktion – erzeugt ein Kurzvideo aus den Bot-Daten.

Beispiele:
  python main.py markt                         # Daten aus config.yaml (Server)
  python main.py markt --daten beispieldaten   # Probe mit Beispieldaten
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from social import bilder, daten, formate, pruefung, stimme, texte, video

HIER = Path(__file__).resolve().parent


def lade_cfg() -> tuple[dict, dict]:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    geheim_p = HIER / "secrets.yaml"
    geheim = yaml.safe_load(geheim_p.read_text(encoding="utf-8")) if geheim_p.exists() else {}
    return cfg, geheim or {}


def lade_sperrliste() -> set[str]:
    p = HIER / "sperrliste.txt"
    if not p.exists():
        return set()
    return {z.split("#")[0].strip().upper() for z in p.read_text(encoding="utf-8").splitlines()
            if z.split("#")[0].strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("format", choices=sorted(formate.FORMATE))
    ap.add_argument("--daten", help="Datenordner (Standard: config.yaml daten.dir)")
    ap.add_argument("--out", default=str(HIER / "ausgabe"))
    args = ap.parse_args()

    cfg, geheim = lade_cfg()
    sperr = lade_sperrliste()
    probe = bool(args.daten)
    d = daten.laden(args.daten or cfg["daten"]["dir"],
                    None if probe else cfg["daten"]["max_alter_min"])

    beitrag = formate.FORMATE[args.format](d, sperr)
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
    print(json.dumps({k: meta[k] for k in ("titel", "dauer_s", "text", "stimme", "pruefung", "video")},
                     ensure_ascii=False, indent=2))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
