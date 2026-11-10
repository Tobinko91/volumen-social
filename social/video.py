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
    """Untertitel als Textfeld (Wunsch Tobias 05.11.2026, ersetzt die 3-Wort-Stuecke): der ganze Satz der Szene in
    einem Kasten, die Woerter erscheinen nacheinander, so wie Brian sie spricht, und bleiben stehen. Das gerade
    gesprochene Wort leuchtet in Flieder, Zahlen in Leuchtminze (negative in Rot).
    y = Oberkante des Kastens. Zeiten aus den ElevenLabs-Zeitmarken, sonst geschaetzt. -> [(Bild, Start, Ende)]."""
    from PIL import Image, ImageDraw
    from . import design
    W, H = cfg["video"]["breite"], cfg["video"]["hoehe"]
    woerter = woerter or woerter_schaetzen(text, dauer)
    # Klammern zerfallen und sehen unfertig aus (Tobias 04.11.2026) -> weglassen
    woerter = [dict(w, w=w["w"].replace("(", "").replace(")", "")) for w in woerter]
    woerter = [w for w in woerter if w["w"]]
    if not woerter:
        return []
    oben = int(y or cfg["video"].get("untertitel_y", 1460))
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    rand, breite_max = 44, W - 120 - 88
    for groesse in (50, 46, 42, 38, 34):
        f = design.font("Bold", groesse)
        leer = probe.textlength(" ", font=f)
        zeilen, akt, x = [], [], 0.0
        for i, w in enumerate(woerter):
            bw = probe.textlength(w["w"], font=f)
            if akt and x + bw > breite_max:
                zeilen.append(akt)
                akt, x = [], 0.0
            akt.append((i, x, bw))
            x += bw + leer
        zeilen.append(akt)
        hoch = int(groesse * 1.38)
        if oben + len(zeilen) * hoch + 2 * rand <= H - 110:
            break
    kasten = [60, oben, W - 60, oben + len(zeilen) * hoch + 2 * rand - 14]
    lage = {i: (60 + rand + x, oben + rand + z * hoch, bw) for z, zl in enumerate(zeilen) for i, x, bw in zl}
    out = []
    for k, aktiv in enumerate(woerter):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(kasten, radius=28, fill=design.rgb("#140F2E", 225))
        for i in range(k + 1):
            wx, wy, bw = lage[i]
            wort = woerter[i]["w"]
            if i == k:
                d.rounded_rectangle([wx - 8, wy - 4, wx + bw + 8, wy + groesse * 1.18], radius=12,
                                    fill=design.rgb("#B69CFF"))
                farbe = "#140F2E"
            elif _zahl(wort):
                farbe = "#FF7A8F" if wort.lstrip("($").startswith(("-", "−")) else "#3CF2C0"
            else:
                farbe = "#F2F0FF"
            d.text((wx, wy), wort, font=f, fill=design.rgb(farbe))
        p = ordner / f"ut_{nr:02d}_{k:03d}.png"
        img.save(p)
        a = 0.0 if k == 0 else aktiv["a"]
        e = woerter[k + 1]["a"] if k + 1 < len(woerter) else dauer
        out.append((p, a, max(e, a + 0.05)))
    return out


def ut_formate(cfg: dict, zeilen: list[str], beitrag: dict | None = None) -> dict:
    """Feste Formate (Markt, Wal, Lernen, Willkommen): animierte Untertitel an der Stelle des frueheren
    Satz-Kastens (bilder.py zeichnet ihn dann nicht mehr)."""
    v = cfg["video"]
    out = {"texte": zeilen, "untertitel_y": v.get("untertitel_y_formate", 1230)} if v.get("untertitel_animiert") else {}
    haken = ((beitrag or {}).get("szenen") or [{}])[0].get("haken")
    return dict(out, haken=haken) if haken else out


def bauen(bilder: list[Path], toene: list[Path], dauern: list[float], ziel: Path, cfg: dict,
          texte: list[str] | None = None, untertitel_y: int | None = None, haken: str | None = None) -> Path:
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
        if i == 0:   # 08.11.2026 (Haltequote 8 %): Sekunde 1 bewegt sich, schneller Zoom von 112 % auf 100 %
            k = max(1, round(0.7 * fps))
            zoom = (f"zoompan=z='if(lt(on,{k}),1.12-0.12*on/{k},1+0.02*(on-{k})/{n})':x='iw/2-(iw/zoom/2)':"
                    f"y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={fps}")
        fokus_p = Path(b).with_suffix(".fokus.json") if not isinstance(b, (list, tuple)) else None
        if fokus_p and fokus_p.exists():   # 10.11.2026 (S24/S28): langsamer Zoom auf den hellsten Cluster
            fx, fy = json.loads(fokus_p.read_text())["fokus"]
            fx, fy = fx * 2, fy * 2   # Bild wird vor dem Zoom auf doppelte Groesse skaliert
            zoom = (f"zoompan=z='1+0.30*on/{n}':x='max(0,min(iw-iw/zoom,{fx}-iw/zoom/2))':"
                    f"y='max(0,min(ih-ih/zoom,{fy}-ih/zoom/2))':d={n}:s={W}x{H}:fps={fps}")
        ut = []
        if texte and i < len(texte) and texte[i]:
            marken = Path(t).with_suffix(".json")
            woerter = json.loads(marken.read_text()) if marken.exists() else None
            ut = untertitel(texte[i], d, tmp, i, cfg, woerter, untertitel_y)
        eingaenge, kette, letzt = [], f"[0:v]scale={W*2}:{H*2},{zoom}[z0]", "z0"
        bild_ein = ["-loop", "1", "-i", str(b)]
        if isinstance(b, (list, tuple)):   # 09.11.2026 (S27): Bildfolge [(png, Sekunden), ...] statt Standbild
            folge = tmp / f"folge_{i:02d}.txt"
            folge.write_text("".join(f"file '{Path(png).resolve()}'\nduration {sek:.3f}\n" for png, sek in b)
                             + f"file '{Path(b[-1][0]).resolve()}'\n")
            bild_ein = ["-f", "concat", "-safe", "0", "-i", str(folge)]
            kette = f"[0:v]fps={fps},scale={W}:{H},tpad=stop_mode=clone:stop_duration=120[z0]"
        for k, (png, a, e) in enumerate(ut):
            eingaenge += ["-i", str(png)]
            kette += f";[{letzt}][{k + 2}:v]overlay=0:0:enable='between(t,{a:.2f},{e:.2f})'[z{k + 1}]"
            letzt = f"z{k + 1}"
        _ff(*bild_ein, "-i", str(t), *eingaenge,
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
            {"dauer": round(sum(dauern), 2), "untertitel": "wort" if texte else "ohne",
             **({"haken": haken} if haken else {})}))
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
