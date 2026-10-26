"""Text-und-Bild-Beitraege fuer Telegram und X (Hauptformat dort, entschieden 20.10.2026).

Bild 1080x1350 (4:5, passt in X und Telegram), dazu ein kurzer Text.
X: hoechstens 280 Zeichen. Telegram: darf laenger sein.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .sprache import T, hinweis, zahl

X_MAX = 280


def _kurz(base: str, chg: float, lang: str) -> str:
    return f"{base} {zahl(chg, lang, True)}" + (" %" if lang == "de" else "%")


def markt_texte(beitrag: dict, cfg: dict) -> dict:
    """Texte fuer X (kurz) und Telegram (ausfuehrlicher), nur aus den Fakten."""
    f, lang = beitrag["fakten"], beitrag.get("sprache", "de")
    t, pz = T[lang], (" %" if lang == "de" else "%")
    b = f.get("breite")
    zeilen_x = [t["p_kopf"].format(datum=f["datum"])]
    if b:
        zeilen_x.append(t["p_breite_x"].format(anzahl=b["anzahl"], median=zahl(b["median_24h"], lang, True),
                                               plus=b["anteil_plus"]))
    if b and b.get("btc_24h") is not None:
        zeilen_x.append(f"Bitcoin: {zahl(b['btc_24h'], lang, True)}{pz}")
    zeilen_x.append(f"{t['p_bewegungen']}: " + ", ".join(_kurz(m["base"], m["chg24"], lang) for m in f["mover"]))
    zeilen_x.append(hinweis(cfg, lang))
    x = "\n".join(zeilen_x)
    if len(x) > X_MAX:  # zur Not ohne dritten Mover
        zeilen_x[-2] = f"{t['p_bewegungen']}: " + ", ".join(_kurz(m["base"], m["chg24"], lang) for m in f["mover"][:2])
        x = "\n".join(zeilen_x)

    tg = [f"📊 <b>{t['p_kopf'].format(datum=f['datum'])}</b>", ""]
    if b:
        tg.append(t["p_breite_tg"].format(anzahl=b["anzahl"], median=zahl(b["median_24h"], lang, True),
                                          plus=b["anteil_plus"]))
        if b.get("btc_24h") is not None:
            tg.append(t["p_btc_tg"].format(btc=zahl(b["btc_24h"], lang, True)))
        tg.append("")
    tg.append(f"<b>{t['p_bewegungen']}</b>")
    for m in f["mover"]:
        zusatz = f" – {t['p_ausloeser']}: {m['ausloeser']}" if m["ausloeser"] else ""
        tg.append(f"• {m['base']}: {zahl(m['chg24'], lang, True)}{pz}{zusatz}")
    tg += ["", f"<i>{hinweis(cfg, lang)}</i>"]
    return {"x": x, "telegram": "\n".join(tg)}


def markt_bild(beitrag: dict, cfg: dict, ziel: Path, verlauf_holen=None) -> Path:
    """Markt-Beitrag 4:5: Ring (Anteil im Plus), Halbwert, Balken der groessten Bewegungen."""
    import datetime as _dt
    from . import grafik
    from .design import absatz, etikett, fuss, hintergrund, karte, marke, thema_waehlen, font
    f = beitrag["fakten"]
    lang = beitrag.get("sprache", "de")
    tag = _dt.date.fromtimestamp(beitrag.get("ts") or _dt.datetime.now().timestamp()).isoformat()
    th = thema_waehlen("markt", tag)
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=sum(map(ord, tag)))
    marke(img, th, 80, 64, 64, untertitel=f["datum"])
    d = ImageDraw.Draw(img)
    etikett(d, th, 80, 170, "KRYPTO-MARKT · 24 STD.")
    y = 260
    b = f.get("breite")
    if b:
        karte(img, th, (80, y, W - 80, y + 330))
        grafik.anteil(img, th, (110, y + 30, 380, y + 300), b["anteil_plus"])
        d = ImageDraw.Draw(img)
        m = b["median_24h"]
        d.text((430, y + 40), f"Die Hälfte der {b['anzahl']} Small Caps lag über", font=font("Medium", 28),
               fill=th.neben)
        d.text((430, y + 80), f"{zahl(m, lang, True)} %", font=font("Bold", 120), fill=th.plus if m >= 0 else th.minus)
        absatz(d, th, 430, y + 230, f"{b['anteil_plus']} % der Coins stehen im Plus, "
               f"{100 - b['anteil_plus']} % im Minus.", W - 80 - 430 - 30, groesse=26, farbe=th.neben)
        y += 370
    reihen = [{"label": mv["base"], "wert": mv["chg24"], "text": f"{zahl(mv['chg24'], lang, True)} %",
               "farbe": th.plus if mv["chg24"] >= 0 else th.minus} for mv in f["mover"]]
    unten = y + 130 + 120 * len(reihen)
    verlaeufe = verlauf_holen([mv["base"] for mv in f["mover"]]) if verlauf_holen else {}
    if verlaeufe and all(verlaeufe.get(mv["base"]) for mv in f["mover"]):
        grafik.mover_linien(img, th, (80, y, W - 80, unten),
                            [dict(mv, verlauf=verlaeufe[mv["base"]], text=f"{zahl(mv['chg24'], lang, True)} %")
                             for mv in f["mover"]], titel="Größte Bewegungen · Kurs 72 Std. · Wert 24 Std.")
    else:   # keine Kurse erreichbar: Balken wie bisher
        grafik.balken(img, th, (80, y, W - 80, unten), reihen, titel="Größte Bewegungen in 24 Stunden")
    d = ImageDraw.Draw(img)
    y = unten + 30
    for mv in f["mover"]:
        if mv.get("ausloeser"):   # nur zeigen, wenn es eine Nachricht gibt
            y = absatz(d, th, 80, y, f"{mv['base']}: {mv['ausloeser']}", W - 160, groesse=27, farbe=th.akzent2,
                       gewicht="Medium", abstand=1.3)
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel
