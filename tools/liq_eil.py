"""S24 Liquiditaets-Eilmeldungen (Wunsch Tobias 06.11.2026), alle 10 Minuten aus tools/live.sh.

Neue Eintraege in /opt/volumen-bot/web/liquiditaet.json -> eilmeldungen[] (Pump/Dump, vom Bot erkannt) werden ein
„BREAKING“-Bild + Reel mit geschaetzten Liquiditaetszonen und Heatmap. Grenzen: je Coin hoechstens 1 in 12 Std.,
hoechstens 4 am Tag (liquiditaet.eil_max_tag), Ruhezeit 22-7 Uhr, nie Coins der Sperrliste.
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
from social import liquiditaet, telegram  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))


def sperrliste() -> set:
    p = BASIS / "sperrliste.txt"
    return {z.strip().upper() for z in p.read_text().splitlines() if z.strip() and not z.startswith("#")} if p.exists() else set()


def main(jetzt: float | None = None, senden=None, reel_bauen=None) -> list[Path]:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    lc = cfg.get("liquiditaet") or {}
    if not lc.get("eil_aktiv", True):
        return []
    jetzt = jetzt or time.time()
    gp = BASIS / "secrets.yaml"
    g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    d = liquiditaet.laden(Path(os.environ.get("SOCIAL_DATEN", cfg["daten"]["dir"])))
    sp = AUSGABE / "liq_eil_stand.json"
    stand = json.loads(sp.read_text()) if sp.exists() else {}
    neu = liquiditaet.eil_auswahl(d, stand, jetzt, sperrliste(), int(lc.get("eil_max_tag", 4)))
    ordner = []
    for e in neu:
        o = AUSGABE / f"{time.strftime('%Y%m%d-%H%M', time.localtime(jetzt))}_redaktion_liq_{e['base']}"
        b = liquiditaet.beitrag(e, o, cfg, d.get("pruefung"), eil=True)
        liquiditaet.eil_merken(stand, e, jetzt)
        sp.write_text(json.dumps(stand))
        ordner.append(o)
        if "--senden" in sys.argv or senden:
            send = senden or telegram.vorschlag_senden
            send(g, o, f"💧 Liquiditaets-Eilmeldung: {e['base']} {e.get('anlass', '')} (Zonen geschaetzt, Daten vom Bot)")
            try:
                ro = o.parent / f"{o.name}_video"
                ro.mkdir(exist_ok=True)
                for f in ("post_x.txt", "post_telegram.txt"):
                    (ro / f).write_text((o / f).read_text(encoding="utf-8"), encoding="utf-8")
                _, quelle = (reel_bauen or liquiditaet.reel)(b, ro, cfg, g)
                send(g, ro, f"💧 {e['base']} als Reel · 🎙 Ton: {quelle}")
            except Exception as ex:
                telegram.text_senden(g, f"⚠️ Liquiditaets-Reel {e['base']} nicht gebaut: {str(ex)[:200]}")
    if neu:
        print("Liquiditaets-Eilmeldungen:", [e["base"] for e in neu])
    return ordner


if __name__ == "__main__":
    main()
