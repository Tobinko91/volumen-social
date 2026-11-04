"""Setzt Bilder und Ton mit ffmpeg zu einem 9:16-Video zusammen (kein Schnitt per Hand)."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def woerter_schaetzen(text: str, dauer: float) -> list[dict]:
    """Ohne Zeitmarken der Stimme: Sprechzeit nach Zeichenzahl auf die Woerter verteilen."""
    worte = text.split()
    sprech = max(0.5, dauer - 0.35)
    gesamt = sum(len(w) + 1 for w in worte) or 1
    out, t = [], 0.0
    for w in worte:
        e = t + sprech * (len(w) + 1) / gesamt
        out.append({"w": w, "a": round(t, 3), "e": round(e, 3)})
        t = e
    return out


def gruppen(woerter: list[dict], n: int = 3) -> list[list[dict]]:
    """Woerter in kurze Untertitel-Stuecke (hoechstens n Woerter, Satzzeichen beenden ein Stueck)."""
    out, akt = [], []
    for w in woerter:
        akt.append(w)
        if len(akt) >= n or w["w"][-1] in ".,!?:;":
            out.append(akt)
            akt = []
    if akt:
        out.append(akt)
    return out


def stuecke(text: str, n: int = 3) -> list[str]:
    return [" ".join(w["w"] for w in g) for g in gruppen([{"w": w} for w in text.split()], n)]


def _zahl(w: str) -> bool:
    return any(c.isdigit() for c in w)


def untertitel(text: str, dauer: float, ordner: Path, nr: int, cfg: dict, woerter: list[dict] | None = None,
               y: int | None = None) -> list[tuple[Path, float, float]]:
    """Animierte Untertitel (Wunsch Tobias 04.11.2026): je Stueck 3 Woerter, das gerade gesprochene Wort auf einer
    Flieder-Pille, Zahlen in Leuchtminze (negative in Rot). Zeiten aus den Zeitmarken der Stimme (ElevenLabs),
    sonst geschaetzt. -> [(Bild, Start, Ende)] in Sekunden."""
    from PIL import Image, ImageDraw
    from . import design
    W, H = cfg["video"]["breite"], cfg["video"]["hoehe"]
    woerter = woerter or woerter_schaetzen(text, dauer)
    mitte = int(y or cfg["video"].get("untertitel_y", 1745))
    out, alle = [], [w for g in gruppen(woerter) for w in g]
    for gi, g in enumerate(gruppen(woerter)):
        probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        groesse = 66
        while groesse > 38:
            f = design.font("Bold", groesse)
            leer = probe.textlength(" ", font=f) * 1.7   # Platz fuer die Pille des aktiven Worts
            breite = sum(probe.textlength(w["w"], font=f) for w in g) + leer * (len(g) - 1)
            if breite <= W - 200:
                break
            groesse -= 4
        for wi, aktiv in enumerate(g):
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            x0 = (W - breite) / 2
            d.rounded_rectangle([x0 - 30, mitte - groesse * 0.8, x0 + breite + 30, mitte + groesse * 0.8],
                                radius=26, fill=design.rgb("#140F2E", 230))
            x = x0
            for w in g:
                bw = d.textlength(w["w"], font=f)
                if w is aktiv:
                    d.rounded_rectangle([x - 12, mitte - groesse * 0.68, x + bw + 12, mitte + groesse * 0.68],
                                        radius=16, fill=design.rgb("#B69CFF"))
                    farbe = "#140F2E"
                elif _zahl(w["w"]):
                    farbe = "#FF7A8F" if w["w"].lstrip("($").startswith(("-", "−")) else "#3CF2C0"
                else:
                    farbe = "#F2F0FF"
                d.text((x, mitte - groesse * 0.62), w["w"], font=f, fill=design.rgb(farbe))
                x += bw + leer
            p = ordner / f"ut_{nr:02d}_{gi:02d}_{wi:02d}.png"
            img.save(p)
            k = alle.index(aktiv)
            a = 0.0 if k == 0 else aktiv["a"]
            e = alle[k + 1]["a"] if k + 1 < len(alle) else dauer
            out.append((p, a, max(e, a + 0.05)))
    return out


def ut_formate(cfg: dict, zeilen: list[str]) -> dict:
    """Feste Formate (Markt, Wal, Lernen, Willkommen): animierte Untertitel an der Stelle des frueheren
    Satz-Kastens (bilder.py zeichnet ihn dann nicht mehr)."""
    v = cfg["video"]
    return {"texte": zeilen, "untertitel_y": v.get("untertitel_y_formate", 1310)} if v.get("untertitel_animiert") else {}


def bauen(bilder: list[Path], toene: list[Path], dauern: list[float], ziel: Path, cfg: dict,
          texte: list[str] | None = None, untertitel_y: int | None = None) -> Path:
    """texte: Sprechtext je Szene -> animierte Untertitel (viele schauen ohne Ton). Zeitmarken der Stimme liegen
    als <ton>.json neben der Tondatei (ElevenLabs), sonst wird geschaetzt."""
    import json
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
        ut = []
        if texte and i < len(texte) and texte[i]:
            marken = Path(t).with_suffix(".json")
            woerter = json.loads(marken.read_text()) if marken.exists() else None
            ut = untertitel(texte[i], d, tmp, i, cfg, woerter, untertitel_y)
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

    try:   # fuer den Wochenbericht (Haltequote mit/ohne Wort-Untertitel)
        (ziel.parent / "video_info.json").write_text(json.dumps(
            {"dauer": round(sum(dauern), 2), "untertitel": "wort" if texte else "ohne"}))
    except OSError:
        pass
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
