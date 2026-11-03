"""Grafiken fuer Beitraege: Balken, Linien, Schemas. Alles selbst gezeichnet im Nachtleuchten-Design."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .design import Thema, de, font, karte, rgb



def _w(de_text: str, en_text: str) -> str:
    """Beschriftung in der Kanal-Sprache."""
    from . import design
    return de_text if design.SPRACHE == "de" else en_text

def balken(img: Image.Image, t: Thema, box, reihen: list[dict], titel: str | None = None, einheit: str = ""):
    """Waagerechte Balken. reihen: [{label, wert, farbe?, text?}]"""
    x0, y0, x1, y1 = box
    karte(img, t, box)
    d = ImageDraw.Draw(img)
    y = y0 + 30
    if titel:
        d.text((x0 + 36, y), titel, font=font("Medium", 26), fill=t.neben)
        y += 52
    n = len(reihen)
    hoehe = (y1 - 30 - y) / n
    maxw = max(abs(r["wert"]) for r in reihen) or 1
    fl, fw = font("SemiBold", 30), font("Bold", 34)
    label_b = max(d.textlength(r["label"], font=fl) for r in reihen) + 24
    bx0, bx1 = x0 + 36 + label_b, x1 - 36
    for i, r in enumerate(reihen):
        cy = y + i * hoehe + hoehe / 2
        d.text((x0 + 36, cy - 18), r["label"], font=fl, fill=t.text)
        txt = r.get("text") or f"{de(r['wert'], 1 if r['wert'] % 1 else 0)}{einheit}"
        tw = d.textlength(txt, font=fw)
        platz = bx1 - bx0 - tw - 20
        lang = max(10, platz * abs(r["wert"]) / maxw)
        bh = min(46, hoehe * 0.55)
        farbe = r.get("farbe") or t.akzent
        d.rounded_rectangle([bx0, cy - bh / 2, bx0 + lang, cy + bh / 2], radius=bh / 2, fill=farbe)
        d.text((bx0 + lang + 16, cy - 21), txt, font=fw, fill=farbe)


def linien(img: Image.Image, t: Thema, box, reihen: list[dict], x_labels: list[str], titel: str | None = None,
           y_min: float | None = None, y_max: float | None = None, einheit: str = "", flaeche: bool = True):
    """Linien mit Endwert-Beschriftung. reihen: [{name, werte, farbe}]"""
    x0, y0, x1, y1 = box
    karte(img, t, box)
    d = ImageDraw.Draw(img)
    top = y0 + 30
    if titel:
        d.text((x0 + 36, top), titel, font=font("Medium", 26), fill=t.neben)
        top += 56
    alle = [v for r in reihen for v in r["werte"]]
    lo = y_min if y_min is not None else min(alle)
    hi = y_max if y_max is not None else max(alle)
    px0, px1, py0, py1 = x0 + 50, x1 - 200, top + 20, y1 - 70
    n = len(reihen[0]["werte"])

    def pt(i, v):
        return (px0 + (px1 - px0) * i / (n - 1), py1 - (py1 - py0) * (v - lo) / ((hi - lo) or 1))

    for k in range(5):   # Hilfslinien
        yy = py0 + (py1 - py0) * k / 4
        d.line([(px0, yy), (px1, yy)], fill=t.linie, width=1)
    fx = font("Medium", 24)
    for i, lab in enumerate(x_labels):
        if lab:
            xx = px0 + (px1 - px0) * i / (len(x_labels) - 1)
            d.text((xx - d.textlength(lab, font=fx) / 2, py1 + 18), lab, font=fx, fill=t.neben)
    for r in reihen:
        pts = [pt(i, v) for i, v in enumerate(r["werte"])]
        if flaeche:
            ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(ebene).polygon(pts + [(pts[-1][0], py1), (pts[0][0], py1)], fill=rgb(r["farbe"], 40))
            img.alpha_composite(ebene)
            d = ImageDraw.Draw(img)
        d.line(pts, fill=r["farbe"], width=6, joint="curve")
        ex, ey = pts[-1]
        d.ellipse([ex - 10, ey - 10, ex + 10, ey + 10], fill=r["farbe"])
        wert = r.get("endtext") or f"{de(r['werte'][-1])}{einheit}"
        d.text((ex + 22, ey - 34), wert, font=font("Bold", 34), fill=r["farbe"])
        d.text((ex + 22, ey + 4), r["name"], font=font("Medium", 22), fill=t.neben)


def schema(img: Image.Image, t: Thema, box, art: str):
    """Schematische Kursbilder zum Erklaeren (keine echten Kurse, darum 'Schema' beschriftet)."""
    x0, y0, x1, y1 = box
    karte(img, t, box)
    d = ImageDraw.Draw(img)
    w, h = x1 - x0, y1 - y0
    fl = font("SemiBold", 26)

    def P(fx, fy):
        return (x0 + 40 + (w - 80) * fx, y0 + 40 + (h - 100) * fy)

    if art == "unterstuetzung":
        # Zonen
        for fy, name, farbe in [(0.2, _w("Widerstand", "Resistance"), t.minus), (0.78, _w("Unterstützung", "Support"), t.plus)]:
            a, b = P(0, fy - 0.06), P(1, fy + 0.06)
            ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(ebene).rectangle([a, b], fill=rgb(farbe, 50))
            img.alpha_composite(ebene)
            d = ImageDraw.Draw(img)
            d.text((a[0] + 10, a[1] - 34 if fy < 0.5 else b[1] + 6), name, font=fl, fill=farbe)
        kurs = [0.5, 0.3, 0.22, 0.4, 0.62, 0.77, 0.6, 0.42, 0.25, 0.21, 0.45, 0.7, 0.78, 0.66, 0.5]
        pts = [P(i / (len(kurs) - 1), v) for i, v in enumerate(kurs)]
        d.line(pts, fill=t.text, width=5, joint="curve")
        for i in (2, 9):
            d.ellipse([pts[i][0] - 9, pts[i][1] - 9, pts[i][0] + 9, pts[i][1] + 9], fill=t.minus)
        for i in (5, 12):
            d.ellipse([pts[i][0] - 9, pts[i][1] - 9, pts[i][0] + 9, pts[i][1] + 9], fill=t.plus)
    elif art == "liquiditaet":
        tief = 0.62
        a, b = P(0.05, tief + 0.02), P(0.72, tief + 0.12)
        ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(ebene).rectangle([a, b], fill=rgb(t.akzent2, 60))
        img.alpha_composite(ebene)
        d = ImageDraw.Draw(img)
        d.text((a[0] + 10, b[1] + 6), _w("viele Stops = Liquidität", "many stops = liquidity"), font=fl, fill=t.akzent2)
        kurs = [0.3, 0.45, 0.6, 0.48, 0.35, 0.5, 0.61, 0.47, 0.4, 0.55, 0.78, 0.5, 0.3, 0.18]
        pts = [P(i / (len(kurs) - 1), v) for i, v in enumerate(kurs)]
        d.line(pts, fill=t.text, width=5, joint="curve")
        sx, sy = pts[10]
        d.ellipse([sx - 11, sy - 11, sx + 11, sy + 11], fill=t.akzent)
        txt = _w("Stops geholt, dann Wende", "stops taken, then reversal")
        tx = sx + 20 if sx + 20 + d.textlength(txt, font=fl) < x1 - 30 else sx - 20 - d.textlength(txt, font=fl)
        d.text((tx, sy + 14), txt, font=fl, fill=t.akzent)
    elif art == "pump":
        kurs = [0.82, 0.8, 0.81, 0.79, 0.8, 0.72, 0.55, 0.3, 0.1, 0.15, 0.45, 0.75, 0.85, 0.88]
        pts = [P(i / (len(kurs) - 1), v) for i, v in enumerate(kurs)]
        for (i0, i1, name, farbe) in [(0, 4, "1 Sammeln", t.akzent2), (4, 8, "2 Bewerben", t.akzent),
                                      (8, 13, "3 Verkaufen", t.minus)]:
            d.line(pts[i0:i1 + 1], fill=farbe, width=6, joint="curve")
            mx = (pts[i0][0] + pts[i1][0]) / 2
            d.text((mx - d.textlength(name, font=fl) / 2, y1 - 52), name, font=fl, fill=farbe)
    sch = _w("Schema", "Illustration")
    d.text((x1 - 40 - d.textlength(sch, font=font("Medium", 22)), y0 + 22), sch,
           font=font("Medium", 22), fill=t.neben)


def liste_x(img: Image.Image, t: Thema, box, eintraege: list[str]):
    """Warnliste mit X-Zeichen (z. B. Fake-Guru)."""
    x0, y0, x1, y1 = box
    karte(img, t, box)
    d = ImageDraw.Draw(img)
    hoehe = (y1 - y0 - 40) / len(eintraege)
    for i, e in enumerate(eintraege):
        cy = y0 + 20 + i * hoehe + hoehe / 2
        cx = x0 + 60
        d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], outline=t.minus, width=3)
        d.line([(cx - 9, cy - 9), (cx + 9, cy + 9)], fill=t.minus, width=4)
        d.line([(cx - 9, cy + 9), (cx + 9, cy - 9)], fill=t.minus, width=4)
        d.text((cx + 46, cy - 20), e, font=font("SemiBold", 32), fill=t.text)


def anteil(img: Image.Image, t: Thema, box, plus: int):
    """Ring: Anteil im Plus / im Minus."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    r = min(x1 - x0, y1 - y0) / 2
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bb = [cx - r, cy - r, cx + r, cy + r]
    d.arc(bb, 0, 360, fill=t.minus, width=int(r * 0.22))
    d.arc(bb, -90, -90 + 360 * plus / 100, fill=t.plus, width=int(r * 0.22))
    f = font("Bold", int(r * 0.5))
    s = f"{plus}" + _w(" %", "%")
    d.text((cx - d.textlength(s, font=f) / 2, cy - r * 0.36), s, font=f, fill=t.text)
    fs = font("Medium", int(r * 0.17))
    lab = _w("im Plus", "green")
    d.text((cx - d.textlength(lab, font=fs) / 2, cy + r * 0.2), lab, font=fs, fill=t.neben)
    _ = math


def mover_linien(img: Image.Image, t: Thema, box, mover: list[dict], titel: str | None = None):
    """Je Coin eine Zeile: Name, Kursverlauf (Linie), Veraenderung 24 Std. mover: [{base, chg24, verlauf, text}]"""
    x0, y0, x1, y1 = box
    karte(img, t, box)
    d = ImageDraw.Draw(img)
    y = y0 + 28
    if titel:
        d.text((x0 + 36, y), titel, font=font("Medium", 26), fill=t.neben)
        y += 50
    hoehe = (y1 - 24 - y) / max(1, len(mover))
    fn, fw = font("Bold", 38), font("Bold", 36)
    for i, m in enumerate(mover):
        top = y + i * hoehe
        farbe = t.plus if m["chg24"] >= 0 else t.minus
        d.text((x0 + 36, top + hoehe / 2 - 24), m["base"], font=fn, fill=t.text)
        tw = d.textlength(m["text"], font=fw)
        d.text((x1 - 36 - tw, top + hoehe / 2 - 22), m["text"], font=fw, fill=farbe)
        lx0, lx1 = x0 + 220, x1 - 72 - tw
        ly0, ly1 = top + 14, top + hoehe - 14
        werte = [v for _, v in m.get("verlauf") or []]
        if len(werte) >= 2:
            lo, hi = min(werte), max(werte)
            pts = [(lx0 + (lx1 - lx0) * k / (len(werte) - 1), ly1 - (ly1 - ly0) * (v - lo) / ((hi - lo) or 1))
                   for k, v in enumerate(werte)]
            ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(ebene).polygon(pts + [(lx1, ly1), (lx0, ly1)], fill=rgb(farbe, 36))
            img.alpha_composite(ebene)
            d = ImageDraw.Draw(img)
            d.line(pts, fill=farbe, width=4, joint="curve")
            d.ellipse([pts[-1][0] - 7, pts[-1][1] - 7, pts[-1][0] + 7, pts[-1][1] + 7], fill=farbe)
        if i < len(mover) - 1:
            d.line([(x0 + 36, top + hoehe), (x1 - 36, top + hoehe)], fill=t.linie, width=1)


# ---------------------------------------------------------------- Lern-Videos: Kerzen-Schema Schritt fuer Schritt
# Wunsch Tobias 03.11.2026: Erklaervideos (z. B. Liquiditaetszone) muessen zeigen, wo das im Chart liegt.
# Schematische Kerzen (keine echten Kurse, darum „Illustration“), je Punkt des Themas ein weiterer Schritt.

def _kerzen(pfad: list[float]) -> list[tuple[float, float, float, float]]:
    """Schlusskurse -> Kerzen (open, high, low, close), alles 0..1 (1 = oben)."""
    out, vorher = [], pfad[0]
    for c in pfad:
        o = vorher
        out.append((o, max(o, c) + 0.02, min(o, c) - 0.02, c))
        vorher = c
    return out


LERN_CHARTS = {
    # Liquiditaet: zwei gleiche Tiefs (Stops darunter), Docht holt die Stops, dann Wende nach oben
    "liquiditaet": {"pfad": [0.62, 0.58, 0.50, 0.42, 0.47, 0.56, 0.52, 0.43, 0.48, 0.46, 0.45, 0.57, 0.67, 0.75],
                    "tiefs": [3, 7], "linie": 0.40, "docht": 10, "docht_tief": 0.24},
    # Unterstuetzung/Widerstand: Pendeln zwischen 0.30 und 0.72, dann Bruch nach unten und Test von unten
    "unterstuetzung": {"pfad": [0.50, 0.62, 0.71, 0.60, 0.45, 0.32, 0.42, 0.55, 0.70, 0.58, 0.40, 0.31, 0.43, 0.36,
                                0.22, 0.17, 0.25, 0.30, 0.21, 0.14],
                       "unten": 0.31, "oben": 0.71, "tests_unten": [5, 11], "tests_oben": [2, 8], "retest": 17},
    # Pump-and-dump: sammeln (flach), bewerben (steil hoch), verkaufen (Absturz)
    "pump": {"pfad": [0.20, 0.21, 0.19, 0.20, 0.22, 0.21, 0.27, 0.35, 0.45, 0.58, 0.72, 0.86, 0.80, 0.56, 0.36, 0.22,
                      0.15, 0.12],
             "phasen": [(0, 5), (6, 11), (12, 17)]},
}
LERN_TEXTE = {
    "en": {"stops": "Stops sit here", "zone": "Liquidity zone: many orders", "geholt": "Stops taken → reversal",
           "tief": "obvious lows", "support": "Support", "resistance": "Resistance",
           "neu": "Old support = new resistance", "phasen": ["1 Accumulate", "2 Promote", "3 Sell"],
           "schema": "Illustration"},
    "de": {"stops": "Hier liegen Stops", "zone": "Liquiditätszone: viele Orders", "geholt": "Stops geholt → Wende",
           "tief": "auffällige Tiefs", "support": "Unterstützung", "resistance": "Widerstand",
           "neu": "Alte Unterstützung = neuer Widerstand", "phasen": ["1 Sammeln", "2 Bewerben", "3 Verkaufen"],
           "schema": "Schema"},
}


def lern_chart(img: Image.Image, t: Thema, box, art: str, schritt: int, lang: str = "en"):
    """Kerzen-Schema fuer Lern-Videos. schritt 1..3 baut das Bild auf (je Punkt des Themas ein Schritt)."""
    spec, tx = LERN_CHARTS[art], LERN_TEXTE[lang]
    x0, y0, x1, y1 = box
    karte(img, t, box)
    pfad = spec["pfad"]
    sichtbar = len(pfad)
    if art == "liquiditaet" and schritt < 3:
        sichtbar = spec["docht"]          # Docht und Wende erst im 3. Schritt
    if art == "unterstuetzung" and schritt < 3:
        sichtbar = 13
    if art == "pump":
        sichtbar = spec["phasen"][min(schritt, 3) - 1][1] + 1
    kerzen = _kerzen(pfad)[:sichtbar]
    if art == "liquiditaet" and schritt >= 3:
        o, h, l, c = kerzen[spec["docht"]]
        kerzen[spec["docht"]] = (o, h, spec["docht_tief"], c)
    n = len(pfad)
    innen = (x0 + 50, y0 + (110 if art == "unterstuetzung" else 70), x1 - 50, y1 - 80)
    bw = (innen[2] - innen[0]) / n

    def X(i):
        return innen[0] + bw * (i + 0.5)

    def Y(v):
        return innen[3] - (innen[3] - innen[1]) * (v - 0.05) / 0.9

    ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
    e = ImageDraw.Draw(ebene)
    sk = max(1.0, (x1 - x0) / 820)          # im Video groessere Schrift (Handy)
    fl, fk = font("Bold", int(30 * sk)), font("SemiBold", int(26 * sk))
    if art == "liquiditaet":
        ly = Y(spec["linie"])
        if schritt >= 2:
            e.rectangle([innen[0], ly, innen[2], Y(spec["linie"] - 0.13)], fill=rgb(t.akzent2, 70))
        for xx in range(int(innen[0]), int(innen[2]), 26):     # gestrichelte Linie unter den Tiefs
            e.line([(xx, ly), (xx + 14, ly)], fill=rgb(t.text, 200), width=3)
    if art == "unterstuetzung":
        for wert, farbe, ab in ((spec["unten"], t.plus if schritt < 3 else t.minus, 1), (spec["oben"], t.minus, 2)):
            if schritt >= ab:
                e.rectangle([innen[0], Y(wert + 0.035), innen[2], Y(wert - 0.035)], fill=rgb(farbe, 60))
    img.alpha_composite(ebene)
    d = ImageDraw.Draw(img)
    for i, (o, h, l, c) in enumerate(kerzen):     # Kerzen
        farbe = t.plus if c >= o else t.minus
        d.line([(X(i), Y(h)), (X(i), Y(l))], fill=farbe, width=4)
        top, unten = Y(max(o, c)), Y(min(o, c))
        d.rectangle([X(i) - bw * 0.3, top, X(i) + bw * 0.3, max(unten, top + 4)], fill=farbe)
    if art == "liquiditaet":
        ly = Y(spec["linie"])
        d.text((innen[0], ly - 40), tx["tief"], font=fk, fill=t.text)
        for i in spec["tiefs"]:                   # Stops als kleine x unter den Tiefs
            for k in (-1, 0, 1):
                sx, sy = X(i) + k * 22, ly + 22
                d.line([(sx - 7, sy - 7), (sx + 7, sy + 7)], fill=t.minus, width=4)
                d.line([(sx - 7, sy + 7), (sx + 7, sy - 7)], fill=t.minus, width=4)
        if schritt >= 2:   # Beschriftung IN der Zone (kollidiert nicht mit „Stops geholt“)
            zy = (Y(spec["linie"]) + Y(spec["linie"] - 0.13)) / 2 - fl.size / 2 + 6
            d.text((innen[0] + 12, zy), tx["zone"], font=fl, fill=t.text)
        else:
            d.text((innen[0], Y(spec["linie"] - 0.13) + 8), tx["stops"], font=fl, fill=t.minus)
        if schritt >= 3:
            sx, sy = X(spec["docht"]), Y(spec["docht_tief"])
            d.ellipse([sx - 14, sy - 14, sx + 14, sy + 14], outline=t.akzent, width=5)
            w_ = d.textlength(tx["geholt"], font=fl)
            d.text((innen[2] - w_, sy + 22), tx["geholt"], font=fl, fill=t.akzent)
    if art == "unterstuetzung":
        for i in spec["tests_unten"]:
            d.ellipse([X(i) - 12, Y(spec["unten"]) - 12, X(i) + 12, Y(spec["unten"]) + 12], outline=t.plus, width=5)
        d.text((innen[0], Y(spec["unten"] - 0.035) + 6), tx["support"], font=fl, fill=t.plus if schritt < 3 else t.minus)
        if schritt >= 2:
            for i in spec["tests_oben"]:
                d.ellipse([X(i) - 12, Y(spec["oben"]) - 12, X(i) + 12, Y(spec["oben"]) + 12], outline=t.minus, width=5)
            d.text((innen[0], Y(spec["oben"] + 0.035) - 40), tx["resistance"], font=fl, fill=t.minus)
        if schritt >= 3:
            i = spec["retest"]
            d.ellipse([X(i) - 14, Y(spec["unten"]) - 14, X(i) + 14, Y(spec["unten"]) + 14], outline=t.akzent, width=5)
            w_ = d.textlength(tx["neu"], font=fk)
            ty = y0 + 56        # oben rechts, freie Flaeche; Linie zum Test von unten
            d.text((innen[2] - w_, ty), tx["neu"], font=fk, fill=t.akzent)
            d.line([(X(i), ty + fk.size + 10), (X(i), Y(spec["unten"]) - 18)], fill=t.akzent, width=3)
    if art == "pump":
        farben = [t.akzent2, t.akzent, t.minus]
        for k, (a, b) in enumerate(spec["phasen"][:min(schritt, 3)]):
            mx = (X(a) + X(b)) / 2
            name = tx["phasen"][k]
            d.text((mx - d.textlength(name, font=fk) / 2, y1 - 62), name, font=fk, fill=farben[k])
            d.line([(X(a) - bw * 0.4, y1 - 72), (X(b) + bw * 0.4, y1 - 72)], fill=farben[k], width=4)
    sch = tx["schema"]
    d.text((x1 - 30 - d.textlength(sch, font=font("Medium", 24)), y0 + 20), sch, font=font("Medium", 24), fill=t.neben)


ECHT_TEXTE = {
    "en": {"tief": "obvious low", "stops": "Stops sit below", "zone": "Liquidity zone", "geholt": "Stops taken → reversal",
           "support": "Support", "resistance": "Resistance", "gebrochen": "Support broken", "haelt": "Support held so far",
           "echt": "Real chart"},
    "de": {"tief": "auffälliges Tief", "stops": "Darunter liegen Stops", "zone": "Liquiditätszone",
           "geholt": "Stops geholt → Wende", "support": "Unterstützung", "resistance": "Widerstand",
           "gebrochen": "Unterstützung gebrochen", "haelt": "Unterstützung hielt bisher", "echt": "Echter Chart"},
}


def _preis(x: float) -> str:
    return f"${x:,.0f}" if x >= 100 else f"${x:,.4g}"


def echt_chart(img: Image.Image, t: Thema, box, kerzen: list[dict], art: str, info: dict, schritt: int,
               lang: str = "en", titel: str = ""):
    """Echter Kerzen-Chart (z. B. BTC 4h) mit markiertem Muster aus social/muster.py, Schritt fuer Schritt."""
    import datetime as _dt
    tx = ECHT_TEXTE[lang]
    x0, y0, x1, y1 = box
    karte(img, t, box)
    sk = max(1.0, (x1 - x0) / 820)
    fl, fk, fs = font("Bold", int(30 * sk)), font("SemiBold", int(25 * sk)), font("Medium", int(21 * sk))
    sichtbar = len(kerzen)
    if art == "liquiditaet" and schritt < 3:
        sichtbar = info["docht_index"]            # Docht und Wende erst im 3. Schritt
    if art == "unterstuetzung" and schritt < 3 and info.get("bruch_index"):
        sichtbar = info["bruch_index"]
    k = kerzen[:sichtbar]
    tief_, hoch_ = min(x["l"] for x in kerzen), max(x["h"] for x in kerzen)
    lo = tief_ - (hoch_ - tief_) * 0.30     # Platz unten fuer Zone und Beschriftung
    hi = hoch_ + (hoch_ - tief_) * 0.08
    innen = (x0 + 30, y0 + 70, x1 - 150, y1 - 60)
    n = len(kerzen)
    bw = (innen[2] - innen[0]) / n

    def X(i):
        return innen[0] + bw * (i + 0.5)

    def Y(v):
        return innen[3] - (innen[3] - innen[1]) * (v - lo) / (hi - lo)

    ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
    e = ImageDraw.Draw(ebene)
    if art == "liquiditaet" and schritt >= 2:
        e.rectangle([innen[0], Y(info["tief"]), innen[2], Y(info["docht"] * 0.997)], fill=rgb(t.akzent2, 75))
    if art == "unterstuetzung":
        for z, farbe, ab in ((info["support"], t.plus, 1), (info["resistance"], t.minus, 2)):
            if schritt >= ab:
                e.rectangle([innen[0], Y(z["oben"] * 1.002), innen[2], Y(z["unten"] * 0.998)], fill=rgb(farbe, 60))
    img.alpha_composite(ebene)
    d = ImageDraw.Draw(img)
    for v in (lo + (hi - lo) * f for f in (0.1, 0.5, 0.9)):     # Preisachse rechts
        d.text((innen[2] + 16, Y(v) - fs.size / 2), _preis(v), font=fs, fill=t.neben)
    dicke = max(2, int(bw * 0.15))
    for i, x in enumerate(k):
        farbe = t.plus if x["c"] >= x["o"] else t.minus
        d.line([(X(i), Y(x["h"])), (X(i), Y(x["l"]))], fill=farbe, width=dicke)
        top, unten = Y(max(x["o"], x["c"])), Y(min(x["o"], x["c"]))
        d.rectangle([X(i) - bw * 0.32, top, X(i) + bw * 0.32, max(unten, top + 2)], fill=farbe)
    if art == "liquiditaet":
        ly, i = Y(info["tief"]), info["tief_index"]
        for xx in range(int(X(i)), int(innen[2]), 22):
            d.line([(xx, ly), (xx + 12, ly)], fill=t.text, width=3)
        lab = f"{tx['tief']} {_preis(info['tief'])}"
        d.text((innen[2] - d.textlength(lab, font=fk), ly - fk.size - 12), lab, font=fk, fill=t.text)
        if schritt == 1:
            d.text((X(i), ly + 10), tx["stops"], font=fl, fill=t.minus)
        if schritt >= 2:   # Zonen-Text auf der Seite, wo der Docht NICHT ist
            wz = d.textlength(tx["zone"], font=fk)
            links = X(info["docht_index"]) > (innen[0] + innen[2]) / 2
            d.text((innen[0] + 10 if links else innen[2] - wz - 10, ly + 8), tx["zone"], font=fk, fill=t.text)
        if schritt >= 3:
            j = info["docht_index"]
            sx, sy = X(j), Y(info["docht"])
            d.ellipse([sx - 14, sy - 14, sx + 14, sy + 14], outline=t.akzent, width=5)
            w_ = d.textlength(tx["geholt"], font=fl)
            d.text((max(innen[0], min(sx - w_ / 2, innen[2] - w_)), sy + 22), tx["geholt"], font=fl, fill=t.akzent)
    if art == "unterstuetzung":
        s, r = info["support"], info["resistance"]
        for j in s["beruehrungen"]:
            if j < sichtbar:
                d.ellipse([X(j) - 12, Y(kerzen[j]["l"]) - 12, X(j) + 12, Y(kerzen[j]["l"]) + 12], outline=t.plus, width=4)
        d.text((innen[0] + 8, Y(s["unten"] * 0.998) + 6), tx["support"], font=fl, fill=t.plus)
        if schritt >= 2:
            for j in r["beruehrungen"]:
                if j < sichtbar:
                    d.ellipse([X(j) - 12, Y(kerzen[j]["h"]) - 12, X(j) + 12, Y(kerzen[j]["h"]) + 12], outline=t.minus,
                              width=4)
            d.text((innen[0] + 8, Y(r["oben"] * 1.002) - fl.size - 8), tx["resistance"], font=fl, fill=t.minus)
        if schritt >= 3:
            b = info.get("bruch_index")
            txt = tx["gebrochen"] if b is not None else tx["haelt"]
            if b is not None:
                d.ellipse([X(b) - 14, Y(kerzen[b]["c"]) - 14, X(b) + 14, Y(kerzen[b]["c"]) + 14], outline=t.akzent, width=5)
            w_ = d.textlength(txt, font=fl)
            d.text((innen[2] - w_, y1 - fl.size - 20), txt, font=fl, fill=t.akzent)
    d.text((x0 + 30, y0 + 20), titel, font=fk, fill=t.text)
    utc = _dt.timezone.utc
    a, b = (_dt.datetime.fromtimestamp(kerzen[0]["t"] / 1000, utc), _dt.datetime.fromtimestamp(kerzen[-1]["t"] / 1000, utc))
    zeit = f"{a:%b %-d} – {b:%b %-d}" if lang == "en" else f"{a.day}.{a.month}. – {b.day}.{b.month}."
    d.text((x1 - 24 - d.textlength(zeit, font=fs), y0 + 24), zeit, font=fs, fill=t.neben)
