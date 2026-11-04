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
        "s_breite": "Die Hälfte der {anzahl} kleinen Coins lag in 24 Stunden über {median_gesprochen} %, "
                    "die andere Hälfte darunter. {plus} % stehen im Plus.",
        "s_btc": " Bitcoin: {btc} %.",
        "gestiegen": "gestiegen", "gefallen": "gefallen",
        "s_mover": "{base} liegt {wert} % {richtung}. {grund}",
        "hoeher": "höher", "tiefer": "tiefer",
        "grund_ja": "Wahrscheinlicher Auslöser: {ausloeser}.",
        "grund_nein": "",
        "s_outro": "Folge WhaleSqueeze für tägliche Krypto-Daten.",
        # Kommentar-Frage am Ende (04.11.2026): Kommentare sind auf TikTok/Instagram ein starkes Reichweiten-Signal
        "cta": {"markt": "Welchen Coin sollen wir morgen prüfen? Schreib es in die Kommentare.",
                "wal": "Bei welchem Coin sollen wir als Nächstes auf die Wale schauen? Schreib es in die Kommentare.",
                "wissen": "Was sollen wir als Nächstes erklären? Schreib es in die Kommentare.",
                "warum": "Welchen Coin sollen wir als Nächstes erklären? Schreib es in die Kommentare."},
        "s_cta_folgen": "Und folge WhaleSqueeze.", "b_kommentar": "↓ IN DIE KOMMENTARE",
        "s_haken": "{base} ist in 24 Stunden um {wert} % {verb}. Das hat den Markt heute bewegt.",
        "haken_hoch": "gestiegen", "haken_runter": "gefallen",
        "b_frage": "WARUM IST {base} {verb}?",
        "s_haken_zahl": "{base} ist in 24 Stunden um {wert} % {verb}. Das hat den Markt heute bewegt.",
        "haken_hoch_zahl": "gestiegen", "haken_runter_zahl": "gefallen",
        "b_haken": "GRÖSSTE BEWEGUNG HEUTE", "b_warum": "WARUM? ↓", "b_folgen": "FOLGEN FÜR TÄGLICHE DATEN",
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
        "s_breite": "Half of {anzahl} small caps did better than {median_gesprochen}% in 24 hours, "
                    "half did worse. {plus}% are green.",
        "s_btc": " Bitcoin: {btc}%.",
        "gestiegen": "up", "gefallen": "down",
        "s_mover": "{base} is {richtung} {wert}%. {grund}",
        "hoeher": "up", "tiefer": "down",
        "grund_ja": "Likely trigger: {ausloeser}.",
        "grund_nein": "",
        "s_outro": "Follow WhaleSqueeze for daily crypto data.",
        "cta": {"markt": "Which coin should we check tomorrow? Comment below.",
                "wal": "Which coin should we check for whales next? Comment below.",
                "wissen": "What should we explain next? Comment below.",
                "warum": "Which coin should we explain next? Comment below."},
        "s_cta_folgen": "And follow WhaleSqueeze.", "b_kommentar": "↓ COMMENT BELOW",
        "s_haken": "Why did {base} {verb} {wert}% in 24 hours? Here is what moved crypto today.",
        "haken_hoch": "jump", "haken_runter": "drop",   # Frage als Haken (04.11.2026)
        "b_frage": "WHY DID {base} {verb}?",
        "s_haken_zahl": "{base} {verb} {wert}% in 24 hours. Here is what moved crypto today.",
        "haken_hoch_zahl": "jumped", "haken_runter_zahl": "dropped",
        "b_haken": "TODAY'S BIGGEST MOVE", "b_warum": "WHY? ↓", "b_folgen": "FOLLOW FOR DAILY DATA",
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


def outro_szene(art: str, lang: str) -> dict:
    """Letzte Szene: Kommentar-Frage + Folgen (Ton) und die Frage gross im Bild."""
    t = T[lang]
    frage = t["cta"][art]
    return {"typ": "outro", "daten": {"_cta": frage.split("?")[0] + "?"}, "vorlage": f"{frage} {t['s_cta_folgen']}"}


def haken_test_an() -> bool:
    try:
        import yaml
        from pathlib import Path
        cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
        return bool((cfg.get("video") or {}).get("haken_test", True))
    except Exception:
        return True


def haken_art(tag: dt.date | None = None, test: bool | None = None) -> str:
    """A/B-Test des Einstiegs (Wunsch Tobias 04.11.2026): Tage abwechselnd 'frage' (Frage im Ton und gross im Bild)
    und 'zahl' (Aussage mit der Zahl, wie bis 04.11.). Ein Tag = eine Art fuer alle Formate, damit der
    Wochenbericht sauber vergleicht. Ohne Test (config video.haken_test: false) immer 'frage'."""
    if not (haken_test_an() if test is None else test):
        return "frage"
    return "frage" if (tag or dt.date.today()).toordinal() % 2 == 0 else "zahl"


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
    """Seit 01.11.2026 (Wunsch Tobias): Zeichen statt Wort, z. B. '+6.9' – die Untertitel zeigen '%' und Vorzeichen,
    eine KI-Stimme liest '+6.9%' trotzdem als 'plus 6.9 percent' vor."""
    return zahl(x, lang, True)


def zahl_gesprochen_alt(x: float, lang: str) -> str:
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
