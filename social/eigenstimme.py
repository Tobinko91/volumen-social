"""Eigene Stimme von Tobias fuer die Formation des Tages (Test 2 Wochen, Entscheidung Tobias 11.11.2026).

Warum: YouTube und Meta stufen gleichfoermige Massenware ohne menschlichen Anteil herab. Eine echte Stimme ist der
einfachste menschliche Anteil; der Wochenbericht vergleicht die Haltequote mit Brian (Format „formationich_video“).

Ablauf:
1. 18:00 (plan.sh): Der Server baut den Sprechtext des Abend-Videos (inkl. Aufloesung von gestern und Community-Zahl,
   die dann fest bleibt) und schickt ihn Tobias als Skript. Zahlen sind ausgeschrieben, damit sie leicht zu lesen sind.
2. Tobias antwortet im Redaktions-Bot mit einer Sprachnachricht (Mikrofon gedrueckt halten). freigabe.py speichert sie.
3. 21:30: Liegt die Aufnahme vor, schreibt ElevenLabs Speech-to-Text die Woerter mit Zeitmarken heraus. Daran wird die
   Aufnahme in die einzelnen Saetze geschnitten (je Szene ein Satz). Klappt etwas nicht: Brian wie immer.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import requests

STT = "https://api.elevenlabs.io/v1/speech-to-text"


def ordner(ausgabe: Path) -> Path:
    return Path(ausgabe) / "eigene_stimme"


def heute() -> str:
    return time.strftime("%Y-%m-%d")


def skript_speichern(ausgabe: Path, zeilen: list[str], community: dict | None, gestern_ordner: str | None,
                     tag: str | None = None) -> Path:
    o = ordner(ausgabe)
    o.mkdir(parents=True, exist_ok=True)
    p = o / f"skript_{tag or heute()}.json"
    p.write_text(json.dumps({"zeilen": zeilen, "community": community, "gestern_ordner": gestern_ordner}))
    return p


def skript_laden(ausgabe: Path, tag: str | None = None) -> dict | None:
    try:
        return json.loads((ordner(ausgabe) / f"skript_{tag or heute()}.json").read_text())
    except Exception:
        return None


def aufnahme(ausgabe: Path, tag: str | None = None) -> Path | None:
    p = ordner(ausgabe) / f"aufnahme_{tag or heute()}.ogg"
    return p if p.exists() and p.stat().st_size > 1000 else None


def wartet(ausgabe: Path, tag: str | None = None) -> bool:
    """Gibt es heute ein Skript ohne Aufnahme? (Dann ist eine Audiodatei von Tobias die Aufnahme, keine Musik.)"""
    return skript_laden(ausgabe, tag) is not None and aufnahme(ausgabe, tag) is None


def skript_text(zeilen: list[str], bis: str = "21:15") -> str:
    """Nachricht an Tobias: nummerierte Saetze, Zahlen ausgeschrieben."""
    from .stimme import sprechbar
    z = [f"🎙️ Formation des Tages – bitte einsprechen (bis {bis} Uhr)", "",
         "So geht's: im Chat mit mir das Mikrofon unten rechts gedrückt halten, ruhig auf Englisch vorlesen, "
         "zwischen den Sätzen kurz Luft holen. Etwa 30–40 Sekunden. Versprecher? Einfach neu aufnehmen, "
         "die letzte Aufnahme zählt.", ""]
    for i, s in enumerate(zeilen, 1):
        z.append(f"{i}. {sprechbar(s)[0]}")
    z += ["", "Keine Zeit? Dann spricht Brian wie immer."]
    return "\n".join(z)


def speichern(ausgabe: Path, daten: bytes, tag: str | None = None) -> Path:
    p = ordner(ausgabe) / f"aufnahme_{tag or heute()}.ogg"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(daten)
    return p


def transkribieren(datei: Path, key: str, post=requests.post) -> list[dict]:
    """ElevenLabs Speech-to-Text (Scribe) -> [{w, a, e}] je gesprochenem Wort."""
    with open(datei, "rb") as f:
        r = post(STT, headers={"xi-api-key": key}, data={"model_id": "scribe_v1", "language_code": "en",
                                                          "timestamps_granularity": "word"},
                 files={"file": (datei.name, f, "audio/ogg")}, timeout=120)
    if r.status_code >= 300:
        raise RuntimeError(f"Speech-to-Text {r.status_code}: {r.text[:150]}")
    return [{"w": w["text"], "a": float(w["start"]), "e": float(w["end"])}
            for w in r.json().get("words") or [] if w.get("type", "word") == "word" and w.get("text", "").strip()]


def grenzen(zeilen: list[str], woerter: list[dict]) -> list[tuple[float, float]]:
    """Zeit-Abschnitt je Satz. Satzgrenzen nach dem Anteil der Woerter (Versprecher verschieben nur wenig);
    geschnitten wird in der Pause zwischen zwei Woertern."""
    from .stimme import sprechbar
    if not woerter:
        raise ValueError("keine Woerter erkannt")
    n = [max(1, len(sprechbar(z)[0].split())) for z in zeilen]
    gesamt, T = sum(n), len(woerter)
    if not 0.6 <= T / gesamt <= 1.5:
        raise ValueError(f"Aufnahme passt nicht zum Skript ({T} statt etwa {gesamt} Woerter)")
    out, start, kum = [], max(0.0, woerter[0]["a"] - 0.15), 0
    for k in range(len(zeilen) - 1):
        kum += n[k]
        i = min(T - 2, max(0, round(kum * T / gesamt) - 1))
        schnitt = (woerter[i]["e"] + woerter[i + 1]["a"]) / 2
        out.append((start, schnitt))
        start = schnitt
    out.append((start, woerter[-1]["e"] + 0.25))
    return out


def schneiden(datei: Path, abschnitte: list[tuple[float, float]], ziel: Path, cfg: dict) -> tuple[list[Path], list[float]]:
    from .stimme import dauer
    ziel.mkdir(parents=True, exist_ok=True)
    dateien, dauern = [], []
    for i, (a, e) in enumerate(abschnitte):
        f = ziel / f"ton_{i:02d}.mp3"   # mp3 = echte Stimme (Musik leiser), wie bei Brian
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{e:.3f}", "-i", str(datei),
                        "-af", "loudnorm=I=-16:TP=-1.5,highpass=f=80", "-ar", "44100", "-ac", "1",
                        "-c:a", "libmp3lame", "-b:a", "160k", str(f)], check=True)
        dateien.append(f)
        dauern.append(max(dauer(f) + 0.35, cfg["video"]["min_szene_s"]))
    return dateien, dauern


def sprecher(datei: Path, key: str, skript: list[str] | None = None, post=requests.post):
    """-> Funktion mit der Form von stimme.sprechen, die die Aufnahme von Tobias nutzt."""
    def sprechen(zeilen, ziel, cfg, _key):
        if skript is not None and list(zeilen) != list(skript):
            raise ValueError("Sprechtext weicht vom Skript ab (Daten geaendert)")
        woerter = transkribieren(datei, key, post)
        abschnitte = grenzen(zeilen, woerter)
        dateien, dauern = schneiden(datei, abschnitte, ziel, cfg)
        for f, (a, e) in zip(dateien, abschnitte):   # Wort-Untertitel aus den echten Zeitmarken
            ws = [dict(w, a=round(w["a"] - a, 3), e=round(w["e"] - a, 3)) for w in woerter if a <= w["a"] < e]
            if ws:
                f.with_suffix(".json").write_text(json.dumps(ws))
        return dateien, dauern, "Stimme Tobias"
    return sprechen
