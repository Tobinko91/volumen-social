"""Text-und-Bild-Beitraege fuer Telegram und X (Hauptformat dort, entschieden 20.10.2026).

Bild 1080x1350 (4:5, passt in X und Telegram), dazu ein kurzer Text.
X: hoechstens 280 Zeichen. Telegram: darf laenger sein.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .bilder import Leinwand, _font
from .sprache import zahl

X_MAX = 280


def _kurz(base: str, chg: float, lang: str) -> str:
    return f"{base} {zahl(chg, lang, True)} %"


def markt_texte(beitrag: dict, cfg: dict) -> dict:
    """Texte fuer X (kurz) und Telegram (ausfuehrlicher), nur aus den Fakten."""
    f, lang = beitrag["fakten"], beitrag.get("sprache", "de")
    b = f.get("breite")
    zeilen_x = [f"Krypto-Markt am {f['datum']}"]
    if b:
        zeilen_x.append(f"Small Caps: Median {zahl(b['median_24h'], lang, True)} % in 24 Std., "
                        f"{b['anteil_plus']} % im Plus.")
    zeilen_x.append("Größte Bewegungen: " + ", ".join(_kurz(m["base"], m["chg24"], lang) for m in f["mover"]))
    zeilen_x.append("Keine Anlageberatung.")
    x = "\n".join(zeilen_x)
    if len(x) > X_MAX:  # zur Not ohne dritten Mover
        zeilen_x[-2] = "Größte Bewegungen: " + ", ".join(_kurz(m["base"], m["chg24"], lang) for m in f["mover"][:2])
        x = "\n".join(zeilen_x)

    tg = [f"📊 <b>Krypto-Markt am {f['datum']}</b>", ""]
    if b:
        tg.append(f"Von {b['anzahl']} Small Caps ist der mittlere Coin in 24 Stunden um "
                  f"{zahl(abs(b['median_24h']), lang)} % {'gestiegen' if b['median_24h'] >= 0 else 'gefallen'}. "
                  f"{b['anteil_plus']} % stehen im Plus.")
        tg.append("")
    tg.append("<b>Größte Bewegungen</b>")
    for m in f["mover"]:
        grund = m["ausloeser"] or "keine klare Nachricht"
        tg.append(f"• {m['base']}: {zahl(m['chg24'], lang, True)} % – Auslöser: {grund}")
    tg += ["", f"<i>{cfg['hinweise']['fusszeile']}. {cfg['hinweise']['konflikt']}</i>"]
    return {"x": x, "telegram": "\n".join(tg)}


def markt_bild(beitrag: dict, cfg: dict, ziel: Path) -> Path:
    c = dict(cfg)
    c["video"] = dict(cfg["video"], hoehe=1350)
    lw = Leinwand(c)
    img, d = lw.neu()
    f = beitrag["fakten"]
    # Kopf (ohne die Abstaende fuer App-Knoepfe wie im Video)
    lw.logo(d, 80, 70, 2.0)
    d.text((160, 77), "WHALESQUEEZE", font=_font("Bold", 38), fill=lw.f["text"])
    d.text((80, 140), "KRYPTO-MARKT", font=_font("Black", 72), fill=lw.f["text"])
    d.text((80, 228), f["datum"], font=_font("SemiBold", 40), fill=lw.f["amber"])
    y = 310
    b = f.get("breite")
    if b:
        m = b["median_24h"]
        d.text((80, y), "Small Caps · 24 Std. · Median", font=_font("SemiBold", 40), fill=lw.f["neben"])
        d.text((80, y + 45), f"{zahl(m, lw.lang, True)} %", font=_font("Black", 130), fill=lw.farbe_wert(m))
        x0, x1, yb = 80, lw.W - 80, y + 210
        teil = x0 + (x1 - x0) * b["anteil_plus"] / 100
        d.rounded_rectangle([x0, yb, x1, yb + 44], radius=22, fill=lw.f["minus"])
        if b["anteil_plus"] > 0:
            d.rounded_rectangle([x0, yb, max(teil, x0 + 44), yb + 44], radius=22, fill=lw.f["plus"])
        d.text((x0, yb + 60), f"{b['anteil_plus']} % im Plus", font=_font("Bold", 36), fill=lw.f["plus"])
        y = yb + 130
    d.text((80, y), "GRÖSSTE BEWEGUNGEN", font=_font("Bold", 40), fill=lw.f["neben"])
    y += 70
    for mv in f["mover"]:
        d.rounded_rectangle([80, y, lw.W - 80, y + 128], radius=24, fill=lw.f["flaeche"])
        d.text((115, y + 22), mv["base"], font=_font("Black", 60), fill=lw.f["text"])
        wert = f"{zahl(mv['chg24'], lw.lang, True)} %"
        fw = _font("Black", 60)
        d.text((lw.W - 115 - d.textlength(wert, font=fw), y + 22), wert, font=fw, fill=lw.farbe_wert(mv["chg24"]))
        grund = ("Auslöser: " + mv["ausloeser"]) if mv.get("ausloeser") else "keine klare Nachricht"
        d.text((115, y + 90), grund, font=_font("Medium", 28), fill=lw.f["amber"] if mv.get("ausloeser") else lw.f["neben"])
        y += 142
    d.line([(80, 1225), (lw.W - 80, 1225)], fill=lw.f["linie"], width=2)
    d.text((80, 1243), cfg["hinweise"]["fusszeile"], font=_font("Medium", 28), fill=lw.f["neben"])
    d.text((80, 1285), "whalesqueeze.com", font=_font("Bold", 30), fill=lw.f["amber"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.save(ziel)
    return ziel
