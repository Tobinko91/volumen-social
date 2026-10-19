"""Setzt Bilder und Ton mit ffmpeg zu einem 9:16-Video zusammen (kein Schnitt per Hand)."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def bauen(bilder: list[Path], toene: list[Path], dauern: list[float], ziel: Path, cfg: dict) -> Path:
    v = cfg["video"]
    fps, W, H = v["fps"], v["breite"], v["hoehe"]
    tmp = ziel.parent / "teile"
    tmp.mkdir(parents=True, exist_ok=True)
    teile = []
    for i, (b, t, d) in enumerate(zip(bilder, toene, dauern)):
        n = max(1, round(d * fps))
        out = tmp / f"teil_{i:02d}.mp4"
        # langsamer Zoom (2 %) gegen "Standbild"-Wirkung
        zoom = f"zoompan=z='1+0.02*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={fps}"
        _ff("-loop", "1", "-i", str(b), "-i", str(t),
            "-filter_complex", f"[0:v]scale={W*2}:{H*2},{zoom},format=yuv420p[v];[1:a]apad,aresample=44100[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
            "-ac", "2", str(out))
        teile.append(out)
    liste = tmp / "liste.txt"
    liste.write_text("".join(f"file '{p.name}'\n" for p in teile))
    roh = tmp / "roh.mp4"
    _ff("-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy", str(roh))

    musik = v.get("musik")
    if musik and Path(musik).exists():
        _ff("-i", str(roh), "-stream_loop", "-1", "-i", musik,
            "-filter_complex", f"[1:a]volume={v['musik_db']}dB[m];[0:a][m]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(ziel))
    else:
        _ff("-i", str(roh), "-c", "copy", "-movflags", "+faststart", str(ziel))
    return ziel
