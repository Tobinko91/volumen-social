"""News-Beitrag gestalten: Bild 4:5 mit Logo, Rubrik, Schlagzeile, Quelle + Texte fuer Telegram und X."""
from __future__ import annotations

import datetime as dt
import html
import textwrap
from pathlib import Path

from .bilder import Leinwand, _font
from .sprache import MONATE_DE

X_MAX = 280


def _quellen_namen(gruppe: dict, n: int = 3) -> list[str]:
    return gruppe["quellen"][:n]


def texte(d: dict, gruppe: dict, cfg: dict, eil: bool = False) -> dict:
    namen = _quellen_namen(gruppe)
    kopf = "🚨 EILMELDUNG: " if eil else ""
    x = f"{kopf}{d['x']}\nQuelle: {', '.join(namen)}\nKeine Anlageberatung."
    while len(x) > X_MAX and len(namen) > 1:
        namen = namen[:-1]
        x = f"{kopf}{d['x']}\nQuelle: {', '.join(namen)}\nKeine Anlageberatung."
    e = html.escape
    links = []
    for q in gruppe["quellen"][:4]:
        m = next(m for m in gruppe["meldungen"] if m["quelle"] == q)
        links.append(f'<a href="{e(m["link"], quote=True)}">{e(q)}</a>')
    tg = [f"{'🚨 ' if eil else '📰 '}<b>{e(d['schlagzeile'])}</b>", "", e(d["kernsatz"]), ""]
    tg += [f"• {e(p)}" for p in d["punkte"]]
    tg += ["", "Quellen: " + ", ".join(links), "",
           f"<i>{e(cfg['hinweise']['fusszeile'])}. {e(cfg['hinweise']['konflikt'])}</i>"]
    return {"x": x, "telegram": "\n".join(tg), "quellen_x": namen}


def bild(d: dict, gruppe: dict, cfg: dict, ziel: Path, eil: bool = False, jetzt: float | None = None) -> Path:
    c = dict(cfg)
    c["video"] = dict(cfg["video"], hoehe=1350)
    lw = Leinwand(c)
    img, dr = lw.neu()
    lw.logo(dr, 80, 70, 2.0)
    dr.text((160, 77), "WHALESQUEEZE", font=_font("Bold", 38), fill=lw.f["text"])
    t = dt.datetime.fromtimestamp(jetzt or dt.datetime.now().timestamp())
    stempel = f"{t.day}. {MONATE_DE[t.month - 1]} {t.year}"
    fs = _font("Medium", 30)
    dr.text((lw.W - 80 - dr.textlength(stempel, font=fs), 82), stempel, font=fs, fill=lw.f["neben"])

    y = 170
    etikett = ("EILMELDUNG · " if eil else "NEWS · ") + d["rubrik"].upper()
    fe = _font("Bold", 32)
    w = dr.textlength(etikett, font=fe) + 50
    farbe = lw.f["minus"] if eil else lw.f["amber"]
    dr.rounded_rectangle([80, y, 80 + w, y + 58], radius=29, outline=farbe, width=3)
    dr.text((105, y + 11), etikett, font=fe, fill=farbe)
    y += 100

    groesse, breite = 70, 22
    zeilen = textwrap.wrap(d["schlagzeile"], width=breite)
    while len(zeilen) > 3 and groesse > 50:
        groesse, breite = groesse - 6, breite + 3
        zeilen = textwrap.wrap(d["schlagzeile"], width=breite)
    for z in zeilen[:4]:
        dr.text((80, y), z, font=_font("Black", groesse), fill=lw.f["text"])
        y += int(groesse * 1.18)
    y += 30

    dr.rounded_rectangle([80, y, lw.W - 80, y + 10], radius=5, fill=lw.f["amber"])
    y += 40
    for z in textwrap.wrap(d["kernsatz"], width=40)[:4]:
        dr.text((80, y), z, font=_font("SemiBold", 40), fill=lw.f["text"])
        y += 52
    y += 24
    fp = _font("Medium", 32)
    for p in d["punkte"]:
        zeilen = textwrap.wrap(p, width=52)[:3]
        if y + len(zeilen) * 42 > 1180:
            break
        dr.ellipse([84, y + 13, 100, y + 29], fill=lw.f["amber"])
        for i, z in enumerate(zeilen):
            dr.text((120, y + i * 42), z, font=fp, fill=lw.f["neben"])
        y += len(zeilen) * 42 + 22

    dr.line([(80, 1205), (lw.W - 80, 1205)], fill=lw.f["linie"], width=2)
    dr.text((80, 1222), "Quelle: " + ", ".join(_quellen_namen(gruppe)), font=_font("SemiBold", 28), fill=lw.f["text"])
    dr.text((80, 1260), cfg["hinweise"]["fusszeile"], font=_font("Medium", 26), fill=lw.f["neben"])
    dr.text((80, 1295), "whalesqueeze.com", font=_font("Bold", 28), fill=lw.f["amber"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.save(ziel)
    return ziel
