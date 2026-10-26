"""Corporate Design „Nachtleuchten“ (Design 06, Website-Chat 20.10.2026) fuer alle Bilder und Videos.

Farben: Mitternacht #140F2E, Leuchtminze #3CF2C0, Flieder #B69CFF, Weiss. Schrift: Space Grotesk (OFL).
Mehrere Hintergruende (Themen), damit nicht jeder Beitrag gleich aussieht. Das Thema wird aus Datum +
Format gewaehlt: gleiche Eingabe = gleiches Bild (nachvollziehbar), aber jeden Tag ein anderes.
"""
from __future__ import annotations

import hashlib
import math
import textwrap
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HIER = Path(__file__).resolve().parent.parent
ASSETS = HIER / "assets"


def _sprache() -> str:
    try:
        import yaml
        return (yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8")) or {}).get("sprache", "en")
    except Exception:
        return "en"


SPRACHE = _sprache()   # Zahlenformat in Bildern: en = 1,234.5 / de = 1.234,5

MITTERNACHT = "#140F2E"
FLAECHE = "#1C1640"
TEXT = "#F2F0FF"
NEBEN = "#ADA5D6"
LINIE = "#342C66"
MINZE = "#3CF2C0"
FLIEDER = "#B69CFF"
MINUS = "#FF7A8F"


def rgb(c: str, a: int | None = None):
    c = c.lstrip("#")
    t = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return t + (a,) if a is not None else t


_FONTS: dict = {}


def font(gewicht: str, groesse: int) -> ImageFont.FreeTypeFont:
    """gewicht: Regular, Medium, SemiBold, Bold."""
    k = (gewicht, groesse)
    if k not in _FONTS:
        p = ASSETS / "schrift" / f"SpaceGrotesk-{gewicht}.ttf"
        _FONTS[k] = ImageFont.truetype(str(p), groesse)
    return _FONTS[k]


@dataclass
class Thema:
    name: str
    grund: str
    text: str
    neben: str
    karte: str
    linie: str
    akzent: str      # Hauptakzent (Linien, Zahlen)
    akzent2: str     # Zweitakzent
    plus: str
    minus: str
    dunkel: bool = True


THEMEN = {
    "nacht": Thema("nacht", MITTERNACHT, TEXT, NEBEN, FLAECHE, LINIE, MINZE, FLIEDER, MINZE, MINUS),
    "sonar": Thema("sonar", MITTERNACHT, TEXT, NEBEN, FLAECHE, LINIE, MINZE, FLIEDER, MINZE, MINUS),
    "tiefsee": Thema("tiefsee", "#0E0A24", TEXT, NEBEN, "#1A1440", LINIE, MINZE, FLIEDER, MINZE, MINUS),
    "flieder": Thema("flieder", "#1E1747", TEXT, "#C9C1F0", "#2A2160", "#40367A", FLIEDER, MINZE, MINZE, MINUS),
    "minze": Thema("minze", MINZE, MITTERNACHT, "#1F4F46", "#2EDDAE", "#25B890", MITTERNACHT, "#5B3FC4",
                   "#0F6B52", "#B0243F", dunkel=False),
}
# Welche Themen zu welchem Beitrag passen (Markt braucht gut lesbares Plus/Minus -> keine helle Minze)
PASSEND = {
    "markt": ["nacht", "sonar", "tiefsee", "flieder"],
    # Minze ist ein Hingucker, aber hell: seltener (1 von 7)
    "wissen": ["nacht", "sonar", "tiefsee", "flieder", "nacht", "sonar", "minze"],
    "news": ["nacht", "sonar", "tiefsee", "flieder", "nacht", "tiefsee", "minze"],
    "eil": ["nacht"],
    "video": ["nacht", "sonar", "tiefsee", "flieder"],
}


def thema_waehlen(art: str, schluessel: str) -> Thema:
    liste = PASSEND.get(art, ["nacht"])
    h = int(hashlib.sha256(f"{art}:{schluessel}".encode()).hexdigest(), 16)
    return THEMEN[liste[h % len(liste)]]


# ---------------------------------------------------------------- Hintergruende

def _leuchten(img: Image.Image, mitte, radius, farbe, staerke=70):
    """Weiches Leuchten (Nachtleuchten-Look) als unscharfer Farbfleck."""
    w, h = img.size
    ebene = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ebene)
    x, y = mitte
    d.ellipse([x - radius, y - radius, x + radius, y + radius], fill=rgb(farbe, staerke))
    ebene = ebene.filter(ImageFilter.GaussianBlur(radius * 0.45))
    img.alpha_composite(ebene)


def hintergrund(t: Thema, w: int, h: int, saat: int = 0) -> Image.Image:
    img = Image.new("RGBA", (w, h), rgb(t.grund, 255))
    d = ImageDraw.Draw(img)
    s = saat % 4
    if t.name == "nacht":
        ecken = [(w * 0.95, h * 0.05), (w * 0.05, h * 0.95), (w * 0.9, h * 0.9), (w * 0.1, h * 0.1)]
        _leuchten(img, ecken[s], w * 0.55, t.akzent, 46)
        _leuchten(img, ecken[(s + 1) % 4], w * 0.45, t.akzent2, 40)
    elif t.name == "sonar":
        cx, cy = [(w, 0), (0, h), (w, h), (0, 0)][s]
        for i in range(1, 14):
            r = i * w * 0.11
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=rgb(t.linie, 255), width=2)
        for gx in range(40, w, 54):
            for gy in range(40, h, 54):
                d.ellipse([gx - 1.5, gy - 1.5, gx + 1.5, gy + 1.5], fill=rgb(t.linie, 255))
        _leuchten(img, (cx, cy), w * 0.35, t.akzent, 34)
    elif t.name == "tiefsee":
        for y in range(h):   # Verlauf nach unten dunkler
            f = y / h
            c = tuple(int(a * (1 - f) + b * f) for a, b in zip(rgb("#1A1450"), rgb("#07051A")))
            d.line([(0, y), (w, y)], fill=c + (255,))
        for k in range(6):   # Wellenlinien
            y0 = h * (0.74 + k * 0.035)   # unten, damit keine Linie durch den Text laeuft
            punkte = [(x, y0 + math.sin(x / w * math.pi * 3 + k + s) * 18) for x in range(0, w + 10, 10)]
            d.line(punkte, fill=rgb(t.akzent, 18 + k * 6), width=2)
    elif t.name == "flieder":
        _leuchten(img, (w * (0.2 + 0.6 * (s % 2)), h * 0.15), w * 0.6, t.akzent, 70)
        for i in range(0, w + h, 46):   # feine Diagonalen
            d.line([(i, 0), (i - h, h)], fill=rgb(t.linie, 110), width=1)
    elif t.name == "minze":
        for gx in range(36, w, 48):
            for gy in range(36, h, 48):
                d.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=rgb(t.linie, 255))
    return img


# ---------------------------------------------------------------- Bausteine

_LOGO = None


def logo(groesse: int) -> Image.Image:
    """Runde Plakette aus volumen-web/static/logo-1080.png (Design 06)."""
    global _LOGO
    if _LOGO is None:
        _LOGO = Image.open(ASSETS / "logo-1080.png").convert("RGBA")
    return _LOGO.resize((groesse, groesse), Image.LANCZOS)


def marke(img: Image.Image, t: Thema, x: int, y: int, groesse: int = 64, untertitel: str | None = None):
    """Logo + Schriftzug 'Whale' + 'Squeeze' (wie logo-schriftzug.svg)."""
    img.alpha_composite(logo(groesse), (x, y))
    d = ImageDraw.Draw(img)
    f = font("Bold", int(groesse * 0.56))
    tx, ty = x + groesse + 18, y + int(groesse * 0.16)
    d.text((tx, ty), "Whale", font=f, fill=t.text)
    d.text((tx + d.textlength("Whale", font=f), ty), "Squeeze", font=f, fill=t.akzent if t.dunkel else MITTERNACHT)
    if untertitel:
        fu = font("Medium", 26)
        d.text((img.width - 80 - d.textlength(untertitel, font=fu), y + groesse * 0.3), untertitel, font=fu,
               fill=t.neben)


def etikett(d: ImageDraw.ImageDraw, t: Thema, x: int, y: int, text: str, farbe: str | None = None) -> int:
    f = font("Bold", 28)
    farbe = farbe or t.akzent2
    w = d.textlength(text, font=f) + 44
    d.rounded_rectangle([x, y, x + w, y + 54], radius=27, outline=rgb(farbe), width=3)
    d.text((x + 22, y + 10), text, font=f, fill=farbe)
    return int(w)


def umbruch(d, text: str, f, breite_px: int) -> list[str]:
    """Zeilenumbruch nach echter Textbreite."""
    # Zahl und Einheit nie trennen ("−50 %", "100.000 €")
    text = text.replace(" %", "\u00a0%").replace(" €", "\u00a0€")
    woerter, zeilen, z = [w for w in text.split(" ") if w], [], ""
    for w in woerter:
        probe = f"{z} {w}".strip()
        if d.textlength(probe, font=f) <= breite_px:
            z = probe
        else:
            if z:
                zeilen.append(z)
            z = w
    if z:
        zeilen.append(z)
    return zeilen


def ueberschrift(d, t: Thema, x: int, y: int, text: str, breite: int, groesse=74, max_zeilen=3) -> int:
    while groesse > 44:
        f = font("Bold", groesse)
        zeilen = umbruch(d, text, f, breite)
        if len(zeilen) <= max_zeilen:
            break
        groesse -= 4
    for z in zeilen[:max_zeilen + 1]:
        d.text((x, y), z, font=f, fill=t.text)
        y += int(groesse * 1.12)
    return y


def absatz(d, t: Thema, x: int, y: int, text: str, breite: int, groesse=32, farbe=None, gewicht="Regular",
           abstand=1.35) -> int:
    f = font(gewicht, groesse)
    for z in umbruch(d, text, f, breite):
        d.text((x, y), z, font=f, fill=farbe or t.text)
        y += int(groesse * abstand)
    return y


def punkte(d, t: Thema, x: int, y: int, liste: list[str], breite: int, groesse=31, bis_y: int = 10_000) -> int:
    f = font("Regular", groesse)
    for p in liste:
        zeilen = umbruch(d, p, f, breite - 40)
        if y + len(zeilen) * groesse * 1.35 > bis_y:
            break
        d.rounded_rectangle([x, y + groesse * 0.35, x + 14, y + groesse * 0.35 + 14], radius=4, fill=t.akzent)
        for i, z in enumerate(zeilen):
            d.text((x + 36, y + i * int(groesse * 1.35)), z, font=f, fill=t.text)
        y += len(zeilen) * int(groesse * 1.35) + 20
    return y


def fuss(img: Image.Image, t: Thema, hinweis: str, quelle: str | None = None):
    d = ImageDraw.Draw(img)
    w, h = img.size
    y = h - 128 if quelle else h - 96
    d.line([(80, y), (w - 80, y)], fill=t.linie, width=2)
    y += 18
    if quelle:
        d.text((80, y), quelle, font=font("SemiBold", 26), fill=t.text)
        y += 36
    d.text((80, y), hinweis, font=font("Medium", 24), fill=t.neben)
    f = font("Bold", 26)
    d.text((w - 80 - d.textlength("whalesqueeze.com", font=f), y - 2), "whalesqueeze.com", font=f,
           fill=t.akzent if t.dunkel else MITTERNACHT)


def karte(img: Image.Image, t: Thema, box, radius=28):
    """Halbtransparente Karte (laesst den Hintergrund durchscheinen)."""
    ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ebene).rounded_rectangle(box, radius=radius, fill=rgb(t.karte, 215),
                                            outline=rgb(t.linie, 255), width=2)
    img.alpha_composite(ebene)


def de(x: float, stellen: int = 1, lang: str | None = None) -> str:
    """Zahl mit Tausendertrennung in der Sprache der Kanaele (Name aus der deutschen Zeit)."""
    s = f"{x:,.{stellen}f}"
    if (lang or SPRACHE) == "de":
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s
