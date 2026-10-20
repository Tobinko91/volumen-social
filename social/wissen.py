"""Lern-Beitraege (Trading lernen, Kaufzonen verstehen, Weg zu 100.000 €, Betrug) als Bild + Text.
Die Themen stehen in inhalte/wissen.yaml. Reihenfolge: das am laengsten nicht gezeigte Thema zuerst."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import yaml

from .bilder import Leinwand, _font

HIER = Path(__file__).resolve().parent.parent


def themen() -> list[dict]:
    return yaml.safe_load((HIER / "inhalte" / "wissen.yaml").read_text(encoding="utf-8"))


def naechstes(stand_datei: Path, thema_id: str | None = None) -> dict:
    alle = themen()
    if thema_id:
        return next(t for t in alle if t["id"] == thema_id)
    stand = json.loads(stand_datei.read_text()) if stand_datei.exists() else {}
    return min(alle, key=lambda t: stand.get(t["id"], 0))


def merken(stand_datei: Path, thema_id: str, ts: float) -> None:
    stand = json.loads(stand_datei.read_text()) if stand_datei.exists() else {}
    stand[thema_id] = ts
    stand_datei.write_text(json.dumps(stand, indent=1))


def texte(t: dict, cfg: dict) -> dict:
    tg = [f"📚 <b>{t['titel']}</b>", ""]
    tg += [f"• {p}" for p in t["punkte"]]
    tg += ["", f"<i>{cfg['hinweise']['fusszeile']}. {cfg['hinweise']['konflikt']}</i>"]
    return {"x": t["x"], "telegram": "\n".join(tg)}


def bild(t: dict, cfg: dict, ziel: Path) -> Path:
    c = dict(cfg)
    c["video"] = dict(cfg["video"], hoehe=1350)
    lw = Leinwand(c)
    img, d = lw.neu()
    lw.logo(d, 80, 70, 2.0)
    d.text((160, 77), "WHALESQUEEZE", font=_font("Bold", 38), fill=lw.f["text"])
    d.text((80, 150), t["saeule"].upper(), font=_font("Bold", 34), fill=lw.f["amber"])
    y = 200
    for z in textwrap.wrap(t["titel"], width=24)[:3]:
        d.text((80, y), z, font=_font("Black", 62), fill=lw.f["text"])
        y += 74
    y += 30
    d.rounded_rectangle([80, y, lw.W - 80, y + 250], radius=28, fill=lw.f["flaeche"])
    groesse = 120
    fg = _font("Black", groesse)
    while d.textlength(t["gross"], font=fg) > lw.W - 240 and groesse > 60:
        groesse -= 8
        fg = _font("Black", groesse)
    d.text((115, y + 25), t["gross"], font=fg, fill=lw.f["amber"])
    for i, z in enumerate(textwrap.wrap(t["gross_text"], width=44)[:2]):
        d.text((115, y + 170 + i * 38), z, font=_font("Medium", 32), fill=lw.f["neben"])
    y += 290
    fp = _font("Medium", 33)
    for p in t["punkte"]:
        zeilen = textwrap.wrap(p, width=50)[:3]
        d.ellipse([84, y + 14, 100, y + 30], fill=lw.f["amber"])
        for i, z in enumerate(zeilen):
            d.text((120, y + i * 42), z, font=fp, fill=lw.f["text"])
        y += len(zeilen) * 42 + 26
    d.line([(80, 1225), (lw.W - 80, 1225)], fill=lw.f["linie"], width=2)
    d.text((80, 1243), cfg["hinweise"]["fusszeile"], font=_font("Medium", 28), fill=lw.f["neben"])
    d.text((80, 1285), "whalesqueeze.com", font=_font("Bold", 30), fill=lw.f["amber"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.save(ziel)
    return ziel
