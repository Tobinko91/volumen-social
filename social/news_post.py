"""News-Beitrag gestalten: Bild 4:5 in wechselnden Layouts + Texte fuer Telegram und X.
Quellen erscheinen nicht im Beitrag (Wunsch Tobias 23.10.2026), nur im Freigabe-Hinweis an Tobias."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import re
from pathlib import Path

from . import design
from .sprache import hinweis, stempel as datum_stempel

X_MAX = 280
LAYOUTS = ("klassisch", "gross", "kennzahl", "chart")
KENNZAHL = re.compile(r"[-+−]?\d[\d.]*(?:,\d+)?\s?(?:%|Mrd\.?\s?(?:\$|€|US-Dollar|Dollar|Euro)?|Mio\.?\s?(?:\$|€|US-Dollar|Dollar|Euro)?"
                      r"|Milliarden\s?(?:\$|€|US-Dollar|Dollar|Euro)?|Millionen\s?(?:\$|€|US-Dollar|Dollar|Euro)?|\$|€|BTC|ETH)")
KENNZAHL_EN = re.compile(r"\$\d[\d,]*(?:\.\d+)?(?:\s?(?:trillion|billion|million|bn|[BMK]\b))?"
                         r"|[-+−]?\d[\d,]*(?:\.\d+)?\s?(?:%|trillion|billion|million|bps|basis points|BTC|ETH)")


KRYPTO_TITEL = {"en": "What it means for crypto", "de": "Was das für Krypto heißt"}


def ist_makro(d: dict, gruppe: dict) -> bool:
    """S19: Makro-Meldung (Fed, Inflation, Zinsen ...), unter die unsere eigenen Krypto-Daten kommen."""
    return str(d.get("rubrik", "")).lower() in ("macro", "makro") or bool(gruppe.get("makro") and not d.get("coins"))


def krypto_zeile(m: dict | None, lang: str = "en") -> dict | None:
    """Eigene Bot-Daten zur Makro-Meldung (nur Zahlen aus markt.json, keine Deutung, keine Empfehlung).
    m = daten.marktlage(). Rueckgabe: {"lang": Satz fuer Telegram/Bild, "kurz": fuer X, "fakten": [Zahlen]}."""
    from .sprache import zahl
    if not m or m.get("anteil_plus") is None or m.get("median_24h") is None:
        return None
    a, med, n = int(round(m["anteil_plus"])), m["median_24h"], m.get("anzahl")
    btc = m.get("btc_24h")
    if lang == "en":
        satz = (f"In the small caps we track{f' ({n} coins)' if n else ''}, {a}% are up over 24h, "
                f"median {zahl(med, lang, True)}%.")
        if btc is not None:
            satz += f" Bitcoin: {zahl(btc, lang, True)}% in 24h."
        kurz = f"Crypto now: {a}% of small caps up in 24h."
    else:
        satz = (f"Bei den Small Caps, die wir verfolgen{f' ({n} Coins)' if n else ''}, liegen {a} % im Plus (24 h), "
                f"Median {zahl(med, lang, True)} %.")
        if btc is not None:
            satz += f" Bitcoin: {zahl(btc, lang, True)} % in 24 h."
        kurz = f"Krypto jetzt: {a} % der Small Caps im Plus (24 h)."
    return {"lang": satz, "kurz": kurz, "fakten": [a, med, n, btc, 24]}


def quellen_hinweis(gruppe: dict) -> str:
    """Nur fuer Tobias im Freigabe-Chat, wird nicht gepostet."""
    return "Quellen (nur für dich, nicht im Post): " + ", ".join(gruppe["quellen"][:4])


def texte(d: dict, gruppe: dict, cfg: dict, eil: bool = False) -> dict:
    """d["krypto"] (optional, S19): Ergebnis von krypto_zeile() bei Makro-Meldungen."""
    lang = cfg.get("sprache", "de")
    hw = hinweis(cfg, lang)
    kopf = (("🚨 BREAKING: " if lang == "en" else "🚨 EILMELDUNG: ") if eil else "")
    x = f"{kopf}{d['x']}\n{hw}"
    if len(x) > X_MAX:
        x = f"{kopf}{d['x'][:X_MAX - len(kopf) - len(hw) - 3].rstrip()}…\n{hw}"
    k = d.get("krypto")
    if k and len(x) + len(k["kurz"]) + 1 <= X_MAX:   # X: kurze Zeile nur, wenn sie passt
        x = x[: x.rfind("\n")] + "\n" + k["kurz"] + x[x.rfind("\n"):]
    e = html.escape
    tg = [f"{'🚨 ' if eil else '📰 '}<b>{e(d['schlagzeile'])}</b>", "", e(d["kernsatz"]), ""]
    tg += [f"• {e(p)}" for p in d["punkte"]]
    if k:
        tg += ["", f"📊 <b>{KRYPTO_TITEL[lang]}:</b> {e(k['lang'])}"]
    tg += ["", f"<i>{e(cfg['hinweise']['post_text'])}</i>"]
    return {"x": x, "telegram": "\n".join(tg)}


def kennzahl(d: dict) -> str | None:
    """Erste Zahl mit Einheit aus Kernsatz/Punkten (Text ist vorher gegen die Quellen geprueft)."""
    for text in [d["kernsatz"], *d["punkte"]]:
        m = (KENNZAHL_EN if design.SPRACHE == "en" else KENNZAHL).search(text)
        if m and any(c.isdigit() for c in m.group()):
            return m.group().strip()
    return None


def layout_waehlen(d: dict, kurs: list | None) -> str:
    moeglich = ["klassisch", "gross"]
    if kennzahl(d):
        moeglich.append("kennzahl")
    if kurs and len(kurs) >= 10:
        moeglich += ["chart", "chart"]   # Grafik bevorzugt, wenn ein Kursverlauf da ist
    h = int(hashlib.sha256(d["schlagzeile"].encode()).hexdigest(), 16)
    return moeglich[h % len(moeglich)]


def bild(d: dict, gruppe: dict, cfg: dict, ziel: Path, eil: bool = False, jetzt: float | None = None,
         kurs: list | None = None, layout: str | None = None) -> Path:
    """kurs: [(zeit_ms, schluss)] des ersten genannten Coins (7 Tage), optional."""
    from PIL import ImageDraw
    from .design import absatz, de, etikett, fuss, hintergrund, karte, marke, punkte, thema_waehlen, ueberschrift, \
        MINUS, font
    from . import grafik
    t = dt.datetime.fromtimestamp(jetzt or dt.datetime.now().timestamp())
    en = design.SPRACHE == "en"
    stempel = datum_stempel(t, design.SPRACHE)
    th = thema_waehlen("eil" if eil else "news", f"{t.isoformat()}:{d['schlagzeile']}")
    layout = layout or layout_waehlen(d, kurs)
    if layout == "chart" and not (kurs and len(kurs) >= 10):
        layout = "klassisch"
    if layout == "kennzahl" and not kennzahl(d):
        layout = "klassisch"
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=len(d["schlagzeile"]))
    marke(img, th, 80, 64, 64, untertitel=stempel)
    dr = ImageDraw.Draw(img)
    etikett(dr, th, 80, 170, (("BREAKING · " if en else "EILMELDUNG · ") if eil else "NEWS · ") + d["rubrik"].upper(),
            farbe=MINUS if eil else None)
    unten = H - 130
    k = d.get("krypto")
    if k:   # S19: Platz fuer die Krypto-Karte unten
        unten -= 175

    if layout == "gross":   # grosse Schlagzeile, Punkte auf einer Karte
        y = ueberschrift(dr, th, 80, 270, d["schlagzeile"], W - 160, groesse=104, max_zeilen=4) + 40
        y = absatz(dr, th, 80, y, d["kernsatz"], W - 160, groesse=38, farbe=th.neben, gewicht="Medium") + 40
        if y < unten - 200:
            karte(img, th, (60, y, W - 60, unten))
            dr = ImageDraw.Draw(img)
            punkte(dr, th, 100, y + 40, d["punkte"], W - 200, groesse=32, bis_y=unten - 30)
    elif layout == "kennzahl":   # eine Zahl gross in Leuchtminze
        y = ueberschrift(dr, th, 80, 256, d["schlagzeile"], W - 160, groesse=70, max_zeilen=3) + 40
        z = kennzahl(d)
        karte(img, th, (60, y, W - 60, y + 300))
        dr = ImageDraw.Draw(img)
        gr = 150
        while dr.textlength(z, font=font("Bold", gr)) > W - 220 and gr > 70:
            gr -= 8
        dr.text((100, y + 34), "NUMBER OF THE DAY" if en else "DIE ZAHL DES TAGES", font=font("Bold", 26), fill=th.neben)
        dr.text((100, y + 165 - gr * 0.55), z, font=font("Bold", gr), fill=th.akzent)
        y += 340
        y = absatz(dr, th, 80, y, d["kernsatz"], W - 160, groesse=38, gewicht="Medium") + 30
        punkte(dr, th, 80, y, d["punkte"], W - 160, groesse=31, bis_y=unten)
    elif layout == "chart":   # Schlagzeile + 7-Tage-Kurs des Coins
        coin = str((d.get("coins") or ["?"])[0]).upper()
        y = ueberschrift(dr, th, 80, 256, d["schlagzeile"], W - 160, groesse=70, max_zeilen=3) + 24
        y = absatz(dr, th, 80, y, d["kernsatz"], W - 160, groesse=36, gewicht="Medium") + 30
        werte = [k[1] for k in kurs]
        chg = (werte[-1] / werte[0] - 1) * 100 if werte[0] else 0
        farbe = th.akzent if chg >= 0 else th.minus
        tage = ["" for _ in werte]
        tage[0], tage[-1] = ("7 days ago", "now") if en else ("vor 7 Tagen", "jetzt")
        grafik.linien(img, th, (60, y, W - 60, unten - 10),
                      [{"name": coin, "werte": werte, "farbe": farbe,
                        "endtext": ("+" if chg >= 0 else "−") + de(abs(chg)) + ("%" if en else " %")}],
                      tage, titel=f"{coin} price, 7 days" if en else f"{coin}-Kurs, 7 Tage")
    else:   # klassisch
        y = ueberschrift(dr, th, 80, 256, d["schlagzeile"], W - 160, groesse=84, max_zeilen=3) + 30
        dr.rounded_rectangle([80, y, 240, y + 8], radius=4, fill=th.akzent)
        y += 40
        y = absatz(dr, th, 80, y, d["kernsatz"], W - 160, groesse=42, gewicht="Medium") + 34
        punkte(dr, th, 80, y, d["punkte"], W - 160, groesse=33, bis_y=unten - 20 if k else H - 150)
    if k:
        karte(img, th, (60, unten + 10, W - 60, H - 118))
        dr = ImageDraw.Draw(img)
        dr.text((96, unten + 32), KRYPTO_TITEL[design.SPRACHE if design.SPRACHE in KRYPTO_TITEL else "en"].upper(),
                font=font("Bold", 24), fill=th.akzent2)
        absatz(dr, th, 96, unten + 68, k["lang"], W - 192, groesse=30, gewicht="Medium")
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    (ziel.parent / "layout.txt").write_text(layout, encoding="utf-8")
    return ziel
