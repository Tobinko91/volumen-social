"""Zentrale Link-Funktion (Auftrag S7, Entscheidung 24.10.2026 "Erst messen, dann wachsen").

Jeder Link zu whalesqueeze.com bekommt eine Kennung, damit die Besucher-Statistik der Website
(volumen-web W3) sieht, welcher Kanal und welches Format Besucher bringt:
  ?utm_source=<kanal>&utm_medium=social&utm_campaign=<format>&utm_content=<beitrags-id>
Nur Links ueber diese Funktion bauen, nie von Hand.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlencode

DOMAIN = "https://whalesqueeze.com"
KANAELE = ("tiktok", "instagram", "youtube", "x", "telegram")
TG_MAX = 1024   # Telegram: hoechstens 1024 Zeichen unter einem Bild
_SLUG = re.compile(r"[^a-z0-9_-]+")


def _slug(text: str) -> str:
    s = _SLUG.sub("-", str(text).strip().lower()).strip("-")
    return s[:60] or "unbekannt"


def link(kanal: str, format: str, beitrag_id: str, pfad: str = "/", lang: str | None = None) -> str:
    """Link zu whalesqueeze.com mit Kanal-, Format- und Beitrags-Kennung.

    kanal: tiktok | instagram | youtube | x | telegram
    format: z. B. markt_30s, wissen, news, coincheck, wal, bio
    beitrag_id: z. B. der Ausgabe-Ordner "20261024-0730_markt"
    pfad: Seite auf der Website, z. B. "/coin/ake/"
    lang: "en" setzt den Pfad unter /en/ (Website PR #8), Deutsch bleibt ohne Vorsilbe.
    """
    lang = lang or _sprache()
    k = str(kanal).strip().lower()
    if k not in KANAELE:
        raise ValueError(f"Unbekannter Kanal: {kanal!r} (erlaubt: {', '.join(KANAELE)})")
    p = "/" + str(pfad or "/").lstrip("/")
    if lang == "en" and not p.startswith("/en/"):
        p = "/en" + p
    q = urlencode({"utm_source": k, "utm_medium": "social", "utm_campaign": _slug(format),
                   "utm_content": _slug(beitrag_id)})
    return f"{DOMAIN}{p}?{q}"


def _sprache() -> str:
    from . import design
    return design.SPRACHE


def bio_links(lang: str | None = None) -> dict[str, str]:
    """Fertige Profil-Links (Bio) je Kanal."""
    return {k: link(k, "bio", "profil", lang=lang) for k in KANAELE}


def telegram_zeile(format: str, beitrag_id: str, pfad: str = "/", lang: str | None = None) -> str:
    """Link-Zeile fuer Telegram-Texte (HTML-Modus)."""
    url = link("telegram", format, beitrag_id, pfad, lang)
    text = "Mehr Daten" if (lang or _sprache()) == "de" else "More data"
    return f'🔗 <a href="{html.escape(url)}">{text}: whalesqueeze.com</a>'   # & -> &amp; (Telegram-HTML)


def mit_telegram_link(tg_text: str, format: str, beitrag_id: str, pfad: str = "/", lang: str | None = None) -> str:
    """Haengt die Link-Zeile vor den Hinweis 'Keine Anlageberatung' (letzte Zeile) bzw. ans Ende."""
    zeile = telegram_zeile(format, beitrag_id, pfad, lang)
    if len(tg_text) + len(zeile) + 2 > TG_MAX:   # Telegram schneidet Bildtexte bei 1024 Zeichen ab -> kein halber Link
        return tg_text
    teile = tg_text.rstrip("\n").split("\n")
    if teile and ("Anlageberatung" in teile[-1] or "financial advice" in teile[-1]):   # Hinweis bleibt unten
        return "\n".join(teile[:-1] + [zeile, teile[-1]])
    return "\n".join(teile + ["", zeile])


def beschreibungen(text: str, format: str, beitrag_id: str, pfad: str = "/", lang: str | None = None) -> dict[str, str]:
    """Video-Beschreibung je Kanal, jeweils mit eigenem Link (YouTube, TikTok, Instagram)."""
    return {k: f"{text.rstrip()}\n\n{link(k, format, beitrag_id, pfad, lang)}"
            for k in ("youtube", "tiktok", "instagram")}


def ohne_eigene_links(text: str) -> str:
    """Fuer die Pruefung: eigene Links entfernen (ihre Kennungen sind keine Datenzahlen)."""
    text = re.sub(r'<a href="https://whalesqueeze\.com[^"]*">([^<]*)</a>', r"\1", text)
    return re.sub(r"https://whalesqueeze\.com\S*", " ", text)
