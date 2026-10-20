"""Sprechtext je Szene. Mit Claude-API-Schluessel formuliert Claude die Saetze,
sonst gilt die feste Vorlage. Claude bekommt NUR die Fakten und darf nichts hinzufuegen."""
from __future__ import annotations

import json

import requests

SYSTEM = {
    "de": """Du schreibst Sprechertexte für ein gesichtsloses 30-Sekunden-Video über den Krypto-Markt (WhaleSqueeze).
Regeln:
- Pro Szene ein kurzer gesprochener Satz, in der vorgegebenen Reihenfolge. Ruhig, sachlich, verständlich, Du-Form.
- Nutze NUR Zahlen und Fakten aus dem JSON. Erfinde keine Ursachen, Kurse, Prognosen oder Kursziele.
- Steht bei einem Coin kein Auslöser, sag nichts über den Grund der Bewegung (keine Vermutung wie "spekulativ").
- Keine Empfehlung, keine Aufforderung zu kaufen oder zu verkaufen, keine Hype-Wörter, keine Emojis.
- Sag "Prozent", nicht "%". Zahlen genau wie angegeben, mit Komma und einer Nachkommastelle.
- Insgesamt höchstens {max_woerter} Wörter.
Antworte nur mit JSON: {{"zeilen": ["Satz 1", "Satz 2", ...]}} mit genau {n} Zeilen.""",
    "en": """You write voice-over lines for a faceless 30-second crypto market video (WhaleSqueeze).
Rules:
- One short spoken line per scene, in the given order. Plain, calm, factual English.
- Use ONLY numbers and facts from the JSON. Never invent causes, prices, predictions or targets.
- If a coin has no trigger, say nothing about why it moved (no guesses like "speculative").
- No advice, no calls to action to buy or sell, no hype words, no emojis.
- Say "percent", not "%". Keep numbers exactly as given (one decimal).
- Total length at most {max_woerter} words.
Return JSON only: {{"zeilen": ["line 1", "line 2", ...]}} with exactly {n} lines.""",
}


def vorlage(beitrag: dict) -> list[str]:
    return [s["vorlage"] for s in beitrag["szenen"]]


def schreiben(beitrag: dict, cfg: dict, api_key: str | None) -> tuple[list[str], str]:
    """Gibt (Zeilen, Quelle) zurueck. Quelle = 'claude' oder 'vorlage'."""
    if not api_key:
        return vorlage(beitrag), "vorlage"
    n = len(beitrag["szenen"])
    eingabe = {
        "fakten": beitrag["fakten"],
        "szenen": [{"typ": s["typ"], "daten": s["daten"], "beispiel": s["vorlage"]} for s in beitrag["szenen"]],
    }
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={
                "model": cfg["text"]["modell"],
                "max_tokens": 800,
                "system": SYSTEM[beitrag.get("sprache", "de")].format(max_woerter=cfg["text"]["max_woerter"], n=n),
                "messages": [{"role": "user", "content": json.dumps(eingabe, ensure_ascii=False)}],
            },
            timeout=60,
        )
        r.raise_for_status()
        txt = "".join(b.get("text", "") for b in r.json().get("content", []))
        zeilen = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])["zeilen"]
        if len(zeilen) != n or not all(isinstance(z, str) and z.strip() for z in zeilen):
            raise ValueError("falsche Zeilenzahl")
        return [z.strip() for z in zeilen], "claude"
    except Exception as e:  # Netz, Format: lieber die sichere Vorlage
        print(f"Claude-Text fehlgeschlagen ({e}) – nehme Vorlage")
        return vorlage(beitrag), "vorlage"
