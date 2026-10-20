"""Bilder 1080x1920 je Szene (gesichtslos: Zahlen, Balken, Untertitel).

Sichere Zonen fuer TikTok/Reels/Shorts: oben ~200 px und unten ~380 px sowie rechts ~140 px
werden von den App-Knoepfen verdeckt. Wichtige Inhalte liegen dazwischen.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .sprache import T, zahl

FONT_ORDNER = [
    Path("/usr/share/fonts/opentype/inter"),
    Path(__file__).resolve().parent.parent / "fonts",
]
FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(gewicht: str, groesse: int) -> ImageFont.FreeTypeFont:
    for o in FONT_ORDNER:
        p = o / f"Inter-{gewicht}.otf"
        if p.exists():
            return ImageFont.truetype(str(p), groesse)
    return ImageFont.truetype(FALLBACK, groesse)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


class Leinwand:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.W, self.H = cfg["video"]["breite"], cfg["video"]["hoehe"]
        self.f = {k: _hex(v) for k, v in cfg["farben"].items()}
        self.lang = cfg.get("sprache", "de")
        self.t = T[self.lang]

    def neu(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (self.W, self.H), self.f["grund"])
        return img, ImageDraw.Draw(img)

    # ---------- Bausteine ----------
    def mitte(self, d, y, text, font, farbe):
        w = d.textlength(text, font=font)
        d.text(((self.W - w) / 2, y), text, font=font, fill=farbe)

    def logo(self, d, x, y, s=2.2):
        a = self.f["amber"]
        d.rounded_rectangle([x + 3 * s, y + 3 * s, x + 29 * s, y + 6.5 * s], radius=1.75 * s, fill=a)
        d.rounded_rectangle([x + 3 * s, y + 25.5 * s, x + 29 * s, y + 29 * s], radius=1.75 * s, fill=a)
        flosse = [(16, 23.5), (15.2, 19.5), (14.6, 15.9), (11, 15.6), (7, 12.5), (11.5, 12.1), (15.1, 10.2),
                  (16, 10.0), (16.9, 10.2), (20.5, 12.1), (25, 12.5), (21, 15.6), (17.4, 15.9), (16.8, 19.5)]
        d.polygon([(x + px * s, y + py * s) for px, py in flosse], fill=(0x5E, 0xA4, 0xBD))

    def kopf(self, d):
        """Marke + feste Fusszeile (Risiko- und KI-Hinweis) oben in der sicheren Zone."""
        self.logo(d, 90, 215, 2.0)
        d.text((170, 222), "WHALESQUEEZE", font=_font("Bold", 38), fill=self.f["text"])
        d.text((90, 300), self.cfg["hinweise"]["fusszeile"], font=_font("Medium", 31), fill=self.f["neben"])
        d.line([(90, 348), (self.W - 90, 348)], fill=self.f["linie"], width=2)

    def untertitel(self, d, text, y=1230):
        """Gesprochener Satz als Untertitel (wichtig: viele schauen ohne Ton)."""
        font = _font("SemiBold", 50)
        text = text.replace(self.t["adresse_gesprochen"], ".com")   # Stimme sagt "Punkt com", Bild zeigt die Adresse
        zeilen = textwrap.wrap(text, width=30)[:4]
        hoehe = len(zeilen) * 66 + 50
        d.rounded_rectangle([70, y, self.W - 70, y + hoehe], radius=28, fill=self.f["flaeche"])
        for i, z in enumerate(zeilen):
            self.mitte(d, y + 25 + i * 66, z, font, self.f["text"])

    def farbe_wert(self, x):
        return self.f["plus"] if x >= 0 else self.f["minus"]

    # ---------- Szenen ----------
    def titel(self, daten, text):
        img, d = self.neu()
        self.kopf(d)
        self.mitte(d, 560, self.t["b_markt"], _font("Black", 104), self.f["text"])
        self.mitte(d, 690, self.t["b_30s"], _font("Black", 104), self.f["amber"])
        self.mitte(d, 860, daten["datum"].upper(), _font("SemiBold", 54), self.f["neben"])
        self.untertitel(d, text)
        return img

    def breite(self, daten, text):
        img, d = self.neu()
        self.kopf(d)
        m = daten["median_24h"]
        self.mitte(d, 440, self.t["b_breite"], _font("Bold", 44), self.f["neben"])
        self.mitte(d, 520, f"{zahl(m, self.lang, True)} %", _font("Black", 200), self.farbe_wert(m))
        self.mitte(d, 780, self.t["b_median"].format(anzahl=daten["anzahl"]), _font("Medium", 44), self.f["neben"])
        # Balken gruen/rot
        x0, x1, y0 = 120, self.W - 120, 900
        teil = x0 + (x1 - x0) * daten["anteil_plus"] / 100
        d.rounded_rectangle([x0, y0, x1, y0 + 56], radius=28, fill=self.f["minus"])
        if daten["anteil_plus"] > 0:
            d.rounded_rectangle([x0, y0, max(teil, x0 + 56), y0 + 56], radius=28, fill=self.f["plus"])
        f = _font("Bold", 40)
        d.text((x0, y0 + 80), self.t["b_plus"].format(p=daten["anteil_plus"]), font=f, fill=self.f["plus"])
        rot = self.t["b_minus"].format(p=100 - daten["anteil_plus"])
        d.text((x1 - d.textlength(rot, font=f), y0 + 80), rot, font=f, fill=self.f["minus"])
        self.untertitel(d, text)
        return img

    def mover(self, daten, text, nr=None, von=None):
        img, d = self.neu()
        self.kopf(d)
        if nr:
            self.mitte(d, 430, self.t["b_mover"].format(nr=nr, von=von), _font("Bold", 44), self.f["neben"])
        self.mitte(d, 500, daten["base"], _font("Black", 180), self.f["text"])
        c = daten["chg24"]
        self.mitte(d, 710, f"{zahl(c, self.lang, True)} %  {self.t['b_24h']}", _font("Black", 100), self.farbe_wert(c))
        grund = self.t["b_ausloeser"].format(a=daten["ausloeser"]).upper() if daten.get("ausloeser") else self.t["b_keine"]
        groesse = 38
        f = _font("Bold", groesse)
        while d.textlength(grund, font=f) + 70 > self.W - 160 and groesse > 24:
            groesse -= 2
            f = _font("Bold", groesse)
        w = d.textlength(grund, font=f) + 70
        x = (self.W - w) / 2
        farbe = self.f["amber"] if daten.get("ausloeser") else self.f["neben"]
        d.rounded_rectangle([x, 900, x + w, 976], radius=38, outline=farbe, width=4)
        d.text((x + 35, 917), grund, font=f, fill=farbe)
        self.untertitel(d, text)
        return img

    def outro(self, daten, text):
        img, d = self.neu()
        self.kopf(d)
        self.logo(d, (self.W - 32 * 7) / 2, 420, 7)
        self.mitte(d, 690, "whalesqueeze.com", _font("Black", 92), self.f["amber"])
        self.mitte(d, 820, self.t["b_outro"], _font("SemiBold", 46), self.f["text"])
        konflikt = textwrap.wrap(self.cfg["hinweise"]["konflikt"], width=48)
        for i, z in enumerate(konflikt):
            self.mitte(d, 930 + i * 44, z, _font("Medium", 34), self.f["neben"])
        self.untertitel(d, text)
        return img


def zeichnen(beitrag: dict, zeilen: list[str], ordner: Path, cfg: dict) -> list[Path]:
    lw = Leinwand(cfg)
    ordner.mkdir(parents=True, exist_ok=True)
    movers = [s for s in beitrag["szenen"] if s["typ"] == "mover"]
    dateien = []
    for i, (s, z) in enumerate(zip(beitrag["szenen"], zeilen)):
        if s["typ"] == "mover":
            img = lw.mover(s["daten"], z, movers.index(s) + 1, len(movers))
        else:
            img = getattr(lw, s["typ"])(s["daten"], z)
        p = ordner / f"bild_{i:02d}.png"
        img.save(p)
        dateien.append(p)
    return dateien
