"""Claude schreibt aus den Quelltexten einen eigenen deutschen News-Beitrag (Telegram + X)."""
from __future__ import annotations

import json

import requests

SYSTEM = """Du bist Redakteur von WhaleSqueeze, einem sachlichen deutschen Krypto-Nachrichtenkanal.
Du bekommst Titel und Kurztexte mehrerer Quellen zu EINEM Ereignis. Schreib daraus einen eigenen Beitrag.

Regeln:
- Nur Fakten aus den Quellen. Keine Vermutung, keine Kursprognose, kein Kursziel, keine Empfehlung,
  keine Aufforderung zu kaufen oder zu verkaufen, keine Hype-Wörter, keine Emojis.
- Eigene Worte, nichts wörtlich übernehmen (höchstens ein Zitat bis 8 Wörter in Anführungszeichen mit Urheber).
- Berichtet nur eine Quelle, schreib "laut <Quelle>". Widersprechen sich Quellen, sag das.
- Zahlen exakt wie in den Quellen (deutsche Schreibweise mit Komma ist erlaubt). Keine eigenen Rechnungen.
- Ruhig, verständlich, Du-Form nur wenn nötig. Fachbegriffe kurz erklären.
- Ist die Meldung kein Krypto-Thema oder zu unklar, setze "geeignet": false.

Antworte NUR mit JSON:
{"geeignet": true,
 "rubrik": "eines von: Bitcoin, Altcoins, Regulierung, Börsen, ETF, Sicherheit, Makro, Unternehmen",
 "schlagzeile": "höchstens 70 Zeichen",
 "kernsatz": "ein Satz, höchstens 160 Zeichen: was ist passiert",
 "punkte": ["2 bis 3 kurze Sätze: Einordnung, warum es wichtig ist, was offen ist"],
 "x": "Text für X, höchstens 220 Zeichen, ohne Link und ohne Hashtags",
 "coins": ["Ticker der genannten Coins, z. B. BTC"]}"""


def schreiben(gruppe: dict, cfg: dict, api_key: str) -> dict | None:
    eingabe = [{"quelle": m["quelle"], "titel": m["titel"], "kurztext": m["kurz"]} for m in gruppe["meldungen"][:6]]
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": cfg["text"]["modell"], "max_tokens": 900, "system": SYSTEM,
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
    d["punkte"] = [p for p in d["punkte"] if isinstance(p, str) and p.strip()][:3]
    return d
