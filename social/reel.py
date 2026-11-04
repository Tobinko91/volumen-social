"""Reels aus dem Redaktions-Chat (Warteschlange) auf dem Server fertig bauen: Stimme (ElevenLabs) + Musik.

Anlass 04.11.2026: Der Chat hat keinen Stimmen-Schluessel (der liegt nur in secrets.yaml auf dem Server).
Darum legt der Chat nur Szenenbilder und Sprechtext ab, der Server spricht und schneidet.

reel.json im Ordner:
  {"thema": "midterms-3",
   "szenen": [{"bild": "szene_0.png", "text": "Gesprochener Satz",
               "chart": {"base": "BTC", "intervall": "15m", "anzahl": 48, "box": [60, 700, 1020, 1500],
                         "titel": "BTC · 15m"}}, ...]}
- "bild" ist Pflicht (fertiges 1080x1920-Bild). Mit "chart" zeichnet der Server den echten Kursverlauf in
  die Box (Kurse holt nur der Server, der Chat erreicht die Boersen nicht). Klappt das nicht, bleibt das Bild.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


def chart_szene(ordner: Path, s: dict, thema: str, kerzen_holen) -> Path:
    from . import design, grafik
    c = s["chart"]
    k = kerzen_holen(c.get("base", "BTC"), c.get("intervall", "15m"), int(c.get("anzahl", 48)))
    if len(k) < 12:
        raise ValueError(f"zu wenige Kerzen ({len(k)})")
    img = Image.open(ordner / s["bild"]).convert("RGBA")
    th = design.thema_waehlen("markt", thema)
    grafik.echt_chart(img, th, tuple(c["box"]), k, "linie", {}, 3, c.get("lang", "en"), c.get("titel", ""))
    ziel = ordner / f"chart_{Path(s['bild']).stem}.png"
    img.convert("RGB").save(ziel)
    return ziel


def bauen(ordner: Path, cfg: dict, geheim: dict, kerzen_holen=None, sprechen=None, schneiden=None) -> str:
    """Baut ordner/video.mp4 aus reel.json. Gibt die Tonquelle zurueck ('elevenlabs', 'stille (...)', ...)."""
    from . import kurse, stimme, video
    kerzen_holen = kerzen_holen or (lambda b, i, n: kurse.kerzen(b, i, n))
    sprechen = sprechen or stimme.sprechen
    schneiden = schneiden or video.bauen
    spec = json.loads((ordner / "reel.json").read_text(encoding="utf-8"))
    bilder, hinweise = [], []
    for s in spec["szenen"]:
        p = ordner / s["bild"]
        if s.get("chart"):
            try:
                p = chart_szene(ordner, s, spec.get("thema", ordner.name), kerzen_holen)
            except Exception as e:   # ohne Kurse trotzdem ein Video, Hinweis an Tobias
                hinweise.append(f"Chart fehlt ({str(e)[:80]})")
        bilder.append(p)
    zeilen = [s["text"] for s in spec["szenen"]]
    toene, dauern, quelle = sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    schneiden(bilder, toene, dauern, ordner / "video.mp4", cfg)
    return "; ".join([quelle, *hinweise])
