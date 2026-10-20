"""Alle sichtbaren und gesprochenen Texte je Sprache. Start: Deutsch (entschieden 20.10.2026)."""
from __future__ import annotations

import datetime as dt

MONATE_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
             "September", "Oktober", "November", "Dezember"]

# Hashtags des Bots -> Beschreibung des Ausloesers
TAG = {
    "de": {
        "Listing": "ein neues Börsen-Listing", "Delisting": "ein angekündigtes Delisting",
        "Partnerschaft": "eine neue Partnerschaft", "Upgrade": "ein Netzwerk-Upgrade",
        "Unlock": "eine Token-Freigabe", "Rueckkauf": "ein Token-Rückkauf", "Airdrop": "ein Airdrop",
        "Funding": "eine Finanzierungsrunde", "ETF": "ETF-Nachrichten", "Hack": "ein Hack",
        "Klage": "eine Klage", "Wale": "Wal-Aktivität",
    },
    "en": {
        "Listing": "a new exchange listing", "Delisting": "a delisting notice",
        "Partnerschaft": "a partnership announcement", "Upgrade": "a network upgrade",
        "Unlock": "a token unlock", "Rueckkauf": "a token buyback", "Airdrop": "an airdrop",
        "Funding": "a funding round", "ETF": "ETF news", "Hack": "a hack", "Klage": "a lawsuit",
        "Wale": "whale activity",
    },
}

T = {
    "de": {
        "titel": "Krypto-Markt in 30 Sekunden",
        "zeitraum": "24 Stunden",
        "s_titel": "Krypto-Markt in 30 Sekunden. {datum}.",
        "s_breite": "Von {anzahl} kleinen Coins ist der mittlere in 24 Stunden um {median} Prozent {richtung}. "
                    "{plus} Prozent stehen im Plus.",
        "gestiegen": "gestiegen", "gefallen": "gefallen",
        "s_mover": "{base} liegt {wert} Prozent {richtung}. {grund}",
        "hoeher": "höher", "tiefer": "tiefer",
        "grund_ja": "Wahrscheinlicher Auslöser: {ausloeser}.",
        "grund_nein": "Keine klare Nachricht. Die Bewegung wirkt spekulativ oder von Futures getrieben.",
        "s_outro": "Mehr Marktdaten findest du auf whalesqueeze Punkt com.",
        "adresse_gesprochen": " Punkt com",
        "b_markt": "KRYPTO-MARKT", "b_30s": "IN 30 SEKUNDEN",
        "b_breite": "ALTCOIN-MARKT · 24 STD.", "b_median": "Median von {anzahl} Small Caps",
        "b_plus": "{p} % im Plus", "b_minus": "{p} % im Minus",
        "b_mover": "TOP-MOVER {nr}/{von}", "b_24h": "24 Std.",
        "b_ausloeser": "AUSLÖSER: {a}", "b_keine": "KEINE KLARE NACHRICHT",
        "b_outro": "Marktdaten. Erklärt. Ehrlich.",
        "hashtags": ["#krypto", "#bitcoin", "#altcoins", "#kryptonews", "#börse"],
    },
    "en": {
        "titel": "Crypto market in 30 seconds",
        "zeitraum": "24 hours",
        "s_titel": "Crypto market in 30 seconds. {datum}.",
        "s_breite": "Across {anzahl} small caps, the median coin is {richtung} {median} percent in 24 hours. "
                    "{plus} percent are green.",
        "gestiegen": "up", "gefallen": "down",
        "s_mover": "{base} is {richtung} {wert} percent. {grund}",
        "hoeher": "up", "tiefer": "down",
        "grund_ja": "Likely trigger: {ausloeser}.",
        "grund_nein": "No clear news. The move looks speculative or futures-driven.",
        "s_outro": "More market data at whalesqueeze dot com.",
        "adresse_gesprochen": " dot com",
        "b_markt": "CRYPTO MARKET", "b_30s": "IN 30 SECONDS",
        "b_breite": "ALTCOIN MARKET · 24H", "b_median": "median of {anzahl} small caps",
        "b_plus": "{p}% green", "b_minus": "{p}% red",
        "b_mover": "TOP MOVER {nr}/{von}", "b_24h": "24h",
        "b_ausloeser": "TRIGGER: {a}", "b_keine": "NO CLEAR NEWS",
        "b_outro": "Market data. Explained. Honest.",
        "hashtags": ["#crypto", "#altcoins", "#cryptonews", "#bitcoin"],
    },
}


def datum(ts: int, lang: str) -> str:
    d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    if lang == "de":
        return f"{d.day}. {MONATE_DE[d.month - 1]}"
    return d.strftime("%B %-d")


def zahl(x: float, lang: str, vorzeichen: bool = False) -> str:
    """Eine Nachkommastelle; Deutsch mit Komma."""
    s = f"{x:+.1f}" if vorzeichen else f"{x:.1f}"
    return s.replace(".", ",") if lang == "de" else s
