"""Beitraege aus dem Redaktions-Chat (Branch 'warteschlange' im Repository) als Vorschlag an Tobias.

Ablauf: Claude legt im Chat einen Ordner warteschlange/<name>/ mit post.png, post_x.txt, post_telegram.txt
an und schiebt ihn auf den Branch 'warteschlange'. plan.sh holt den Branch nach /opt/volumen-social/eingang,
dieses Skript prueft jeden neuen Ordner und schickt ihn mit Freigabe-Knoepfen an Tobias.
Gepostet wird erst, wenn Tobias einen Knopf drueckt.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import telegram  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))
EINGANG = Path(os.environ.get("SOCIAL_EINGANG", BASIS / "eingang"))
FOTOS = Path(os.environ.get("SOCIAL_FOTOS", BASIS / "fotos"))


def pruefen(ordner: Path, cfg: dict, sperr: set[str]) -> list[str]:
    fehler = []
    for f in ("post.png", "post_x.txt", "post_telegram.txt"):
        if not (ordner / f).exists():
            fehler.append(f"{f} fehlt")
    if fehler:
        return fehler
    x = (ordner / "post_x.txt").read_text(encoding="utf-8")
    tg = (ordner / "post_telegram.txt").read_text(encoding="utf-8")
    if len(x) > 280:
        fehler.append(f"X-Text zu lang ({len(x)} Zeichen)")
    hw = (cfg["hinweise"].get("post_text") or "Keine Anlageberatung").rstrip(".")
    if hw not in x + tg and "Keine Anlageberatung" not in x + tg:
        fehler.append("Risiko-Hinweis fehlt")
    text = (x + " " + tg)
    for h in (h for h in cfg["hinweise"].values() if h):   # leere Hinweise ueberspringen
        text = text.replace(h, " ")
    klein = text.replace("Keine Anlageberatung", " ").lower()
    fehler += [f"verbotene Wendung: '{w}'" for w in cfg["pruefung"]["verboten"] if w in klein]
    import re
    fehler += [f"Coin auf der Sperrliste: {c}" for c in sperr if re.search(rf"\b{re.escape(c)}\b", text, re.I)]
    return fehler


def hingucker(ziel: Path, geheim: dict) -> str:
    """hingucker.png zeichnen, Test-Gruppe zuteilen, Vorschau an Tobias. Rueckgabe: Zeile fuer den Hinweis."""
    from social import bildpaket
    try:
        bild = bildpaket.aus_spec(ziel, FOTOS)
    except Exception as e:
        return f"\n🖼 Hingucker nicht gezeichnet ({str(e)[:100]})"
    if not bild:
        return "\n🖼 Kein freies Foto dieser Person in der Bibliothek, X bekommt nur das Beitragsbild."
    art = bildpaket.test_zuteilen(ziel, AUSGABE / "bildtest_stand.json")
    if art == "mit":
        telegram.foto_an_tobias(geheim, bild, "🖼 Hingucker (X bekommt 2 Bilder nebeneinander)")
        return "\n🖼 Bild-Test: MIT Hingucker auf X (Vorschau oben)"
    return "\n🖼 Bild-Test: OHNE Hingucker (Vergleichsgruppe, X bekommt nur das Beitragsbild)"


def main() -> int:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    gp = BASIS / "secrets.yaml"
    geheim = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    sp = BASIS / "sperrliste.txt"
    sperr = {z.split("#")[0].strip().upper() for z in (sp.read_text().splitlines() if sp.exists() else [])
             if z.split("#")[0].strip()}
    stand_p = AUSGABE / "eingang_stand.json"
    stand = json.loads(stand_p.read_text()) if stand_p.exists() else []
    if not EINGANG.is_dir():
        return 0
    for o in sorted(p for p in EINGANG.iterdir() if p.is_dir()):
        if o.name in stand:
            continue
        ziel = AUSGABE / f"chat_{o.name}"
        shutil.copytree(o, ziel, dirs_exist_ok=True)
        fehler = pruefen(ziel, cfg, sperr)
        ton = ""
        if (ziel / "reel.json").exists() and not (ziel / "video.mp4").exists():   # Reel: Server spricht + schneidet
            from social import reel
            try:
                ton = "\n🎙 Ton: " + reel.bauen(ziel, cfg, geheim)
            except Exception as e:
                fehler.append(f"Reel nicht gebaut ({str(e)[:120]}), nur Bild")
        bild_hw = ""
        if (ziel / "hingucker.json").exists():   # 06.11.2026: Hingucker-Bild fuer X (Foto/Zitat/Vergleich)
            bild_hw = hingucker(ziel, geheim)
        hinweis = ("💬 Aus dem Redaktions-Chat" + ton + bild_hw
                   + ("\n⚠️ " + "; ".join(fehler) if fehler else ""))
        if not (ziel / "post.png").exists():
            gesendet = telegram.text_senden(geheim, hinweis)
        else:
            gesendet = telegram.vorschlag_senden(geheim, ziel, hinweis)
        if not gesendet:   # beim naechsten Lauf noch einmal versuchen, statt still zu verschwinden
            print("Eingang:", o.name, "NICHT zugestellt, neuer Versuch beim naechsten Lauf")
            continue
        stand.append(o.name)
        print("Eingang:", o.name, fehler or "ok")
    stand_p.write_text(json.dumps(stand[-500:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
