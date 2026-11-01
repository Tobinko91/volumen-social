"""Eigene, lizenzfreie Hintergrundmusik fuer Videos ohne Stimme (Wunsch Tobias 01.11.2026: Reels/TikTok ohne
ElevenLabs-Kosten). Wird einmal mit ffmpeg aus Sinustoenen erzeugt (ruhige Flaeche + leiser Puls), also ohne
fremde Rechte. Auf TikTok (Entwurf in der App) kann Tobias stattdessen einen Trend-Sound waehlen.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

# Akkordfolge (Hz) je 4 Sekunden: Am – F – C – G, ruhig und neutral
AKKORDE = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 196.0, 261.63), (196.0, 246.94, 293.66)]
TAKT = 4.0


def _ausdruck(dauer: float) -> str:
    teile = []
    for i, akk in enumerate(AKKORDE):
        # Fenster je Akkord, weich ein- und ausgeblendet; die Folge wiederholt sich alle 16 s
        fenster = (f"between(mod(t,{TAKT * len(AKKORDE)}),{i * TAKT},{(i + 1) * TAKT})"
                   f"*sin(PI*mod(t,{TAKT})/{TAKT})")
        toene = "+".join(f"sin(2*PI*{f}*t)+0.3*sin(4*PI*{f}*t)" for f in akk)
        teile.append(f"{fenster}*({toene})")
    puls = "0.25*sin(2*PI*55*t)*exp(-6*mod(t,0.5))"   # leiser Herzschlag, 120 BPM
    return f"0.05*({'+'.join(teile)})+0.15*{puls}"


def erzeugen(ziel: Path, dauer: float = 64.0) -> Path:
    """Musik-Datei (AAC) erzeugen, falls noch nicht vorhanden. 64 s reichen, das Video schleift sie."""
    if ziel.exists() and ziel.stat().st_size > 0:
        return ziel
    ziel.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"aevalsrc='{_ausdruck(dauer)}':s=44100:d={dauer}",
                    "-af", "lowpass=f=2400,aecho=0.8:0.6:120:0.25,afade=t=in:d=1.5,"
                           f"afade=t=out:st={dauer - 2}:d=2,loudnorm=I=-18:TP=-2",
                    "-ac", "2", "-c:a", "aac", "-b:a", "128k", str(ziel)], check=True)
    return ziel


def pfad(cfg: dict, ausgabe: Path) -> Path | None:
    """Welche Musik: eigene Datei aus config.yaml (video.musik), 'generiert' oder keine."""
    m = (cfg.get("video") or {}).get("musik")
    if not m:
        return None
    if m == "generiert":
        return erzeugen(ausgabe / "musik_whalesqueeze.m4a")
    p = Path(m)
    return p if p.exists() else None
