"""'Wal des Tages': Coin mit der groessten Wal-Veraenderung in 7 Tagen (Bild 4:5 + Text fuer Telegram und X).

Daten: coins/<BASE>.json vom Bot (wale, wale_7d, holder, holder_7d, wale_verlauf; Bot 9.10, Wunsch Nr. 9).
Auswahl in daten.wal_des_tages(); Rueckfall ohne wale_7d: hoechster aktueller Wal-Anteil.
Nur Daten, keine Empfehlung. Jede Zahl im Text steht in fakten() (Pruefung).
"""
from __future__ import annotations

import datetime as dt
import html
from pathlib import Path

from PIL import ImageDraw

from .sprache import MONATE_DE, zahl

X_MAX = 280

W = {
    "de": {"etikett": "WAL DES TAGES", "wal": "Wale halten {w} % der Menge", "pp": "{v} Prozentpunkte in 7 Tagen",
           "boerse": "Börsen-Anteil {b} %", "boerse7": "Börsen-Anteil {b} % ({v} in 7 Tagen)",
           "holder": "Holder: {h} (vor 7 Tagen {h7})", "holder1": "Holder: {h}",
           "chart": "Anteil an der Gesamtmenge · 30 Tage", "kurve_w": "Wale", "kurve_b": "Börsen",
           "jetzt": "jetzt", "vor": "vor {n} T.", "titel": "🐋 <b>Wal des Tages: ${b}</b>",
           "x_kopf": "🐋 Wal des Tages: ${b}",
           "v_haken7": "Wale haben ihren Anteil an {b} in 7 Tagen um {v} Prozentpunkte {verb}.",
           "v_haken": "Wale halten {w} % von {b}.", "mehr": "erhöht", "weniger": "gesenkt",
           "v_verlauf": "Wale halten jetzt {w} % der Gesamtmenge.",
           "v_boerse": "{b} % liegen auf Börsen.", "v_holder": "Holder: {h}.",
           "v_holder7": "Holder: {h}, vor 7 Tagen {h7}.",
           "v_frage": "WALE IN BEWEGUNG", "v_details": "BÖRSEN & HOLDER"},
    "en": {"etikett": "WHALE OF THE DAY", "wal": "Whales hold {w}% of supply", "pp": "{v} percentage points in 7 days",
           "boerse": "Exchange share {b}%", "boerse7": "Exchange share {b}% ({v} in 7 days)",
           "holder": "Holders: {h} (7 days ago {h7})", "holder1": "Holders: {h}",
           "chart": "Share of total supply · 30 days", "kurve_w": "Whales", "kurve_b": "Exchanges",
           "jetzt": "now", "vor": "{n}d ago", "titel": "🐋 <b>Whale of the day: ${b}</b>",
           "x_kopf": "🐋 Whale of the day: ${b}",
           "v_haken7": "Whales {verb} their share of {b} by {v} percentage points in 7 days.",
           "v_haken": "Whales hold {w}% of {b}.", "mehr": "raised", "weniger": "cut",
           "v_verlauf": "Whales now hold {w}% of the supply.",
           "v_boerse": "{b}% sits on exchanges.", "v_holder": "Holders: {h}.",
           "v_holder7": "Holders: {h}, 7 days ago {h7}.",
           "v_frage": "WHALES ON THE MOVE", "v_details": "EXCHANGES & HOLDERS"},
}


def fakten(w: dict) -> dict:
    """Alle Zahlen, die in Text und Bild vorkommen duerfen."""
    f = {k: w.get(k) for k in ("base", "quelle", "wal", "boerse", "wal_7d", "boerse_7d", "holder", "holder_7d",
                               "chg24")}
    f["zeitraum_tage"] = [7, 30]
    if w.get("verlauf"):
        f["verlauf_tage"] = round((w["verlauf"][-1][0] - w["verlauf"][0][0]) / 86400)
    return f


def _tsd(n: int, lang: str) -> str:
    return str(int(n))   # ohne Tausenderpunkt: "12.345" wuerde die Pruefung als 12,345 lesen


def zeilen(w: dict, lang: str = "de") -> list[str]:
    t = W[lang]
    z = []
    if w.get("wal") is not None:
        z.append(t["wal"].format(w=zahl(w["wal"], lang)))
    if w.get("wal_7d") is not None:
        z.append(t["pp"].format(v=zahl(w["wal_7d"], lang, True)))
    if w.get("boerse") is not None:
        z.append(t["boerse7"].format(b=zahl(w["boerse"], lang), v=zahl(w["boerse_7d"], lang, True))
                 if w.get("boerse_7d") is not None else t["boerse"].format(b=zahl(w["boerse"], lang)))
    if w.get("holder") is not None:
        z.append(t["holder"].format(h=_tsd(w["holder"], lang), h7=_tsd(w["holder_7d"], lang))
                 if w.get("holder_7d") is not None else t["holder1"].format(h=_tsd(w["holder"], lang)))
    return z


def texte(w: dict, cfg: dict, lang: str = "de") -> dict:
    t, z = W[lang], zeilen(w, lang)
    from .sprache import hinweis as _hinweis
    hinweis = _hinweis(cfg, lang)
    x = "\n".join([t["x_kopf"].format(b=w["base"]), *z, hinweis])
    while len(x) > X_MAX and len(z) > 1:
        z = z[:-1]
        x = "\n".join([t["x_kopf"].format(b=w["base"]), *z, hinweis])
    tg = [t["titel"].format(b=html.escape(w["base"])), ""] + [f"• {html.escape(s)}" for s in zeilen(w, lang)]
    tg += ["", f"<i>{html.escape(hinweis)}</i>"]
    return {"x": x, "telegram": "\n".join(tg)}


def video_szenen(w: dict, lang: str = "de") -> dict:
    """Szenen fuer das Video 'Whale of the day' (Wunsch Tobias 01.11.2026). Gleiche Fakten wie der Bild-Beitrag."""
    t = W[lang]
    if w.get("wal_7d") is not None:
        v = w["wal_7d"]
        haken = t["v_haken7"].format(b=w["base"], v=zahl(abs(v), lang), verb=t["mehr"] if v >= 0 else t["weniger"])
    else:
        haken = t["v_haken"].format(b=w["base"], w=zahl(w.get("wal") or 0, lang))
    szenen = [{"typ": "wal_haken", "daten": w, "vorlage": haken}]
    if len(w.get("verlauf") or []) >= 2 and w.get("wal") is not None:
        szenen.append({"typ": "wal_verlauf", "daten": w, "vorlage": t["v_verlauf"].format(w=zahl(w["wal"], lang))})
    teile = []
    if w.get("boerse") is not None:
        teile.append(t["v_boerse"].format(b=zahl(w["boerse"], lang)))
    if w.get("holder") is not None:
        teile.append(t["v_holder7"].format(h=_tsd(w["holder"], lang), h7=_tsd(w["holder_7d"], lang))
                     if w.get("holder_7d") is not None else t["v_holder"].format(h=_tsd(w["holder"], lang)))
    if teile:
        szenen.append({"typ": "wal_details", "daten": w, "vorlage": " ".join(teile)})
    from .sprache import T as _T
    szenen.append({"typ": "outro", "daten": {}, "vorlage": _T[lang]["s_outro"]})
    return {"format": "wal", "sprache": lang, "szenen": szenen, "fakten": fakten(w),
            "titel": t["x_kopf"].format(b=w["base"])}


def bild(w: dict, cfg: dict, ziel: Path, lang: str = "de", jetzt: float | None = None) -> Path:
    from . import grafik
    from .design import absatz, etikett, font, fuss, hintergrund, karte, marke, thema_waehlen
    t = W[lang]
    tag = dt.date.today().isoformat()
    th = thema_waehlen("markt", f"{tag}:wal:{w['base']}")
    Wd, H = 1080, 1350
    img = hintergrund(th, Wd, H, saat=len(w["base"]) + 7)
    d0 = dt.datetime.fromtimestamp(jetzt or dt.datetime.now().timestamp())
    datum = f"{d0.day}. {MONATE_DE[d0.month - 1]}" if lang == "de" else d0.strftime("%B %-d")
    marke(img, th, 80, 64, 64, untertitel=datum)
    d = ImageDraw.Draw(img)
    etikett(d, th, 80, 170, t["etikett"])
    d.text((80, 246), f"${w['base']}", font=font("Bold", 92), fill=th.text)
    y = 370
    if w.get("wal_7d") is not None:
        v = w["wal_7d"]
        d.text((80, y), f"{zahl(v, lang, True)} {'pp' if lang == 'en' else 'PP'}", font=font("Bold", 120), fill=th.plus if v >= 0 else th.minus)
        y = absatz(d, th, 80, y + 150, t["pp"].format(v=zahl(v, lang, True)), Wd - 160, groesse=30, farbe=th.neben)
    elif w.get("wal") is not None:
        d.text((80, y), f"{zahl(w['wal'], lang)} %", font=font("Bold", 120), fill=th.akzent)
        y = absatz(d, th, 80, y + 150, t["wal"].format(w=zahl(w["wal"], lang)), Wd - 160, groesse=30, farbe=th.neben)
    y += 30
    v = w.get("verlauf") or []
    if len(v) >= 2:
        tage = round((v[-1][0] - v[0][0]) / 86400)
        labels = [""] * len(v)
        labels[0], labels[-1] = t["vor"].format(n=tage), t["jetzt"]
        reihen = [{"name": t["kurve_w"], "werte": [p[1] for p in v], "farbe": th.akzent}]
        if all(p[2] is not None for p in v):
            reihen.append({"name": t["kurve_b"], "werte": [p[2] for p in v], "farbe": th.akzent2})
        grafik.linien(img, th, (80, y, Wd - 80, y + 460), reihen, labels, titel=t["chart"], einheit="%" if lang == "en" else " %",
                      flaeche=False)
        y += 500
    rest = zeilen(w, lang)[2:]   # Boerse und Holder unter der Grafik, auf einer Karte (lesbar vor jedem Hintergrund)
    if rest:
        karte(img, th, (80, y, Wd - 80, y + 40 + 44 * len(rest)), radius=22)
    d = ImageDraw.Draw(img)
    y += 22
    for s in rest:
        y = absatz(d, th, 112, y, s, Wd - 224, groesse=30, farbe=th.text, gewicht="Medium", abstand=1.45)
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel
