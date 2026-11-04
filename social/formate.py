"""Formate: waehlen aus den Bot-Daten die Fakten und legen die Szenen fest.

Jede Szene = ein Bild + ein gesprochener Satz. Der Text darf nur Fakten aus `fakten` nennen.
"""
from __future__ import annotations

from .daten import Daten, marktlage
from .sprache import haken_art, TAG, T, datum, zahl, zahl_gesprochen


def markt_30s(d: Daten, sperrliste: set[str], lang: str | None = None, anzahl_mover: int = 3) -> dict:
    """'Krypto-Markt in 30 Sekunden': Altcoin-Breite + staerkste Bewegungen mit Ausloeser."""
    from .design import SPRACHE
    lang = lang or SPRACHE
    t = T[lang]
    breite = marktlage(d)   # markt.json vom Bot, sonst Ersatzrechnung aus coins/
    mover = []
    for n in sorted(d.news, key=lambda n: abs(n.get("chg24") or 0), reverse=True):
        base = n.get("base")
        if not base or base.upper() in sperrliste or n.get("chg24") is None:
            continue
        drv = n.get("driver") or None
        tag = (drv.get("tags") or [None])[0] if drv else None
        mover.append({"base": base, "chg24": round(n["chg24"], 1),
                      "ausloeser": TAG[lang].get(tag) if tag else None})
        if len(mover) >= anzahl_mover:
            break
    if not mover:
        raise ValueError("Keine Bewegungen in news.json – kein Video")

    tag_txt = datum(d.ts, lang)
    # Haken (Wunsch Tobias 01.11.2026): die ersten 1-2 Sekunden entscheiden auf TikTok/Reels, ob jemand bleibt.
    # Darum zuerst die groesste Bewegung als riesige Zahl, nicht der Titel.
    h = mover[0]
    import datetime as _dt
    art = haken_art(_dt.date.fromtimestamp(d.ts)) if lang == "en" else "zahl"   # A/B-Test nur englisch
    hoch = h["chg24"] >= 0
    if art == "frage":
        vorlage = t["s_haken"].format(base=h["base"], wert=zahl(abs(h["chg24"]), lang),
                                      verb=t["haken_hoch"] if hoch else t["haken_runter"])
        frage = t["b_frage"].format(base=h["base"], verb=(t["haken_hoch"] if hoch else t["haken_runter"]).upper())
    else:
        sz, vh, vr = ("s_haken_zahl", "haken_hoch_zahl", "haken_runter_zahl") if "s_haken_zahl" in t else \
            ("s_haken", "haken_hoch", "haken_runter")
        vorlage = t[sz].format(base=h["base"], wert=zahl(abs(h["chg24"]), lang), verb=t[vh] if hoch else t[vr])
        frage = None
    szenen = [{"typ": "haken", "haken": art, "daten": dict(h, datum=tag_txt, _frage=frage), "vorlage": vorlage}]
    if breite:
        szenen.append({"typ": "breite", "daten": breite, "vorlage": t["s_breite"].format(
            anzahl=breite["anzahl"], median_gesprochen=zahl_gesprochen(breite["median_24h"], lang),
            plus=breite["anteil_plus"])
            + (t["s_btc"].format(btc=zahl_gesprochen(breite["btc_24h"], lang)) if "btc_24h" in breite else "")})
    for m in mover:
        grund = t["grund_ja"].format(ausloeser=m["ausloeser"]) if m["ausloeser"] else t["grund_nein"]
        szenen.append({"typ": "mover", "daten": m, "vorlage": t["s_mover"].format(
            base=m["base"], wert=zahl(abs(m["chg24"]), lang),
            richtung=t["hoeher"] if m["chg24"] >= 0 else t["tiefer"], grund=grund).strip()})
    szenen.append({"typ": "outro", "daten": {}, "vorlage": t["s_outro"]})

    return {
        "format": "markt_30s",
        "sprache": lang,
        "titel": f"{t['titel']} – {tag_txt}",
        "ts": d.ts,
        "fakten": {"titel": t["titel"], "zeitraum": t["zeitraum"], "datum": tag_txt,
                   "breite": breite, "mover": mover},
        "szenen": szenen,
        "hashtags": t["hashtags"],
    }


FORMATE = {"markt": markt_30s}
