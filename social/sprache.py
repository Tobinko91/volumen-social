"""Alle sichtbaren und gesprochenen Texte je Sprache. Start: Deutsch (entschieden 20.10.2026)."""
from __future__ import annotations

import datetime as dt

MONATE_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
             "September", "Oktober", "November", "Dezember"]

MONATE_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]

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
        "s_breite": "Die Hälfte der {anzahl} kleinen Coins lag in 24 Stunden über {median_gesprochen} Prozent, "
                    "die andere Hälfte darunter. {plus} Prozent stehen im Plus.",
        "s_btc": " Bitcoin: {btc} Prozent.",
        "gestiegen": "gestiegen", "gefallen": "gefallen",
        "s_mover": "{base} liegt {wert} Prozent {richtung}. {grund}",
        "hoeher": "höher", "tiefer": "tiefer",
        "grund_ja": "Wahrscheinlicher Auslöser: {ausloeser}.",
        "grund_nein": "",
        "s_outro": "Mehr Marktdaten findest du auf whalesqueeze Punkt com.",
        "adresse_gesprochen": " Punkt com",
        "b_markt": "KRYPTO-MARKT", "b_30s": "IN 30 SEKUNDEN",
        "b_breite": "ALTCOIN-MARKT · 24 STD.", "b_median": "Hälfte der {anzahl} Small Caps lag darüber",
        "b_plus": "{p} % im Plus", "b_minus": "{p} % im Minus",
        "b_mover": "TOP-MOVER {nr}/{von}", "b_24h": "24 Std.",
        "b_ausloeser": "AUSLÖSER: {a}", "b_keine": "KEINE KLARE NACHRICHT",
        "b_outro": "Marktdaten. Erklärt. Ehrlich.",
        "hashtags": ["#krypto", "#bitcoin", "#altcoins", "#kryptonews", "#börse"],
        "hinweis": "Keine Anlageberatung.",
        "p_kopf": "Krypto-Markt am {datum}",
        "p_breite_x": "{anzahl} Small Caps in 24 Std.: Hälfte über {median} %, {plus} % im Plus.",
        "p_breite_tg": "Die Hälfte der {anzahl} Small Caps lag in 24 Stunden über {median} %, "
                       "die andere Hälfte darunter. {plus} % stehen im Plus.",
        "p_btc_tg": "Bitcoin: {btc} % in 24 Stunden.",
        "p_bewegungen": "Größte Bewegungen", "p_ausloeser": "Auslöser",
    },
    "en": {
        "titel": "Crypto market in 30 seconds",
        "zeitraum": "24 hours",
        "s_titel": "Crypto market in 30 seconds. {datum}.",
        "s_breite": "Half of {anzahl} small caps did better than {median_gesprochen} percent in 24 hours, "
                    "half did worse. {plus} percent are green.",
        "s_btc": " Bitcoin: {btc} percent.",
        "gestiegen": "up", "gefallen": "down",
        "s_mover": "{base} is {richtung} {wert} percent. {grund}",
        "hoeher": "up", "tiefer": "down",
        "grund_ja": "Likely trigger: {ausloeser}.",
        "grund_nein": "",
        "s_outro": "More market data at whalesqueeze dot com.",
        "adresse_gesprochen": " dot com",
        "b_markt": "CRYPTO MARKET", "b_30s": "IN 30 SECONDS",
        "b_breite": "ALTCOIN MARKET · 24H", "b_median": "half of {anzahl} small caps above, half below",
        "b_plus": "{p}% green", "b_minus": "{p}% red",
        "b_mover": "TOP MOVER {nr}/{von}", "b_24h": "24h",
        "b_ausloeser": "TRIGGER: {a}", "b_keine": "NO CLEAR NEWS",
        "b_outro": "Market data. Explained. Honest.",
        "hashtags": ["#crypto", "#bitcoin", "#altcoins", "#cryptonews", "#whalesqueeze"],
        "hinweis": "Not financial advice.",
        "p_kopf": "Crypto market, {datum}",
        "p_breite_x": "{anzahl} small caps, 24h: half above {median}%, {plus}% green.",
        "p_breite_tg": "Half of {anzahl} small caps did better than {median}% in 24 hours, "
                       "half did worse. {plus}% are green.",
        "p_btc_tg": "Bitcoin: {btc}% in 24 hours.",
        "p_bewegungen": "Biggest moves", "p_ausloeser": "Trigger",
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


def zahl_gesprochen(x: float, lang: str) -> str:
    """+7,3 -> 'plus 7,3' (Vorzeichen als Wort, damit die Stimme es richtig liest)."""
    w = {"de": ("plus", "minus"), "en": ("plus", "minus")}[lang]
    return f"{w[0] if x >= 0 else w[1]} {zahl(abs(x), lang)}"


SPRACHEN = tuple(T)


def stempel(d: dt.datetime | dt.date, lang: str, jahr: bool = True) -> str:
    """Datum fuer Bilder: '26 October 2026' / '26. Oktober 2026'."""
    if lang == "de":
        return f"{d.day}. {MONATE_DE[d.month - 1]}" + (f" {d.year}" if jahr else "")
    return f"{MONATE_EN[d.month - 1]} {d.day}" + (f", {d.year}" if jahr else "")


def hinweis(cfg: dict, lang: str) -> str:
    """Pflicht-Hinweis unter Posts: in der Kanal-Sprache aus config.yaml (Wunsch Tobias 22.10.), sonst aus T."""
    return cfg["hinweise"]["post_text"] if lang == cfg.get("sprache", "de") else T[lang]["hinweis"]
