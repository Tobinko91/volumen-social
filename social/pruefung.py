"""Automatische Pruefung vor der Freigabe: Zahlen, verbotene Woerter, Sperrliste, Laenge."""
from __future__ import annotations

import re

ZAHL = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?")


def _zahlen_aus(obj) -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(abs(float(obj)))
    elif isinstance(obj, dict):
        for v in obj.values():
            out += _zahlen_aus(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _zahlen_aus(v)
    elif isinstance(obj, str):
        out += [abs(float(z.replace(",", "."))) for z in ZAHL.findall(obj)]
    return out


def pruefen(zeilen: list[str], beitrag: dict, cfg: dict, sperrliste: set[str],
            erlaubt_fusszeile: bool = False) -> list[str]:
    """Liste der Fehler; leer = bestanden."""
    fehler = []
    text = " ".join(zeilen)
    p = cfg["pruefung"]
    if erlaubt_fusszeile:  # feste Hinweise duerfen in Posts stehen, sie werden nicht mitgeprueft
        for h in cfg["hinweise"].values():
            text = text.replace(h, " ")
        text = text.replace("Keine Anlageberatung", " ")
    klein = text.lower()

    for w in p["verboten"]:
        if w in klein:
            fehler.append(f"verbotene Wendung: '{w}'")

    for coin in sperrliste:
        if re.search(rf"\b{re.escape(coin)}\b", text, re.IGNORECASE):
            fehler.append(f"Coin auf der Sperrliste: {coin}")

    erlaubt = _zahlen_aus(beitrag["fakten"])
    ohne_aufzaehlung = re.sub(r"(?m)^\s*\d+\.\s", " ", text)   # "1. ", "2. " am Zeilenanfang sind keine Daten
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
