"""Abend-Erinnerung (Wunsch Tobias 05.11.2026): Welche Vorschlaege von heute sind noch ohne Knopfdruck?
Die wichtigsten (Videos und Redaktion zuerst, dann News, Rest) noch einmal kurz mit Freigabe-Knoepfen.
    sudo -u redaktion env SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe \\
      python3 tools/offen.py [--senden]
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import bericht, telegram  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))
RANG = ["redaktion", "warum_video", "wal_video", "wissen_video", "news", "coincheck", "termine", "karussell"]


def offene(ausgabe: Path, tag: dt.date) -> list[Path]:
    kurz = tag.strftime("%Y%m%d")
    out = []
    for o in ausgabe.iterdir() if ausgabe.exists() else []:
        if not o.is_dir() or not (o / "post_telegram.txt").exists():
            continue
        if not (o.name.startswith(kurz) or (o.name.startswith("chat_") and
                                             dt.date.fromtimestamp(o.stat().st_mtime) == tag)):
            continue
        st = {}
        try:
            st = json.loads((o / "gepostet.json").read_text())
        except Exception:
            pass
        if st.get("verworfen") or any(k in st for k in ("telegram", "x", "instagram", "tiktok", "youtube")):
            continue
        out.append(o)
    rang = lambda o: (RANG.index(bericht.format_aus_ordner(o.name)) if bericht.format_aus_ordner(o.name) in RANG
                      else len(RANG), o.name)
    return sorted(out, key=rang)


def kopfzeile(o: Path) -> str:
    t = (o / "post_telegram.txt").read_text(encoding="utf-8").strip().splitlines()[0]
    return re.sub(r"<[^>]+>", "", t)[:120]


def main() -> int:
    g = yaml.safe_load((BASIS / "secrets.yaml").read_text()) if (BASIS / "secrets.yaml").exists() else {}
    liste = offene(AUSGABE, dt.date.today())
    print(len(liste), "offen")
    if not liste or "--senden" not in sys.argv:
        return 0
    namen = bericht.NAMEN
    telegram.text_senden(g, f"🔔 Noch {len(liste)} Vorschläge von heute ohne Knopfdruck. Die wichtigsten, "
                            "mit Bild bzw. Video zum Ansehen:")
    for o in liste[:3]:
        fmt = bericht.format_aus_ordner(o.name)
        art = "🎬 Reel" if (o / "video.mp4").exists() else "🖼 Bild"
        hinweis = f"🔔 Erinnerung · {art} · {namen.get(fmt, fmt)}"
        # Tobias 05.11.2026: nur Text mit Knoepfen war unbrauchbar -> Bild/Video noch einmal mitschicken
        if (o / "post.png").exists() and telegram.vorschlag_senden(g, o, hinweis):
            continue
        requests.post(telegram.API.format(token=g["telegram_token"], methode="sendMessage"),
                      data={"chat_id": g["telegram_chat_id"], "text": f"📌 {hinweis}: {kopfzeile(o)}",
                            "reply_markup": json.dumps(telegram.knoepfe(o.name))}, timeout=30)
    return 0


if __name__ == "__main__":
    sys.exit(main())
