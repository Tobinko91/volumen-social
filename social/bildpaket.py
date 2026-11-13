"""Hingucker-Bild fuer X (Wunsch Tobias 06.11.2026): Bild 1 = Foto/Zitat/Vergleich, Bild 2 = unsere Datenkarte.

hingucker.json im Beitragsordner (legt der Redaktions-Chat an, der Server zeichnet, weil nur er die Fotos hat):
  {"art": "foto",      "person": "trump", "etikett": "BREAKING", "kopf": "Trump signs ...", "unter": "Nov 6, 2:00 PM ET"}
  {"art": "zitat",     "person": "warsh", "zitat": "Conditions are quite positive.", "wer": "Fed Chair Kevin Warsh",
                       "wann": "Nov 5, 2026"}
  {"art": "vergleich", "etikett": "US JOBS · OCTOBER", "kopf": "Jobs beat",
                       "reihen": [["Expected", 60000, "60K"], ["Actual", 165000, "165K"], ["September", 60000, "60K"]],
                       "hervor": 1, "unter": "Nov 6, 8:30 AM ET"}
Format 16:9 (1200x675): X zeigt es in der Timeline ohne Beschnitt. Fehlt das Foto, gibt es kein Hingucker-Bild
(der Beitrag laeuft normal mit einem Bild weiter).
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

W, H = 1200, 675


def _grund(th, saat=3):
    from . import design
    return design.hintergrund(th, W, H, saat=saat)


def _kopfleiste(img, th, etikett: str | None, farbe=None):
    """WhaleSqueeze oben links auf dunklem Balken, Etikett rechts daneben."""
    from . import design
    ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ebene).rectangle([0, 0, W, 92], fill=design.rgb(design.MITTERNACHT, 205))
    img.alpha_composite(ebene)
    design.marke(img, th, 36, 18, 56)
    if etikett:
        d = ImageDraw.Draw(img)
        f = design.font("Bold", 26)
        b = d.textlength(etikett, font=f) + 40
        x = W - 36 - b
        d.rounded_rectangle([x, 22, x + b, 70], radius=24, fill=design.rgb(farbe or th.minus))
        d.text((x + 20, 30), etikett, font=f, fill=design.MITTERNACHT)


def _foto(pfad: str, w: int, h: int) -> Image.Image:
    """Foto auf Groesse zuschneiden, Gesicht meist oben -> Ausschnitt etwas oberhalb der Mitte. Keine Veraenderung
    des Bildinhalts (nur Zuschnitt und Groesse)."""
    f = Image.open(pfad).convert("RGBA")
    return ImageOps.fit(f, (w, h), Image.LANCZOS, centering=(0.5, 0.3))


def _ausblenden(f: Image.Image, breite: int, links: bool) -> Image.Image:
    """Foto weich in den Hintergrund auslaufen lassen (Transparenz-Verlauf, keine harte Kante)."""
    maske = Image.new("L", f.size, 255)
    d = ImageDraw.Draw(maske)
    for i in range(breite):
        x = i if links else f.width - 1 - i
        d.line([(x, 0), (x, f.height)], fill=int(255 * (i / breite) ** 1.4))
    f = f.copy()
    f.putalpha(maske)
    return f


def _verlauf(img, x0: int, x1: int, farbe, links_dunkel=True):
    from . import design
    ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ebene)
    for x in range(x0, x1):
        a = (x1 - x) / (x1 - x0) if links_dunkel else (x - x0) / (x1 - x0)
        d.line([(x, 0), (x, H)], fill=design.rgb(farbe, int(255 * min(1, a * 1.15))))
    img.alpha_composite(ebene)


def _credit(img, text: str):
    from . import design
    if not text:
        return
    d = ImageDraw.Draw(img)
    f = design.font("Medium", 16)
    b = d.textlength(text, font=f)
    d.rectangle([W - b - 24, H - 30, W, H], fill=design.rgb(design.MITTERNACHT, 180))
    d.text((W - b - 12, H - 26), text, font=f, fill=design.NEBEN)


def _text_passend(d, x: int, y: int, text: str, breite: int, hoehe: int, farbe, gross: int, klein: int) -> int:
    """Groesste Schrift (gross..klein), bei der der ganze Text in die Box passt; nie abgeschnitten."""
    from . import design
    g = gross
    while True:
        f = design.font("Bold", g)
        zeilen = design.umbruch(d, text, f, breite)
        if len(zeilen) * g * 1.18 <= hoehe or g <= klein:
            break
        g -= 2
    for z in zeilen:
        d.text((x, y), z, font=f, fill=farbe)
        y += int(g * 1.18)
    return y


def foto_titel(foto: dict, kopf: str, unter: str = "", etikett: str | None = "BREAKING", th=None,
               groesse: tuple[int, int] = (1080, 1350)) -> Image.Image:
    """Hochformat 1080x1350 (Instagram/Telegram/X-Karussell, Wunsch Tobias 12.11.2026): Foto oben gross,
    weich auslaufend, Schlagzeile darunter. Foto nur zugeschnitten, nicht veraendert; Credit klein im Bild."""
    from . import design
    th = th or design.THEMEN["nacht"]
    w, h = groesse
    fh = 880 if h <= 1350 else 1180   # 9:16 (Reel): Foto groesser, Untertitel-Platz unten bleibt frei
    img = design.hintergrund(th, w, h, saat=5)
    f = _foto(foto["pfad"], w, fh)
    maske = Image.new("L", f.size, 255)
    dm = ImageDraw.Draw(maske)
    for i in range(320):   # unten weich in den Hintergrund
        dm.line([(0, fh - 1 - i), (w, fh - 1 - i)], fill=int(255 * (i / 320) ** 1.4))
    f.putalpha(maske)
    img.alpha_composite(f, (0, 0))
    ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ebene).rectangle([0, 0, w, 96], fill=design.rgb(design.MITTERNACHT, 205))
    img.alpha_composite(ebene)
    design.marke(img, th, 40, 20, 56)
    d = ImageDraw.Draw(img)
    if etikett:
        fe = design.font("Bold", 28)
        b = d.textlength(etikett, font=fe) + 44
        d.rounded_rectangle([w - 40 - b, 24, w - 40, 74], radius=25, fill=design.rgb(th.minus))
        d.text((w - 40 - b + 22, 32), etikett, font=fe, fill=design.MITTERNACHT)
    if foto.get("credit"):
        fc = design.font("Medium", 18)
        t = f"Photo: {foto['credit']}"[:90]
        d.text((w - 30 - d.textlength(t, font=fc), 108), t, font=fc, fill=design.NEBEN)
    y = _text_passend(d, 60, fh - 40, kopf, w - 120, 260, th.text, 84, 50)
    if unter:
        d.text((60, y + 18), unter, font=design.font("SemiBold", 40), fill=th.akzent)
    design.fuss(img, th, "Not financial advice.")
    return img


def foto_karte(foto: dict, kopf: str, unter: str = "", etikett: str | None = "BREAKING", th=None) -> Image.Image:
    """Foto rechts gross, Schlagzeile links, Verlauf dazwischen."""
    from . import design
    th = th or design.THEMEN["nacht"]
    img = _grund(th)
    fw = 700
    img.alpha_composite(_ausblenden(_foto(foto["pfad"], fw, H), 320, links=True), (W - fw, 0))
    _kopfleiste(img, th, etikett)
    d = ImageDraw.Draw(img)
    y = _text_passend(d, 48, 150, kopf, 600, 330, th.text, 64, 40) + 24
    if unter:
        d.text((48, y), unter, font=design.font("SemiBold", 28), fill=th.akzent)
    _credit(img, foto.get("credit", ""))
    return img


def zitat_karte(foto: dict, zitat: str, wer: str, wann: str = "", th=None) -> Image.Image:
    """Foto links, woertliches Zitat gross rechts (keine Kuerzung, kein Umschreiben: der Chat liefert das Zitat)."""
    from . import design
    th = th or design.THEMEN["nacht"]
    img = _grund(th, 5)
    fw = 470
    img.alpha_composite(_ausblenden(_foto(foto["pfad"], fw, H), 220, links=False), (0, 0))
    _kopfleiste(img, th, None)
    d = ImageDraw.Draw(img)
    x, breite = fw + 20, W - fw - 70
    d.text((x - 6, 92), "“", font=design.font("Bold", 150), fill=th.akzent)
    y = _text_passend(d, x, 230, zitat, breite, 300, th.text, 54, 30) + 26
    d.text((x, y), wer, font=design.font("Bold", 30), fill=th.akzent2)
    if wann:
        d.text((x, y + 42), wann, font=design.font("Medium", 26), fill=th.neben)
    _credit(img, foto.get("credit", ""))
    return img


def vergleich_karte(kopf: str, reihen: list, hervor: int = 1, etikett: str = "", unter: str = "", th=None) -> Image.Image:
    """Grosse Balken „Expected vs Actual“: reihen = [[Name, Wert, Anzeige], ...]; hervor = Index der echten Zahl."""
    from . import design
    th = th or design.THEMEN["nacht"]
    img = _grund(th, 2)
    _kopfleiste(img, th, etikett or None, th.akzent2)
    d = ImageDraw.Draw(img)
    d.text((48, 118), kopf, font=design.font("Bold", 64), fill=th.text)
    maxw = max(abs(r[1]) for r in reihen) or 1
    y, hoehe, x0, breite = 230, 92, 300, W - 300 - 60
    for i, (name, wert, anzeige) in enumerate(reihen):
        farbe = (th.plus if wert >= 0 else th.minus) if i == hervor else th.linie
        d.text((48, y + 22), name, font=design.font("Bold" if i == hervor else "SemiBold", 36),
               fill=th.text if i == hervor else th.neben)
        w = max(hoehe, int(breite * abs(wert) / maxw))
        d.rounded_rectangle([x0, y, x0 + w, y + hoehe], radius=18, fill=design.rgb(farbe))
        f = design.font("Bold", 52 if i == hervor else 40)
        tw = d.textlength(anzeige, font=f)
        innen = w > tw + 50
        d.text((x0 + w - tw - 24 if innen else x0 + w + 20, y + (14 if i == hervor else 22)), anzeige, font=f,
               fill=design.MITTERNACHT if innen and i == hervor else th.text)
        y += hoehe + 26
    if unter:
        d.text((48, H - 56), unter, font=design.font("Medium", 26), fill=th.neben)
    return img


def aus_spec(ordner: Path, fotos_dir: Path) -> Path | None:
    """hingucker.json -> hingucker.png. None, wenn das Foto fehlt (dann kein Hingucker, kein Fehler)."""
    from . import fotos
    spec = json.loads((ordner / "hingucker.json").read_text(encoding="utf-8"))
    art = spec.get("art")
    if art == "vergleich":
        img = vergleich_karte(spec["kopf"], spec["reihen"], int(spec.get("hervor", 1)), spec.get("etikett", ""),
                              spec.get("unter", ""))
    else:
        foto = fotos.waehlen(fotos_dir, spec.get("person", ""), ordner.name)
        if not foto:
            return None
        if art == "zitat":
            img = zitat_karte(foto, spec["zitat"], spec["wer"], spec.get("wann", ""))
        else:
            img = foto_karte(foto, spec["kopf"], spec.get("unter", ""), spec.get("etikett", "BREAKING"))
    ziel = ordner / "hingucker.png"
    img.convert("RGB").save(ziel)
    return ziel


# ---------------------------------------------------------------- A/B-Test „mit / ohne Hingucker“ (Wunsch 06.11.2026)

def test_zuteilen(ordner: Path, stand_p: Path, test: str = "hingucker") -> str:
    """Abwechselnd 'mit'/'ohne' je Beitrag mit Hingucker (gleich viele in beiden Gruppen). Schreibt bildtest.json."""
    p = ordner / "bildtest.json"
    if p.exists():
        return json.loads(p.read_text())["art"]
    try:
        s = json.loads(stand_p.read_text())
    except Exception:
        s = {"n": 0}
    art = "mit" if s["n"] % 2 == 0 else "ohne"
    s["n"] += 1
    stand_p.parent.mkdir(parents=True, exist_ok=True)
    stand_p.write_text(json.dumps(s))
    p.write_text(json.dumps({"art": art, "test": test}))
    return art


def x_bilder(bild: Path) -> list[Path]:
    """Welche Bilder auf X: [hingucker.png, post.png] in der Test-Gruppe 'mit', sonst nur das Beitragsbild."""
    h, t = bild.parent / "hingucker.png", bild.parent / "bildtest.json"
    if bild.name == "post.png" and h.exists():
        try:
            if json.loads(t.read_text())["art"] == "mit":
                return [h, bild]
        except Exception:
            return [h, bild]
    return [bild]
