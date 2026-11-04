"""Setzt Bilder und Ton mit ffmpeg zu einem 9:16-Video zusammen (kein Schnitt per Hand)."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def stuecke(text: str, n: int = 3) -> list[str]:
    """Sprechtext in kurze Untertitel-Stuecke (hoechstens n Woerter, Satzzeichen beenden ein Stueck)."""
    out, akt = [], []
    for w in text.split():
        akt.append(w)
        if len(akt) >= n or w[-1] in ".,!?:;":
            out.append(" ".join(akt))
            akt = []
    if akt:
        out.append(" ".join(akt))
    return out


def untertitel(text: str, dauer: float, ordner: Path, nr: int, cfg: dict) -> list[tuple[Path, float, float]]:
    """Je Stueck ein durchsichtiges Bild (Leuchtminze auf dunkler Pille, unten mittig) mit Start/Ende in Sekunden.
    Zeit je Stueck nach Zeichenzahl verteilt (die Stimme spricht etwa gleichmaessig)."""
    from PIL import Image, ImageDraw
    from . import design
    W, H = cfg["video"]["breite"], cfg["video"]["hoehe"]
    teile = stuecke(text)
    sprech = max(0.5, dauer - 0.35)
    gesamt = sum(len(t) + 2 for t in teile) or 1
    out, t0 = [], 0.0
    for k, t in enumerate(teile):
        t1 = t0 + sprech * (len(t) + 2) / gesamt
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        groesse = 64
        while groesse > 36:
            f = design.font("Bold", groesse)
            if d.textlength(t, font=f) <= W - 160:
                break
            groesse -= 4
        b = d.textlength(t, font=f)
        mitte = int(cfg["video"].get("untertitel_y", 1745))
        d.rounded_rectangle([(W - b) / 2 - 28, mitte - groesse * 0.75, (W + b) / 2 + 28, mitte + groesse * 0.75],
                            radius=24, fill=design.rgb("#140F2E", 225))
        d.text(((W - b) / 2, mitte - groesse * 0.62), t, font=f, fill=design.rgb("#3CF2C0"))
        p = ordner / f"ut_{nr:02d}_{k:02d}.png"
        img.save(p)
        out.append((p, t0, t1 if k < len(teile) - 1 else dauer))
        t0 = t1
    return out


def bauen(bilder: list[Path], toene: list[Path], dauern: list[float], ziel: Path, cfg: dict,
          texte: list[str] | None = None) -> Path:
    """texte: Sprechtext je Szene -> eingeblendete Untertitel (viele schauen ohne Ton)."""
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
        ut = untertitel(texte[i], d, tmp, i, cfg) if texte and i < len(texte) and texte[i] else []
        eingaenge, kette, letzt = [], f"[0:v]scale={W*2}:{H*2},{zoom}[z0]", "z0"
        for k, (png, a, e) in enumerate(ut):
            eingaenge += ["-i", str(png)]
            kette += f";[{letzt}][{k + 2}:v]overlay=0:0:enable='between(t,{a:.2f},{e:.2f})'[z{k + 1}]"
            letzt = f"z{k + 1}"
        _ff("-loop", "1", "-i", str(b), "-i", str(t), *eingaenge,
            "-filter_complex", f"{kette};[{letzt}]format=yuv420p[v];[1:a]apad,aresample=44100[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
            "-ac", "2", str(out))
        teile.append(out)
    liste = tmp / "liste.txt"
    liste.write_text("".join(f"file '{p.name}'\n" for p in teile))
    roh = tmp / "roh.mp4"
    _ff("-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy", str(roh))

    from . import musik as _musik
    musik = _musik.pfad(cfg, ziel.parent.parent)
    if musik:
        mit_stimme = any(Path(t).suffix == ".mp3" for t in toene)   # echte Stimme = mp3, Stille = m4a
        db = v["musik_db"] if mit_stimme else v.get("musik_db_ohne_stimme", 0)
        _ff("-i", str(roh), "-stream_loop", "-1", "-i", str(musik),
            "-filter_complex", f"[1:a]volume={db}dB[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(ziel))
    else:
        _ff("-i", str(roh), "-c", "copy", "-movflags", "+faststart", str(ziel))
    return ziel
