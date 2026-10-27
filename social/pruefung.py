"""Automatische Pruefung vor der Freigabe: Zahlen, verbotene Woerter, Sperrliste, Laenge."""
from __future__ import annotations

import re

from .links import ohne_eigene_links
from .sprache import T

ZAHL = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?")
TAUSENDER_EN = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")   # 100,000 -> 100000 (nur Englisch)


def _norm(text: str, lang: str) -> str:
    return TAUSENDER_EN.sub("", text) if lang == "en" else text


def _zahlen_aus(obj, lang: str = "de") -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(abs(float(obj)))
    elif isinstance(obj, dict):
        for v in obj.values():
            out += _zahlen_aus(v, lang)
    elif isinstance(obj, list):
        for v in obj:
            out += _zahlen_aus(v, lang)
    elif isinstance(obj, str):
        out += [abs(float(z.replace(",", "."))) for z in ZAHL.findall(_norm(obj, lang))]
    return out


def pruefen(zeilen: list[str], beitrag: dict, cfg: dict, sperrliste: set[str],
            erlaubt_fusszeile: bool = False) -> list[str]:
    """Liste der Fehler; leer = bestanden."""
    fehler = []
    text = ohne_eigene_links(" ".join(zeilen))   # Kennungen in eigenen Links sind keine Datenzahlen
    p = cfg["pruefung"]
    if erlaubt_fusszeile:  # feste Hinweise duerfen in Posts stehen, sie werden nicht mitgeprueft
        for h in (h for h in cfg["hinweise"].values() if h):   # leere Hinweise ueberspringen
            text = text.replace(h, " ")
        text = text.replace("Keine Anlageberatung", " ")
        for lang in T:   # Pflicht-Hinweis anderer Sprachen ("Not financial advice.") ist erlaubt
            text = text.replace(T[lang]["hinweis"], " ")
    klein = text.lower()

    for w in p["verboten"]:
        if w in klein:
            fehler.append(f"verbotene Wendung: '{w}'")

    for coin in sperrliste:
        if re.search(rf"\b{re.escape(coin)}\b", text, re.IGNORECASE):
            fehler.append(f"Coin auf der Sperrliste: {coin}")

    lang = cfg.get("sprache", "de")
    erlaubt = _zahlen_aus(beitrag["fakten"], lang)
    ohne_aufzaehlung = re.sub(r"(?m)^\s*\d+\.\s", " ", _norm(text, lang))   # "1. ", "2. " am Zeilenanfang sind keine Daten
    for z in ZAHL.findall(ohne_aufzaehlung):
        wert = abs(float(z.replace(",", ".")))
        if not any(abs(wert - e) <= p["zahlen_toleranz"] for e in erlaubt):
            fehler.append(f"Zahl {z} steht nicht in den Daten")

    woerter = len(text.split())
    grenze = 220 if erlaubt_fusszeile else cfg["text"]["max_woerter"] + 10   # Posts (X + Telegram) duerfen laenger sein
    if woerter > grenze:
        fehler.append(f"zu lang: {woerter} Woerter")
    if len(zeilen) != len(beitrag["szenen"]):
        fehler.append("Zeilenzahl passt nicht zu den Szenen")
    return fehler
