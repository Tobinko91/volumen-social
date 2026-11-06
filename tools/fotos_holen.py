"""Foto-Bibliothek laden (inhalte/personen.yaml, Wunsch Tobias 06.11.2026). Aus plan.sh sonntags 04:00 und beim
ersten Lauf:  python3 tools/fotos_holen.py --senden
Mit --senden bekommt Tobias eine Uebersicht (Kontaktbogen) aller Fotos. Ein Foto entfernen: Datei auf dem Server
loeschen oder dem Redaktions-Chat sagen, er traegt es in personen.yaml als Ausschluss ein.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import fotos  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
ZIEL = Path(os.environ.get("SOCIAL_FOTOS", BASIS / "fotos"))


def kontaktbogen(index: dict, ziel: Path) -> Path | None:
    from PIL import Image, ImageDraw
    from social import design
    zeilen = [(slug, l) for slug, l in index.items()]
    if not zeilen:
        return None
    k = 160
    img = Image.new("RGB", (240 + 5 * (k + 8), len(zeilen) * (k + 8) + 8), design.rgb(design.MITTERNACHT))
    d = ImageDraw.Draw(img)
    for r, (slug, liste) in enumerate(zeilen):
        y = 8 + r * (k + 8)
        d.text((12, y + k // 2 - 14), slug, font=design.font("Bold", 26), fill=design.TEXT)
        for c, f in enumerate(liste[:5]):
            try:
                t = Image.open(ziel / f["datei"]).convert("RGB")
                t.thumbnail((k, k))
                img.paste(t, (240 + c * (k + 8), y))
            except Exception:
                pass
    p = ziel / "kontaktbogen.jpg"
    img.save(p, quality=85)
    return p


def main(get=None, senden=False) -> dict:
    index = fotos.holen(ZIEL, get=get) if get else fotos.holen(ZIEL)
    n = sum(len(v) for v in index.values())
    print(f"Foto-Bibliothek: {len(index)} Personen, {n} Fotos")
    if "--senden" in sys.argv or senden:
        gp = BASIS / "secrets.yaml"
        g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
        from social import telegram
        alle = [p["slug"] for p in yaml.safe_load((HIER / "inhalte" / "personen.yaml").read_text(encoding="utf-8"))]
        fehlt = [s for s in alle if s not in index]
        bogen = kontaktbogen(index, ZIEL)
        text = (f"📸 Foto-Bibliothek: {len(index)} Personen, {n} Fotos (nur freie Lizenzen)."
                + (f"\nOhne freies Foto: {', '.join(fehlt)}" if fehlt else "")
                + "\nGefällt ein Foto nicht, sag es dem Redaktions-Chat (Person + Nummer von links).")
        if bogen:
            telegram.foto_an_tobias(g, bogen, text)
        else:
            telegram.an_tobias(g, text)
    return index


if __name__ == "__main__":
    main()
