"""S22 Unlock-Posts + S26 Nachfolge-Reels, alle 10 Minuten aus tools/live.sh (Wunsch Tobias 03./06.11.2026).

Neue grosse Unlocks oder Unlocks mit Muster -> Bild (4:5) + Reel (9:16) an Tobias. Nach jedem geposteten Unlock:
Reel „24h after“ (folge tag1) und „7 days later“ (tag7, nur wenn tag1 gepostet wurde oder |tag7| >= 10 %).
Ruhezeit 22-7 Uhr, Sperrliste, je Unlock 1 Post + hoechstens 2 Nachfolger.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import stimme, telegram, unlocks, video  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))


def sperrliste() -> set:
    p = BASIS / "sperrliste.txt"
    return {z.strip().upper() for z in p.read_text().splitlines() if z.strip() and not z.startswith("#")} if p.exists() else set()


def reel(bilder, zeilen, ordner: Path, cfg: dict, g: dict) -> str:
    toene, dauern, quelle = stimme.sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, g))
    video.bauen(bilder, toene, dauern, ordner / "video.mp4", cfg, **video.ut_formate(cfg, zeilen))
    return quelle


def main(jetzt: float | None = None, senden=None, reel_bauen=None) -> list[Path]:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    uc = cfg.get("unlocks") or {}
    if not uc.get("aktiv", True):
        return []
    jetzt = jetzt or time.time()
    gp = BASIS / "secrets.yaml"
    g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    eintraege = unlocks.laden(Path(os.environ.get("SOCIAL_DATEN", cfg["daten"]["dir"])))
    sp = AUSGABE / "unlock_post_stand.json"
    stand = json.loads(sp.read_text()) if sp.exists() else {}
    neu = unlocks.auswahl(eintraege, stand, jetzt, sperrliste(), uc.get("schon_gepostet"))
    sp.write_text(json.dumps(stand))
    send = senden or (telegram.vorschlag_senden if "--senden" in sys.argv else None)
    reel_bauen = reel_bauen or reel
    ordner = []
    for art, e in neu:
        stempel = time.strftime("%Y%m%d-%H%M", time.localtime(jetzt))
        o = AUSGABE / f"{stempel}_redaktion_unlock_{e['base']}_{art}"
        o.mkdir(parents=True, exist_ok=True)
        if art == "post":
            tx = unlocks.texte(e, cfg)
            unlocks.bild(e, cfg, o / "post.png", tx["kopf"])
            szene = unlocks.bild(e, cfg, o / "bilder" / "szene.png", tx["kopf"], H=1920)
            hinweis = f"🔓 Unlock {e['base']} ({unlocks.termin(e)}), Art: {tx['art']}"
        else:
            tx = unlocks.nachfolge_texte(e, cfg)
            szene = unlocks.nachfolge_bild(e, cfg, o / "bilder" / "szene.png", tx["kopf"])
            (o / "post.png").write_bytes(szene.read_bytes())
            hinweis = f"🔓 Nachfolge {e['base']}: {'7 Tage' if art == 'tag7' else '24 Std.'} nach dem Unlock"
        (o / "post_x.txt").write_text(tx["x"], encoding="utf-8")
        (o / "post_telegram.txt").write_text(tx["telegram"], encoding="utf-8")
        unlocks.merken(stand, art, e)
        sp.write_text(json.dumps(stand))
        ordner.append(o)
        if send:
            if art == "post":
                send(g, o, hinweis)
            vo = o if art != "post" else o.parent / f"{o.name}_video"
            vo.mkdir(exist_ok=True)
            for f in ("post_x.txt", "post_telegram.txt"):
                (vo / f).write_text((o / f).read_text(encoding="utf-8"), encoding="utf-8")
            try:
                quelle = reel_bauen([szene] * len(tx["sprech"]), tx["sprech"], vo, cfg, g)
                send(g, vo, f"{hinweis} · Reel · 🎙 Ton: {quelle}")
            except Exception as ex:
                telegram.text_senden(g, f"⚠️ Unlock-Reel {e['base']} nicht gebaut: {str(ex)[:200]}")
    if neu:
        print("Unlocks:", [(a, e["base"]) for a, e in neu])
    return ordner


if __name__ == "__main__":
    main()
