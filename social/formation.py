"""S27 „Formation des Tages: BUY or SELL?“ (Wunsch Tobias 09.11.2026, Vorbild TikTok @michael.trades1).

Echter Chart eines echten Coins mit einer Formation, Countdown 5…1, dann die echte Aufloesung und – unser Unterschied –
die echte Trefferquote der Formation neben dem Zufall. Daten: /opt/volumen-bot/web/muster_des_tages.json (Bot 9.36),
Ablauf nach der Vorlage des Trading-Chats (Projekt-Dokument formation-des-tages-vorlage), umgesetzt mit Pillow +
ffmpeg im Design „Nachtleuchten“, mit Stimme, Wort-Untertiteln und Ticken im Countdown.

Regeln: keine Kauf-/Verkaufsaufforderung (nur Rueckblick „the textbook was right/wrong“), Szene „But here's the catch“
nie weglassen, wenn `statistik` da ist, nur eigene Charts, „Not financial advice.“
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1080, 1920
BOX = (60, 470, 1020, 1150)       # Chart
UNTEN = 1200                      # Countdown / grosse Zahl / Karte


def laden(web_dir: str | Path) -> dict | None:
    p = Path(web_dir) / "muster_des_tages.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not d.get("kerzen_vorher") or len(d.get("kerzen_nachher") or []) < 6:
        return None
    return d


def _pz(x: float) -> str:
    return f"{x:+.1f}%".replace("-", "−")


EINSTIEG = ["Watch {coin} on the 4 hour chart.", "Here is {coin} on the 4 hour chart.",
            "Today's chart: {coin}, 4 hours per candle.", "Look at {coin} on the 4 hour chart.",
            "New day, new pattern. Watch {coin}."]   # 11.11.2026: weniger Schablone, Satz wechselt je Tag


def einstieg(d: dict) -> str:
    tag = str(d.get("datum") or "")
    i = sum(map(ord, tag)) % len(EINSTIEG) if tag else 0
    return EINSTIEG[i].format(coin=d["coin"])


def saat(d: dict) -> int:
    """Hintergrund wechselt je Tag (gleiches Datum = gleiches Bild)."""
    return 7 + sum(map(ord, str(d.get("datum") or ""))) % 40


def texte(d: dict, modus: str = "sofort") -> dict:
    """Sprechtext je Szene (englisch, ohne Klammern) und die Texte fuer X/Telegram.
    modus "morgen" (Entscheidung Tobias 10.11.2026): Video endet nach dem Countdown, die Aufloesung kommt im
    naechsten Video (vorspann()), damit die Kommentare echte Tipps sind."""
    if modus == "morgen":
        coin, name = d["coin"], d["name_en"]
        zeilen = [einstieg(d), f"A {name}. Buy or sell?", "Comment your answer now.",
                  "The answer comes tomorrow. Follow so you don't miss it."]
        x = (f"BUY or SELL? 📊\n{name} on ${coin}, 4h chart.\nComment your answer. The real result comes "
             "tomorrow.\nNot financial advice.")
        return {"zeilen": zeilen, "titel_erg": "", "x": x[:280]}
    e, s = d["ergebnis"], d.get("statistik")
    runter = d["lehrbuch"] == "down"
    stimmt = e.get("lehrbuch_stimmt")
    coin, name = d["coin"], d["name_en"]
    zeilen = [
        einstieg(d),   # 10.11.2026 Tobias: erst die Bewegung, dann die Frage
        f"A {name}. Buy or sell?",
        "Comment your answer now.",
        "Here is what happened next.",
        f"{coin} moved {_pz(e['r6'])} in 24 hours. " + ("The textbook was right." if stimmt
                                                       else "The textbook was wrong."),
    ]
    if s:
        richtung = "fell" if runter else "rose"
        vor = s.get("vorsprung_pp", s["treffer_pct"] - s["zufall_pct"])
        urteil = ("A small edge, not a guarantee." if vor >= 5 else "Worse than random." if vor <= -5
                  else "No real edge.")
        zeilen.append(f"But here is the catch. After a {name}, price {richtung} {s['treffer_pct']:.0f}% of the time. "
                      f"Without any pattern: {s['zufall_pct']:.0f}%. {urteil}")
    zeilen.append("Tomorrow, a new pattern. Follow and guess along.")
    titel_erg = (("SELL was right" if runter else "BUY was right") if stimmt else "The textbook was wrong")
    x = (f"BUY or SELL? 📊\n{name} on ${coin}, 4h chart.\nWhat happened next: {_pz(e['r6'])} in 24h. "
         + ("The textbook was right." if stimmt else "The textbook was wrong.")
         + (f"\n{name}: {s['n']:,} cases, price {'fell' if runter else 'rose'} after it {s['treffer_pct']:.0f}%, "
            f"without any pattern {s['zufall_pct']:.0f}%." if s else "")
         + "\nNot financial advice.")
    return {"zeilen": zeilen, "titel_erg": titel_erg, "x": x[:280]}


# ---------------------------------------------------------------- Zeichnen

def _skala(kerzen: list, box):
    lo = min(k[3] for k in kerzen)
    hi = max(k[2] for k in kerzen)
    pad = (hi - lo) * 0.08 or hi * 0.01
    lo, hi = lo - pad, hi + pad
    x0, y0, x1, y1 = box
    return lambda p: y1 - (p - lo) / (hi - lo) * (y1 - y0)


def _bild(d: dict, n_nach: int, titel: str, unter: str = "", pfeile: bool = False, zahl: int | None = None,
         n_vor: int | None = None,
         gross: tuple | None = None, karte_zeilen: list | None = None, markieren: bool = True, saat: int = 7):
    from . import design
    from .design import font, rgb
    th = design.THEMEN["nacht"]
    alle_vor = [list(k) for k in d["kerzen_vorher"][-26:]]
    vor = alle_vor[:n_vor] if n_vor else alle_vor   # Aufbau Kerze fuer Kerze
    nach = [list(k) for k in d["kerzen_nachher"][:6]]
    img = design.hintergrund(th, W, H, saat=saat)
    design.marke(img, th, 80, 90, 72)
    dr = ImageDraw.Draw(img)
    f = font("Bold", 92)
    dr.text(((W - dr.textlength(titel, font=f)) / 2, 230), titel, font=f, fill=th.text)
    if unter:
        fu = font("SemiBold", 40)
        dr.text(((W - dr.textlength(unter, font=fu)) / 2, 350), unter, font=fu, fill=th.neben)
    design.karte(img, th, BOX)
    dr = ImageDraw.Draw(img)
    x0, y0, x1, y1 = BOX
    innen = (x0 + 30, y0 + 70, x1 - 30, y1 - 30)
    y = _skala(vor + nach[:n_nach], innen)   # nur sichtbare Kerzen: die Skala verraet nichts ueber die Zukunft
    slots = len(alle_vor) + 6 + 1
    breite = (innen[2] - innen[0]) / slots
    dr.text((x0 + 30, y0 + 20), f"${d['coin']} · 4h · real chart", font=font("SemiBold", 28), fill=th.neben)
    for i, k in enumerate(vor + nach[:n_nach]):
        _, o, h, l, c = k[:5]
        farbe = rgb(th.plus if c >= o else th.minus)
        xm = innen[0] + (i + 0.5) * breite
        dr.line([(xm, y(h)), (xm, y(l))], fill=farbe, width=3)
        oben, unten = min(y(o), y(c)), max(y(o), y(c))
        dr.rectangle([xm - breite * 0.33, oben, xm + breite * 0.33, max(unten, oben + 2)], fill=farbe)
    if markieren:   # Formation = die letzten 1-3 Kerzen von kerzen_vorher
        mk = d.get("muster_kerzen") or 1   # Bot 9.36 liefert die Anzahl (1-3), aeltere Beispiele eine Liste
        m = max(1, min(3, mk if isinstance(mk, int) else len(mk)))
        a = innen[0] + (len(vor) - m) * breite
        e = innen[0] + len(vor) * breite
        hs = [y(k[2]) for k in vor[-m:]]
        ls = [y(k[3]) for k in vor[-m:]]
        dr.rounded_rectangle([a - 6, min(hs) - 16, e + 6, max(ls) + 16], radius=12, outline=rgb(th.akzent2), width=5)
    if pfeile:
        xs = innen[0] + (len(vor) + 0.6) * breite
        ys = y(vor[-1][4])
        for ziel_y, farbe in ((innen[1] + 30, th.plus), (innen[3] - 30, th.minus)):
            xe = xs + breite * 4.5
            dr.line([(xs, ys), (xe, ziel_y)], fill=rgb(farbe), width=10)
            import math
            w_ = math.atan2(ziel_y - ys, xe - xs)
            spitze = [(xe, ziel_y), (xe - 40 * math.cos(w_ - 0.45), ziel_y - 40 * math.sin(w_ - 0.45)),
                      (xe - 40 * math.cos(w_ + 0.45), ziel_y - 40 * math.sin(w_ + 0.45))]
            dr.polygon(spitze, fill=rgb(farbe))
    if zahl is not None:
        cx, cy, r = W // 2, UNTEN + 120, 105
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgb(design.FLAECHE), outline=rgb(th.akzent2), width=8)
        fz = font("Bold", 130)
        dr.text((cx - dr.textlength(str(zahl), font=fz) / 2, cy - 82), str(zahl), font=fz, fill=th.text)
        fb = font("Bold", 88)
        dr.text((cx - r - 70 - dr.textlength("BUY", font=fb), cy - 52), "BUY", font=fb, fill=th.plus)
        dr.text((cx + r + 70, cy - 52), "SELL", font=fb, fill=th.minus)
    if gross:
        text, farbe = gross
        fg = font("Bold", 120)
        dr.text(((W - dr.textlength(text, font=fg)) / 2, UNTEN + 40), text, font=fg, fill=farbe)
    if karte_zeilen:
        design.karte(img, th, (60, UNTEN - 10, W - 60, UNTEN + 70 + 66 * len(karte_zeilen)))
        dr = ImageDraw.Draw(img)
        yy = UNTEN + 25
        for j, (t_, farbe) in enumerate(karte_zeilen):
            fk = font("Bold" if j == 0 else "SemiBold", 46 if j == 0 else 40)
            dr.text((100, yy), t_, font=fk, fill=farbe)
            yy += 66
    design.fuss(img, th, "Not financial advice.")
    return img


bild = _bild


def szenen(d: dict, ordner: Path, modus: str = "sofort") -> tuple[list, dict]:
    """-> (Bildfolgen je Szene [(png, Sekunden), ...], Texte). Mindestdauern stehen in den Folgen."""
    from . import design
    th = design.THEMEN["nacht"]
    ordner.mkdir(parents=True, exist_ok=True)
    tx = texte(d, modus)
    sa = saat(d)
    bild = lambda *a, **k: _bild(*a, **{"saat": sa, **k})
    e, s = d["ergebnis"], d.get("statistik")
    runter = d["lehrbuch"] == "down"

    def speichern(img, name):
        p = ordner / f"{name}.png"
        img.convert("RGB").save(p)
        return p

    n = len(d["kerzen_vorher"][-26:])
    schritte = list(range(3, n, 1))   # Kerze fuer Kerze, ohne Markierung und ohne Frage
    folgen = [[(speichern(bild(d, 0, "Watch the chart", f"${d['coin']} · 4h", markieren=False, n_vor=k), f"auf_{k:02d}"),
                0.13) for k in schritte]
              + [(speichern(bild(d, 0, "Watch the chart", f"${d['coin']} · 4h", markieren=False), "auf_fertig"), 0.5)]]
    folgen.append([(speichern(bild(d, 0, "BUY or SELL?", f"Pattern: {d['name_en']}"), "muster"), 0.9),
                   (speichern(bild(d, 0, "BUY or SELL?", f"Pattern: {d['name_en']}", pfeile=True), "frage"), 1.6)])
    folgen.append([(speichern(bild(d, 0, "BUY or SELL?", "Comment your answer!", pfeile=True, zahl=n), f"count_{n}"),
                    1.0) for n in (5, 4, 3, 2, 1)])
    if modus == "morgen":
        folgen.append([(speichern(bild(d, 0, "Answer tomorrow", "Comment BUY or SELL", pfeile=True,
                                       gross=("Follow", th.akzent)), "morgen"), 2.5)])
        return folgen, tx
    folgen.append([(speichern(bild(d, n, "What happened next?", "the next 24 hours"), f"nach_{n}"), 0.45)
                   for n in range(1, 7)])
    farbe = th.minus if e["r6"] < 0 else th.plus
    folgen.append([(speichern(bild(d, 6, tx["titel_erg"], f"Textbook: {d['lehrbuch_en']}",
                                   gross=(f"{_pz(e['r6'])} in 24h", farbe)), "ergebnis"), 3.0)])
    if s:
        vor = s.get("vorsprung_pp", s["treffer_pct"] - s["zufall_pct"])
        fazit = ("→ a small edge, no guarantee" if vor >= 5 else "→ worse than random" if vor <= -5
                 else "→ no real edge")
        folgen.append([(speichern(bild(d, 6, "But here's the catch", "", markieren=False, karte_zeilen=[
            (f"{d['name_en']}: {s['n']:,} cases", th.text),
            (f"Price {'fell' if runter else 'rose'} after it: {s['treffer_pct']:.0f}%", th.text),
            (f"Without any pattern: {s['zufall_pct']:.0f}%", th.akzent2),
            (fazit, th.akzent)]), "haken"), 4.5)])
    folgen.append([(speichern(bild(d, 6, "Tomorrow: new pattern", "Follow & guess along", markieren=False,
                                   gross=("Follow", th.akzent)), "folgen"), 2.5)])
    return folgen, tx


def vorspann(g: dict, ordner: Path, community: dict | None = None) -> tuple[list, list]:
    """Aufloesung von gestern als Vorspann (modus "morgen"): die 6 Kerzen danach, Ergebnis + Community, Haken.
    community = {"n", "mehrheit": "buy"|"sell", "pct"} oder None (unter der Mindestzahl)."""
    from . import design
    th = design.THEMEN["nacht"]
    ordner.mkdir(parents=True, exist_ok=True)
    e, s = g["ergebnis"], g.get("statistik")
    runter = g["lehrbuch"] == "down"
    sa = saat(g)

    def sp(img, n):
        p = ordner / f"gestern_{n}.png"
        img.convert("RGB").save(p)
        return p

    stieg = e["r6"] > 0
    zeilen = [f"Yesterday's {g['name_en']} on {g['coin']}. Here is what happened."]
    folgen = [[(sp(_bild(g, 0, "Yesterday's answer", f"{g['name_en']} · ${g['coin']}", saat=sa), "start"), 1.0)]
              + [(sp(_bild(g, n, "Yesterday's answer", "the next 24 hours", saat=sa), f"nach_{n}"), 0.4)
                 for n in range(1, 7)]]
    satz = f"{g['coin']} moved {_pz(e['r6'])} in 24 hours."
    karte = [(f"{_pz(e['r6'])} in 24h · {'BUY' if stieg else 'SELL'} was right" if e["r6"] else
              "Flat after 24h", th.plus if stieg else th.minus)]
    if community and e["r6"]:
        recht = (community["mehrheit"] == "buy") == stieg
        satz += (f" {community['pct']:.0f}% of {community['n']} of you said {community['mehrheit'].upper()}. "
                 + ("You were right." if recht else "The chart said otherwise."))
        karte.append((f"{community['pct']:.0f}% of {community['n']} said {community['mehrheit'].upper()}", th.text))
        karte.append(("→ you were right" if recht else "→ the chart said otherwise", th.akzent if recht else th.neben))
    zeilen.append(satz)
    folgen.append([(sp(_bild(g, 6, "Yesterday's answer", f"Textbook: {g['lehrbuch_en']}", saat=sa,
                             karte_zeilen=karte), "ergebnis"), 3.0)])
    if s:   # Regel S27: der Haken bleibt, wenn es die Statistik gibt
        vor = s.get("vorsprung_pp", s["treffer_pct"] - s["zufall_pct"])
        urteil = ("A small edge, not a guarantee." if vor >= 5 else "Worse than random." if vor <= -5
                  else "No real edge.")
        zeilen.append(f"The catch: after a {g['name_en']}, price {'fell' if runter else 'rose'} "
                      f"{s['treffer_pct']:.0f}% of the time. Without any pattern: {s['zufall_pct']:.0f}%. {urteil}")
        folgen.append([(sp(_bild(g, 6, "But here's the catch", "", markieren=False, saat=sa, karte_zeilen=[
            (f"{g['name_en']}: {s['n']:,} cases", th.text),
            (f"Price {'fell' if runter else 'rose'} after it: {s['treffer_pct']:.0f}%", th.text),
            (f"Without any pattern: {s['zufall_pct']:.0f}%", th.akzent2),
            ("→ " + urteil.rstrip(".").lower(), th.akzent)]), "haken"), 4.0)])
    return folgen, zeilen


def ticken(ton: Path, ziel: Path, dauer: float = 5.0) -> Path:
    """Stimme der Countdown-Szene + 5 Ticks (je 1 s). Zeitmarken-Datei bleibt fuer die Untertitel erhalten."""
    import shutil
    import subprocess
    tick = "+".join(f"sin(2*PI*1600*t)*exp(-60*(t-{i}))*gte(t,{i})" for i in range(5))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ton), "-f", "lavfi", "-t", f"{dauer}",
                    "-i", f"aevalsrc='0.5*({tick})':s=44100",
                    "-filter_complex", "[0:a]apad,aresample=44100[s];[s][1:a]amix=inputs=2:duration=longest:normalize=0",
                    "-t", f"{dauer}", "-c:a", "libmp3lame", "-b:a", "160k", str(ziel)], check=True)
    if ton.with_suffix(".json").exists():
        shutil.copy(ton.with_suffix(".json"), ziel.with_suffix(".json"))
    return ziel


def video(d: dict, ordner: Path, cfg: dict, geheim: dict, sprechen=None, schneiden=None, modus: str = "sofort",
          gestern: dict | None = None, community: dict | None = None) -> tuple[Path, str, dict]:
    """Baut ordner/video.mp4. -> (Video, Tonquelle, Texte). Mit gestern (modus "morgen"): Vorspann davor."""
    from . import stimme
    from . import video as _video
    sprechen = sprechen or stimme.sprechen
    schneiden = schneiden or _video.bauen
    folgen, tx = szenen(d, ordner / "bilder", modus)
    v = 0
    if gestern:
        vf, vz = vorspann(gestern, ordner / "bilder", community)
        v = len(vf)
        tx = dict(tx, zeilen=vz + ["Now today's pattern. " + tx["zeilen"][0]] + tx["zeilen"][1:])
        folgen = vf + folgen
    toene, dauern, quelle = sprechen(tx["zeilen"], ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    dauern = [max(du, sum(sek for _, sek in f) + 0.2) for du, f in zip(dauern, folgen)]
    try:   # Countdown: Ticken unter die Stimme
        toene[v + 2] = ticken(Path(toene[v + 2]), Path(toene[v + 2]).with_name("countdown_tick.mp3"), dauern[v + 2])
    except Exception as e:
        print("Ticken nicht gemischt:", e)
    schneiden(folgen, toene, dauern, ordner / "video.mp4", cfg, texte=tx["zeilen"],
              untertitel_y=1590)   # unter Countdown, Ergebnis und Karte
    return ordner / "video.mp4", quelle, tx
