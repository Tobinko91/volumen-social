"""News-Beitrag gestalten: Bild 4:5 mit Logo, Rubrik, Schlagzeile, Quelle + Texte fuer Telegram und X."""
from __future__ import annotations

import datetime as dt
import html
from pathlib import Path

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
           f"<i>{e(cfg['hinweise']['post_text'])}</i>"]
    return {"x": x, "telegram": "\n".join(tg), "quellen_x": namen}


def bild(d: dict, gruppe: dict, cfg: dict, ziel: Path, eil: bool = False, jetzt: float | None = None) -> Path:
    from PIL import ImageDraw
    from .design import absatz, etikett, fuss, hintergrund, marke, punkte, thema_waehlen, ueberschrift, MINUS
    t = dt.datetime.fromtimestamp(jetzt or dt.datetime.now().timestamp())
    stempel = f"{t.day}. {MONATE_DE[t.month - 1]} {t.year}"
    th = thema_waehlen("eil" if eil else "news", f"{t.isoformat()}:{d['schlagzeile']}")
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=len(d["schlagzeile"]))
    marke(img, th, 80, 64, 64, untertitel=stempel)
    dr = ImageDraw.Draw(img)
    etikett(dr, th, 80, 170, ("EILMELDUNG · " if eil else "NEWS · ") + d["rubrik"].upper(),
            farbe=MINUS if eil else None)
    y = ueberschrift(dr, th, 80, 256, d["schlagzeile"], W - 160, groesse=84, max_zeilen=3) + 30
    dr.rounded_rectangle([80, y, 240, y + 8], radius=4, fill=th.akzent)
    y += 40
    y = absatz(dr, th, 80, y, d["kernsatz"], W - 160, groesse=42, gewicht="Medium") + 34
    punkte(dr, th, 80, y, d["punkte"], W - 160, groesse=33, bis_y=H - 150)
    fuss(img, th, cfg["hinweise"]["fusszeile"], quelle="Quelle: " + ", ".join(_quellen_namen(gruppe)))
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel
