"""Grafiken fuer Beitraege: Balken, Linien, Schemas. Alles selbst gezeichnet im Nachtleuchten-Design."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .design import Thema, de, font, karte, rgb


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
        for fy, name, farbe in [(0.2, "Widerstand", t.minus), (0.78, "Unterstützung", t.plus)]:
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
        d.text((a[0] + 10, b[1] + 6), "viele Stops = Liquidität", font=fl, fill=t.akzent2)
        kurs = [0.3, 0.45, 0.6, 0.48, 0.35, 0.5, 0.61, 0.47, 0.4, 0.55, 0.78, 0.5, 0.3, 0.18]
        pts = [P(i / (len(kurs) - 1), v) for i, v in enumerate(kurs)]
        d.line(pts, fill=t.text, width=5, joint="curve")
        sx, sy = pts[10]
        d.ellipse([sx - 11, sy - 11, sx + 11, sy + 11], fill=t.akzent)
        txt = "Stops geholt, dann Wende"
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
    d.text((x1 - 40 - d.textlength("Schema", font=font("Medium", 22)), y0 + 22), "Schema",
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
    s = f"{plus} %"
    d.text((cx - d.textlength(s, font=f) / 2, cy - r * 0.36), s, font=f, fill=t.text)
    fs = font("Medium", int(r * 0.17))
    d.text((cx - d.textlength("im Plus", font=fs) / 2, cy + r * 0.2), "im Plus", font=fs, fill=t.neben)
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
