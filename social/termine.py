"""S13 Termine der Woche (montags): US-Termine, die Krypto bewegen (CPI, Arbeitsmarkt, PCE, Fed) + Optionsverfall.

Liste in inhalte/termine.yaml (Zeit in New-Yorker Ortszeit), UTC wird hier umgerechnet (Sommer-/Winterzeit).
Der Optionsverfall auf Deribit (letzter Freitag im Monat, 08:00 UTC) wird berechnet.
Nur Termine und was sie bedeuten, keine Prognose, keine Empfehlung, keine Quellenangabe im Beitrag.
"""
from __future__ import annotations

import datetime as dt
import html
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from PIL import ImageDraw

from .sprache import MONATE_DE, MONATE_EN

NY = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
TAGE = {"en": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"], "de": ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]}
PFLEGE = ("cpi", "nfp", "pce")   # muessen immer >= 4 Wochen voraus eingetragen sein
T = {
    "en": {"etikett": "KEY DATES", "titel": "This week in macro", "sub": "US dates that can move crypto",
           "x_kopf": "📅 Key dates this week", "tg_kopf": "📅 <b>Key dates this week</b>",
           "nichts": "No major US data this week."},
    "de": {"etikett": "TERMINE", "titel": "Die Woche im Blick", "sub": "US-Termine, die Krypto bewegen können",
           "x_kopf": "📅 Termine der Woche", "tg_kopf": "📅 <b>Termine der Woche</b>",
           "nichts": "Keine großen US-Daten diese Woche."},
}


def _esc(s: str) -> str:
    return html.escape(s, quote=False)


def laden(pfad: Path) -> dict:
    return yaml.safe_load(pfad.read_text(encoding="utf-8"))


def _datum(x) -> dt.date:
    return x if isinstance(x, dt.date) else dt.date.fromisoformat(str(x))


def letzter_freitag(jahr: int, monat: int) -> dt.date:
    ende = dt.date(jahr + monat // 12, monat % 12 + 1, 1) - dt.timedelta(days=1)
    return ende - dt.timedelta(days=(ende.weekday() - 4) % 7)


def woche(daten: dict, montag: dt.date, lang: str = "en") -> list[dict]:
    """Alle Termine Montag..Sonntag, sortiert, mit ET- und UTC-Zeit und Texten in der Sprache."""
    sonntag = montag + dt.timedelta(days=6)
    roh = [dict(t, datum=_datum(t["datum"])) for t in daten["termine"]]
    for j, mo in {(montag.year, montag.month), (sonntag.year, sonntag.month)}:
        lf = letzter_freitag(j, mo)
        if montag <= lf <= sonntag:
            et = dt.datetime.combine(lf, dt.time(8, 0), UTC).astimezone(NY)
            roh.append({"datum": lf, "zeit": et.strftime("%H:%M"), "art": "verfall"})
    out = []
    for t in roh:
        if not (montag <= t["datum"] <= sonntag):
            continue
        h, m = map(int, str(t["zeit"]).split(":"))
        et = dt.datetime.combine(t["datum"], dt.time(h, m), NY)
        u = et.astimezone(UTC)
        txt = daten["arten"][t["art"]][lang]
        monat = ""
        if t.get("monat"):
            j, mo = map(int, str(t["monat"]).split("-"))
            monat = (MONATE_EN if lang == "en" else MONATE_DE)[mo - 1]
        out.append({"art": t["art"], "datum": t["datum"].isoformat(), "tag": TAGE[lang][t["datum"].weekday()],
                    "tag_nr": t["datum"].day, "monat_kurz": (MONATE_EN if lang == "en" else MONATE_DE)[t["datum"].month - 1][:3],
                    "et": _uhr(et, lang), "utc": u.strftime("%H:%M"), "titel": txt["titel"],
                    "info": txt["info"].format(monat=monat), "_ts": u.timestamp()})
    return sorted(out, key=lambda e: e["_ts"])


def _uhr(t: dt.datetime, lang: str) -> str:
    if lang == "en":
        return t.strftime("%I:%M %p").lstrip("0")
    return t.strftime("%H:%M")


def pflege_luecken(daten: dict, montag: dt.date, tage: int = 28) -> list[str]:
    """Welche Pflicht-Arten haben keinen Termin mehr in den naechsten `tage` Tagen nach dieser Woche?"""
    grenze = montag + dt.timedelta(days=7 + tage)
    luecken = []
    for art in PFLEGE:
        letzte = max((_datum(t["datum"]) for t in daten["termine"] if t["art"] == art), default=None)
        if letzte is None or letzte < grenze:
            luecken.append(f"{art} (zuletzt {letzte})")
    return luecken


def fakten(ereignisse: list[dict]) -> dict:
    return {"termine": [{k: v for k, v in e.items() if not k.startswith("_")} for e in ereignisse]}


def _tag(e: dict, lang: str) -> str:
    if lang == "en":
        return f"{e['tag'].title()} {e['monat_kurz']} {e['tag_nr']}"
    return f"{e['tag'].title()} {e['tag_nr']}.{int(e['datum'][5:7])}."


def _zeile(e: dict, lang: str) -> str:
    return f"{_tag(e, lang)} · {e['et']} ET / {e['utc']} UTC"


def texte(ereignisse: list[dict], cfg: dict, lang: str = "en") -> dict:
    from .sprache import hinweis as _hinweis
    t, hw = T[lang], _hinweis(cfg, lang)
    xz = [f"• {e['titel']}: {_tag(e, lang)}, {e['utc']} UTC" for e in ereignisse]
    x = "\n".join([t["x_kopf"], *xz, hw])
    while len(x) > 280 and len(xz) > 1:
        xz = xz[:-1]
        x = "\n".join([t["x_kopf"], *xz, hw])
    tg = [t["tg_kopf"], ""]
    for e in ereignisse:
        tg += [f"<b>{_esc(e['titel'])}</b>", _esc(_zeile(e, lang)), _esc(e["info"]), ""]
    tg.append(f"<i>{_esc(hw)}</i>")
    return {"x": x, "telegram": "\n".join(tg)}


def bild(ereignisse: list[dict], cfg: dict, ziel: Path, montag: dt.date, lang: str = "en") -> Path:
    from .design import absatz, etikett, font, fuss, hintergrund, marke, thema_waehlen
    t = T[lang]
    th = thema_waehlen("markt", f"termine:{montag.isoformat()}")
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=13)
    so = montag + dt.timedelta(days=6)
    mn = MONATE_EN if lang == "en" else MONATE_DE
    zeitraum = (f"{mn[montag.month - 1][:3]} {montag.day} – {mn[so.month - 1][:3]} {so.day}" if lang == "en"
                else f"{montag.day}.{montag.month}. – {so.day}.{so.month}.")
    marke(img, th, 80, 64, 64, untertitel=zeitraum)
    d = ImageDraw.Draw(img)
    etikett(d, th, 80, 170, t["etikett"])
    d.text((80, 240), t["titel"], font=font("Bold", 84), fill=th.text)
    absatz(d, th, 80, 350, t["sub"], W - 160, groesse=36, farbe=th.neben, gewicht="Medium")
    y = 440
    platz = (1200 - y) // max(len(ereignisse), 1)
    hoch = max(110, min(170, platz - 18))
    for e in ereignisse:
        if y + hoch > 1210:
            break
        d.rounded_rectangle([60, y, W - 60, y + hoch], radius=26, fill=th.karte)
        d.rounded_rectangle([80, y + 18, 210, y + hoch - 18], radius=20, outline=th.akzent, width=3)
        ft, fn = font("Bold", 30), font("Bold", 54)
        mitte = y + hoch / 2
        d.text((145 - d.textlength(e["tag"], font=ft) / 2, mitte - 48), e["tag"], font=ft, fill=th.akzent)
        nr = str(e["tag_nr"])
        d.text((145 - d.textlength(nr, font=fn) / 2, mitte - 14), nr, font=fn, fill=th.text)
        farbe = th.akzent2 if e["art"] in ("fomc", "protokoll") else th.text
        d.text((240, y + 22), e["titel"], font=font("Bold", 40), fill=farbe)
        d.text((240, y + 72), f"{e['et']} ET · {e['utc']} UTC", font=font("Medium", 30), fill=th.akzent)
        if hoch >= 150:
            absatz(d, th, 240, y + 108, e["info"], W - 320, groesse=22, farbe=th.neben, abstand=1.25)
        y += hoch + 18
    if not ereignisse:
        absatz(d, th, 80, 520, t["nichts"], W - 160, groesse=44, gewicht="Bold")
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel
