"""Reels aus dem Redaktions-Chat (Warteschlange) auf dem Server fertig bauen: Stimme (ElevenLabs) + Musik.

Anlass 04.11.2026: Der Chat hat keinen Stimmen-Schluessel (der liegt nur in secrets.yaml auf dem Server).
Darum legt der Chat nur Szenenbilder und Sprechtext ab, der Server spricht und schneidet.

reel.json im Ordner:
  {"thema": "midterms-3",
   "szenen": [{"bild": "szene_0.png", "text": "Gesprochener Satz",
               "chart": {"base": "BTC", "intervall": "15m", "anzahl": 48, "box": [60, 700, 1020, 1500],
                         "titel": "BTC · 15m"}}, ...]}
- "bild" ist Pflicht (fertiges 1080x1920-Bild). Mit "chart" zeichnet der Server den echten Kursverlauf in
  die Box (Kurse holt nur der Server, der Chat erreicht die Boersen nicht). Klappt das nicht, bleibt das Bild.
- Wunsch Tobias 05.11.2026: Ein Chart ohne Zahl sagt nichts. Mit "ab_ts" (Unix-Sekunden, z. B. Zeitpunkt einer
  Entscheidung) rechnet der Server die Veraenderung seitdem aus echten Kerzen und setzt sie in den Sprechtext
  ein: "text": "Bitcoin is {chg} since the Democrats won the Senate." -> "+2.4%". Dazu {von}/{bis} (Preise).
  Ohne Kurse gilt "text_ohne" (Pflicht, wenn der Text Platzhalter hat).
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


def chart_szene(ordner: Path, s: dict, thema: str, kerzen_holen) -> tuple[Path, dict]:
    """-> (Bild mit echtem Chart, Werte {chg, von, bis} seit ab_ts bzw. seit der ersten Kerze)."""
    from . import design, grafik
    c = s["chart"]
    k = kerzen_holen(c.get("base", "BTC"), c.get("intervall", "15m"), int(c.get("anzahl", 48)))
    if c.get("ab_ts"):
        k = [x for x in k if x["t"] >= int(c["ab_ts"]) * 1000 - 3600_000]   # ab der Stunde vor dem Ereignis
    if len(k) < 12:
        raise ValueError(f"zu wenige Kerzen ({len(k)})")
    von, bis = k[0]["o"], k[-1]["c"]
    chg = (bis / von - 1) * 100
    img = Image.open(ordner / s["bild"]).convert("RGBA")
    th = design.thema_waehlen("markt", thema)
    titel = c.get("titel", "")
    if c.get("ab_ts"):
        titel = f"{titel} · {chg:+.1f}% since {c.get('ab_text', 'then')}".strip(" ·")
    grafik.echt_chart(img, th, tuple(c["box"]), k, "linie", {}, 3, c.get("lang", "en"), titel)
    ziel = ordner / f"chart_{Path(s['bild']).stem}.png"
    img.convert("RGB").save(ziel)
    preis = lambda x: f"${x:,.0f}" if x >= 100 else f"${x:,.2f}"
    return ziel, {"chg": f"{chg:+.1f}%", "von": preis(von), "bis": preis(bis)}


def bauen(ordner: Path, cfg: dict, geheim: dict, kerzen_holen=None, sprechen=None, schneiden=None) -> str:
    """Baut ordner/video.mp4 aus reel.json. Gibt die Tonquelle zurueck ('elevenlabs', 'stille (...)', ...)."""
    from . import kurse, stimme, video
    kerzen_holen = kerzen_holen or (lambda b, i, n: kurse.kerzen(b, i, n))
    sprechen = sprechen or stimme.sprechen
    schneiden = schneiden or video.bauen
    spec = json.loads((ordner / "reel.json").read_text(encoding="utf-8"))
    bilder, hinweise, zeilen = [], [], []
    for s in spec["szenen"]:
        p, text = ordner / s["bild"], s["text"]
        if s.get("chart"):
            try:
                p, werte = chart_szene(ordner, s, spec.get("thema", ordner.name), kerzen_holen)
                text = text.format(**werte) if "{" in text else text
                hinweise.append(f"Chart {s['chart'].get('base', 'BTC')}: {werte['chg']}")
            except Exception as e:   # ohne Kurse trotzdem ein Video, Hinweis an Tobias
                hinweise.append(f"Chart fehlt ({str(e)[:80]})")
                text = s.get("text_ohne") or text.replace("{chg}", "").replace("{von}", "").replace("{bis}", "")
        bilder.append(p)
        zeilen.append(text)
    toene, dauern, quelle = sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    schneiden(bilder, toene, dauern, ordner / "video.mp4", cfg, texte=zeilen)
    return "; ".join([quelle, *hinweise])


# ---------------------------------------------------------------- Reel aus einem Bild-Vorschlag (Knopf „🎬 Als Reel“)

def sprechtext(x_text: str) -> list[str]:
    """X-Text als Sprechtext: ohne Emojis, Links, Hashtags, Cashtag-$; je Satz/Zeile eine Szene-Zeile."""
    import re
    t = re.sub(r"https?://\S+", "", x_text)
    t = re.sub(r"#\w+", "", t)
    t = re.sub(r"\$([A-Za-z]{2,10})\b", r"\1", t)                      # $ZK -> ZK, $75,740 bleibt
    t = "".join(c for c in t if c.isascii() or c.isalpha() or c in "€–—’“”…·")
    t = t.replace("·", ",")
    zeilen = [re.sub(r"\s+,", ",", re.sub(r"\s+", " ", z)).strip(" -•,") for z in t.splitlines()]
    return [z if z[-1:] in ".!?:" else z + "." for z in zeilen if len(z) > 1]


def bild_szene(post: Path, ziel: Path, thema: str, cfg: dict) -> Path:
    """Hochformat 1080x1920: Marke oben, Beitragsbild gross in der Mitte, Folgen-Hinweis unten."""
    from PIL import ImageDraw
    from . import design
    th = design.thema_waehlen("markt", thema)
    W, H = cfg["video"]["breite"], cfg["video"]["hoehe"]
    img = design.hintergrund(th, W, H, saat=31)
    design.marke(img, th, 80, 90, 72)
    b = Image.open(post).convert("RGBA")
    breite = W - 60
    b = b.resize((breite, int(b.height * breite / b.width)))
    y = max(230, (H - b.height) // 2)
    img.alpha_composite(b, ((W - breite) // 2, y))
    d = ImageDraw.Draw(img)
    f = design.font("Bold", 40)
    txt = f"Follow {design.FUSS_MARKE}"
    d.text(((W - d.textlength(txt, font=f)) / 2, min(H - 140, y + b.height + 50)), txt, font=f, fill=th.akzent)
    img.convert("RGB").save(ziel)
    return ziel


def aus_bild(ordner: Path, cfg: dict, geheim: dict, sprechen=None, schneiden=None) -> tuple[Path, str]:
    """Neuer Vorschlags-Ordner <name>_video mit video.mp4: Beitragsbild als Hochformat, Brian liest den X-Text."""
    import shutil
    from . import stimme, video
    sprechen = sprechen or stimme.sprechen
    schneiden = schneiden or video.bauen
    neu = ordner.parent / f"{ordner.name}_video"
    if (neu / "video.mp4").exists():
        return neu, "schon gebaut"
    neu.mkdir(exist_ok=True)
    for f in ("post.png", "post_x.txt", "post_telegram.txt"):
        shutil.copy(ordner / f, neu / f)
    zeilen = sprechtext((ordner / "post_x.txt").read_text(encoding="utf-8"))
    szene = bild_szene(ordner / "post.png", neu / "szene.png", ordner.name, cfg)
    toene, dauern, quelle = sprechen(zeilen, neu / "ton", cfg, stimme.schluessel(cfg, geheim))
    schneiden([szene] * len(zeilen), toene, dauern, neu / "video.mp4", cfg, texte=zeilen)
    return neu, quelle
