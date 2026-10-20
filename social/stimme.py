"""KI-Stimme. Mit ElevenLabs-Schluessel und voice_id: echte Stimme je Szene.
Ohne Schluessel: Stille in passender Laenge (fuer Probevideos)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import requests


def dauer(datei: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(datei)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def _stille(datei: Path, sekunden: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{sekunden:.2f}", "-c:a", "aac", str(datei)],
        check=True,
    )


class StimmeFehlt(Exception):
    pass


def voice_id(cfg: dict, key: str) -> str:
    """Feste ID aus config.yaml oder Suche nach dem Namen der eigenen Stimme im ElevenLabs-Konto."""
    st = cfg["stimme"]
    if st.get("voice_id"):
        return st["voice_id"]
    name = (st.get("voice_name") or "").strip().lower()
    r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=30)
    r.raise_for_status()
    for v in r.json().get("voices", []):
        if (v.get("name") or "").strip().lower() == name:
            st["voice_id"] = v["voice_id"]          # fuer diesen Lauf merken
            return v["voice_id"]
    raise StimmeFehlt(f"Stimme '{st.get('voice_name')}' nicht im ElevenLabs-Konto gefunden")


def _elevenlabs(text: str, datei: Path, cfg: dict, key: str) -> None:
    vid = voice_id(cfg, key)
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
        headers={"xi-api-key": key, "accept": "audio/mpeg", "content-type": "application/json"},
        json={"text": text, "model_id": cfg["stimme"]["modell"],
              "voice_settings": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15}},
        timeout=120,
    )
    r.raise_for_status()
    datei.write_bytes(r.content)


def sprechen(zeilen: list[str], ordner: Path, cfg: dict, key: str | None) -> tuple[list[Path], list[float], str]:
    """Erzeugt je Zeile eine Tondatei. Gibt (Dateien, Dauern, Quelle) zurueck."""
    ordner.mkdir(parents=True, exist_ok=True)
    echt = bool(key and (cfg["stimme"].get("voice_id") or cfg["stimme"].get("voice_name")))
    dateien, dauern = [], []
    for i, z in enumerate(zeilen):
        if echt:
            f = ordner / f"ton_{i:02d}.mp3"
            _elevenlabs(z, f, cfg, key)
            d = dauer(f) + 0.35          # kurze Pause nach jedem Satz
        else:
            f = ordner / f"ton_{i:02d}.m4a"
            d = max(cfg["video"]["min_szene_s"], len(z.split()) / cfg["video"]["woerter_pro_sekunde"] + 0.4)
            _stille(f, d)
        dateien.append(f)
        dauern.append(max(d, cfg["video"]["min_szene_s"]))
    return dateien, dauern, ("elevenlabs" if echt else "stille")
