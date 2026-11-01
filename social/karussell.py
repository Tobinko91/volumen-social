"""S11 Wal-Karussell (sonntags): die Wale der Woche als Bilderserie.

Folien (4:5): Deckblatt mit Balken aller Wale -> je Wal eine Folie (wie „Whale of the day“) -> Abschluss „Folgen“.
Posten: Instagram-Karussell, TikTok-Fotoserie, X (erste 4 Folien), Telegram-Album (siehe karussell_posten.py).
Nur Wal-Daten (Prozentpunkte der Gesamtmenge in 7 Tagen), keine Empfehlung, keine Bot-Ergebnisse.
"""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

from PIL import ImageDraw

from . import grafik, wal
from .sprache import MONATE_EN, zahl

T = {
    "en": {"etikett": "WHALES OF THE WEEK", "titel": "Whales of the week", "sub": "Biggest whale moves in 7 days",
           "folie": "WHALES OF THE WEEK · {i}/{n}", "einheit": "pp", "chart": "Change of whale share · 7 days",
           "ende1": "A new whale every day.", "ende2": "Follow @whalesqueeze",
           "zeile": "${b}: {v} pp", "tg_kopf": "🐋 <b>Whales of the week</b>",
           "tg_satz": "Where whales moved the most in the last 7 days (change of their share of total supply):",
           "x_kopf": "🐋 Whales of the week (change of whale share, 7 days):"},
    "de": {"etikett": "WALE DER WOCHE", "titel": "Wale der Woche", "sub": "Größte Wal-Bewegungen in 7 Tagen",
           "folie": "WALE DER WOCHE · {i}/{n}", "einheit": "PP", "chart": "Veränderung des Wal-Anteils · 7 Tage",
           "ende1": "Jeden Tag ein neuer Wal.", "ende2": "Folge @whalesqueeze",
           "zeile": "${b}: {v} PP", "tg_kopf": "🐋 <b>Wale der Woche</b>",
           "tg_satz": "Wo Wale in den letzten 7 Tagen am stärksten bewegt haben (Veränderung ihres Anteils an der Gesamtmenge):",
           "x_kopf": "🐋 Wale der Woche (Veränderung Wal-Anteil, 7 Tage):"},
}


def fakten(wale: list[dict]) -> dict:
    return {"zeitraum_tage": 7, "anzahl": len(wale), "wale": [wal.fakten(w) for w in wale]}


def texte(wale: list[dict], cfg: dict, lang: str = "en") -> dict:
    from .sprache import hinweis as _hinweis
    t, hw = T[lang], _hinweis(cfg, lang)
    zeilen = [t["zeile"].format(b=w["base"], v=zahl(w["wal_7d"], lang, True)) for w in wale]
    x = "\n".join([t["x_kopf"], *zeilen, hw])
    while len(x) > 280 and len(zeilen) > 1:
        zeilen = zeilen[:-1]
        x = "\n".join([t["x_kopf"], *zeilen, hw])
    tg = [t["tg_kopf"], "", html.escape(t["tg_satz"]), ""]
    tg += [f"• {html.escape(t['zeile'].format(b=w['base'], v=zahl(w['wal_7d'], lang, True)))}" for w in wale]
    tg += ["", f"<i>{html.escape(hw)}</i>"]
    return {"x": x, "telegram": "\n".join(tg)}


def _deckblatt(wale: list[dict], cfg: dict, ziel: Path, lang: str, jetzt: float) -> Path:
    from .design import absatz, etikett, font, fuss, hintergrund, marke, thema_waehlen
    t = T[lang]
    th = thema_waehlen("markt", f"karussell:{int(jetzt) // 86400}")
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=11)
    ende = dt.datetime.fromtimestamp(jetzt)
    anfang = ende - dt.timedelta(days=7)
    zeitraum = (f"{MONATE_EN[anfang.month - 1][:3]} {anfang.day} – {MONATE_EN[ende.month - 1][:3]} {ende.day}"
                if lang == "en" else f"{anfang.day}.{anfang.month}. – {ende.day}.{ende.month}.")
    marke(img, th, 80, 64, 64, untertitel=zeitraum)
    d = ImageDraw.Draw(img)
    etikett(d, th, 80, 170, t["etikett"])
    d.text((80, 250), t["titel"], font=font("Bold", 100), fill=th.text)
    absatz(d, th, 80, 380, t["sub"], W - 160, groesse=38, farbe=th.neben, gewicht="Medium")
    reihen = [{"label": f"${w['base']}", "wert": w["wal_7d"],
               "farbe": th.plus if w["wal_7d"] >= 0 else th.minus,
               "text": f"{zahl(w['wal_7d'], lang, True)} {t['einheit']}"} for w in wale]
    grafik.balken(img, th, (60, 470, W - 60, 1160), reihen, titel=t["chart"])
    d = ImageDraw.Draw(img)
    pfeil = "Swipe →" if lang == "en" else "Wischen →"
    f = font("Bold", 34)
    d.text((W - 80 - d.textlength(pfeil, font=f), 1180), pfeil, font=f, fill=th.akzent)
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel


def _abschluss(cfg: dict, ziel: Path, lang: str) -> Path:
    from .design import font, fuss, hintergrund, logo, thema_waehlen
    t = T[lang]
    th = thema_waehlen("markt", "karussell:ende")
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=5)
    lg = logo(240)
    img.paste(lg, ((W - 240) // 2, 330), lg)
    d = ImageDraw.Draw(img)
    for y, text, f, farbe in ((660, t["ende1"], font("Bold", 64), th.text),
                              (770, t["ende2"], font("Bold", 72), th.akzent),
                              (880, "Telegram · X · Instagram · TikTok · YouTube", font("Medium", 34), th.neben)):
        d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=farbe)
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    img.convert("RGB").save(ziel)
    return ziel


def bauen(wale: list[dict], cfg: dict, ordner: Path, lang: str = "en", jetzt: float | None = None) -> list[Path]:
    """Alle Folien + karussell.json + post.png (= Deckblatt, fuer Story und Vorschau)."""
    import time
    jetzt = jetzt or time.time()
    t = T[lang]
    ordner.mkdir(parents=True, exist_ok=True)
    folien = [_deckblatt(wale, cfg, ordner / "folie_00.png", lang, jetzt)]
    for i, w in enumerate(wale, 1):
        folien.append(wal.bild(w, cfg, ordner / f"folie_{i:02d}.png", lang, jetzt,
                               etikett_text=t["folie"].format(i=i, n=len(wale))))
    folien.append(_abschluss(cfg, ordner / f"folie_{len(wale) + 1:02d}.png", lang))
    (ordner / "post.png").write_bytes(folien[0].read_bytes())
    (ordner / "karussell.json").write_text(json.dumps({"folien": [f.name for f in folien]}), encoding="utf-8")
    return folien


def folien(ordner: Path) -> list[Path]:
    k = json.loads((ordner / "karussell.json").read_text(encoding="utf-8"))
    return [ordner / n for n in k["folien"]]
