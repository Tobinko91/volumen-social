"""Claude schreibt aus den Quelltexten einen eigenen deutschen News-Beitrag (Telegram + X)."""
from __future__ import annotations

import datetime as dt
import json
import re
from zoneinfo import ZoneInfo

import requests

SYSTEM = """Du bist Redakteur von WhaleSqueeze, einem sachlichen deutschen Krypto-Nachrichtenkanal.
Du bekommst Titel und Kurztexte mehrerer Quellen zu EINEM Ereignis, dazu das heutige Datum und
umgerechnete deutsche Uhrzeiten. Schreib daraus einen eigenen, gründlichen Beitrag für die Community.

Regeln:
- Nur Fakten aus den Quellen. Keine Vermutung, keine Kursprognose, kein Kursziel, keine Empfehlung,
  keine Aufforderung zu kaufen oder zu verkaufen, keine Hype-Wörter, keine Emojis.
- Eigene Worte, nichts wörtlich übernehmen (höchstens ein Zitat bis 8 Wörter in Anführungszeichen mit Urheber).
- Schreib Tatsachen direkt: "Die Fed entscheidet am Mittwoch, 28. Oktober, um 19:00 Uhr", nicht
  "Berichten zufolge ...". Verboten: "Berichten zufolge", "laut Berichten", "angeblich", "soll ... haben".
  Nenne keine Medien namentlich. Ist etwas wirklich unbestätigt, sag konkret wer es sagt
  (z. B. "Die SEC hat noch nicht entschieden", "Das Unternehmen bestätigt das nicht").
- Immer konkret, soweit in den Quellen: Datum mit Wochentag, Uhrzeit in deutscher Zeit (nutze die
  mitgelieferten Umrechnungen), wer entscheidet oder spricht, wie es danach weitergeht (nächster Termin,
  Frist, Abstimmung), Beträge und Vergleichswerte (vorher/jetzt).
- Zahlen exakt wie in den Quellen (deutsche Schreibweise mit Komma ist erlaubt). Keine eigenen Rechnungen.
- Ruhig, verständlich, Du-Form nur wenn nötig. Fachbegriffe kurz erklären.
- Ist die Meldung kein Krypto- oder Finanzmarkt-Thema oder zu unklar, setze "geeignet": false.

Antworte NUR mit JSON:
{"geeignet": true,
 "rubrik": "eines von: Bitcoin, Altcoins, Regulierung, Börsen, ETF, Sicherheit, Makro, Unternehmen",
 "schlagzeile": "höchstens 70 Zeichen",
 "kernsatz": "ein Satz, höchstens 200 Zeichen: was passiert, wann (Datum, Uhrzeit), wer",
 "punkte": ["3 bis 5 Sätze: Termine/Ablauf, Ausgangslage mit Zahlen, warum es wichtig ist, wie es danach weitergeht"],
 "x": "Text für X, höchstens 230 Zeichen, ohne Link und ohne Hashtags, mit Datum/Uhrzeit wenn vorhanden",
 "coins": ["Ticker der genannten Coins, z. B. BTC"]}"""


def schreiben(gruppe: dict, cfg: dict, api_key: str) -> dict | None:
    meldungen = [{"quelle": m["quelle"], "titel": m["titel"], "kurztext": m["kurz"]} for m in gruppe["meldungen"][:6]]
    quelltext = " ".join(m["titel"] + " " + m["kurz"] for m in gruppe["meldungen"])
    eingabe = {"heute": heute_text(), "deutsche_uhrzeiten": deutsche_zeiten(quelltext), "meldungen": meldungen}
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": cfg["text"]["modell"], "max_tokens": 1400, "system": SYSTEM,
              "messages": [{"role": "user", "content": json.dumps(eingabe, ensure_ascii=False)}]},
        timeout=90,
    )
    r.raise_for_status()
    txt = "".join(b.get("text", "") for b in r.json().get("content", []))
    d = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    if not d.get("geeignet", True):
        return None
    for k in ("rubrik", "schlagzeile", "kernsatz", "punkte", "x"):
        if not d.get(k):
            raise ValueError(f"Feld fehlt: {k}")
    d["punkte"] = [p for p in d["punkte"] if isinstance(p, str) and p.strip()][:5]
    return d


BERLIN = ZoneInfo("Europe/Berlin")
ZONEN = {"ET": "America/New_York", "EDT": "America/New_York", "EST": "America/New_York",
         "UTC": "UTC", "GMT": "UTC", "CET": "Europe/Berlin", "CEST": "Europe/Berlin"}
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
UHRZEIT = re.compile(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\s*\(?\b(ET|EDT|EST|UTC|GMT)\b", re.I)


def heute_text(jetzt: dt.datetime | None = None) -> str:
    j = (jetzt or dt.datetime.now(BERLIN)).astimezone(BERLIN)
    return f"{WOCHENTAGE[j.weekday()]}, {j.day}.{j.month}.{j.year}"


def deutsche_zeiten(text: str, jetzt: dt.datetime | None = None) -> list[str]:
    """Uhrzeiten mit Zeitzone aus den Quellen in deutsche Zeit umrechnen (Tag = heute, fuer die Sommer-/Winterzeit).
    Ergebnis z. B. ['2:00 p.m. ET = 19:00 Uhr deutsche Zeit']."""
    j = (jetzt or dt.datetime.now(BERLIN)).astimezone(BERLIN)
    out = []
    for m in UHRZEIT.finditer(text):
        h, mi, ampm, zone = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower(), m.group(4).upper()
        if ampm.startswith("p") and h < 12:
            h += 12
        if ampm.startswith("a") and h == 12:
            h = 0
        if h > 23 or mi > 59 or (not ampm and not m.group(2)):
            continue   # "2 ET" ohne Minuten/am-pm ist zu unsicher
        quelle = dt.datetime(j.year, j.month, j.day, h, mi, tzinfo=ZoneInfo(ZONEN[zone]))
        d = quelle.astimezone(BERLIN)
        z = f"{m.group(0).strip()} = {d.hour}:{d.minute:02d} Uhr deutsche Zeit"
        if z not in out:
            out.append(z)
    return out[:8]
