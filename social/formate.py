"""Formate: waehlen aus den Bot-Daten die Fakten und legen die Szenen fest.

Jede Szene = ein Bild + ein gesprochener Satz. Der Text darf nur Fakten aus `fakten` nennen.
"""
from __future__ import annotations

import datetime as dt

from .daten import Daten, marktbreite

# Hashtags des Bots (deutsch) -> englische Beschreibung fuer den Sprechtext
TAG_EN = {
    "Listing": "a new exchange listing",
    "Delisting": "a delisting notice",
    "Partnerschaft": "a partnership announcement",
    "Upgrade": "a network upgrade",
    "Unlock": "a token unlock",
    "Rueckkauf": "a token buyback",
    "Airdrop": "an airdrop",
    "Funding": "a funding round",
    "ETF": "ETF news",
    "Hack": "a hack",
    "Klage": "a lawsuit",
    "Wale": "whale activity",
}


def _datum(ts: int) -> str:
    d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    return d.strftime("%B %-d")


def _vz(x: float) -> str:
    return f"+{x:.1f}" if x >= 0 else f"{x:.1f}"


def markt_30s(d: Daten, sperrliste: set[str], anzahl_mover: int = 3) -> dict:
    """'Market in 30 seconds': Altcoin-Breite + staerkste Bewegungen mit Ausloeser."""
    breite = marktbreite(d)
    mover = []
    for n in sorted(d.news, key=lambda n: abs(n.get("chg24") or 0), reverse=True):
        base = n.get("base")
        if not base or base.upper() in sperrliste or n.get("chg24") is None:
            continue
        drv = n.get("driver") or None
        tag = (drv.get("tags") or [None])[0] if drv else None
        mover.append({
            "base": base,
            "chg24": round(n["chg24"], 1),
            "ausloeser": TAG_EN.get(tag) if tag else None,
        })
        if len(mover) >= anzahl_mover:
            break
    if not mover:
        raise ValueError("Keine Bewegungen in news.json – kein Video")

    datum = _datum(d.ts)
    szenen = [{"typ": "titel", "daten": {"datum": datum},
               "vorlage": f"Crypto market in 30 seconds. {datum}."}]
    if breite:
        szenen.append({"typ": "breite", "daten": breite,
                       "vorlage": (f"Across {breite['anzahl']} small caps, the median coin moved "
                                   f"{_vz(breite['median_24h'])} percent in 24 hours. "
                                   f"{breite['anteil_plus']} percent are green.")})
    for m in mover:
        richtung = "up" if m["chg24"] >= 0 else "down"
        grund = (f"Likely trigger: {m['ausloeser']}." if m["ausloeser"]
                 else "No clear news. The move looks speculative or futures-driven.")
        szenen.append({"typ": "mover", "daten": m,
                       "vorlage": f"{m['base']} is {richtung} {abs(m['chg24']):.1f} percent. {grund}"})
    szenen.append({"typ": "outro", "daten": {},
                   "vorlage": "Every signal and its result is public at whalesqueeze dot com."})

    return {
        "format": "market_30s",
        "titel": f"Crypto market in 30 seconds – {datum}",
        "ts": d.ts,
        "fakten": {"titel": "Crypto market in 30 seconds", "zeitraum": "24 hours", "datum": datum, "breite": breite, "mover": mover},
        "szenen": szenen,
        "hashtags": ["#crypto", "#altcoins", "#cryptonews", "#bitcoin"],
    }


FORMATE = {"markt": markt_30s}
