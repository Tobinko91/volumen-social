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
    ema_n = int(c.get("ema") or 0)   # 13.11.2026: z. B. 200-Tage-EMA, aus echten Kerzen gerechnet
    # Fehler 13.11.2026 (Tobias: „EMA 200 bei 75.000 statt ca. 68.000“): Mit nur 200 Kerzen Vorlauf steckte im
    # Startwert (Schnitt der ersten 200 Tage) noch zu viel alter, hoeherer Kurs. Eine EMA braucht ein Vielfaches
    # ihrer Laenge als Vorlauf, damit sie wie bei TradingView aussieht: hier 4 x n (Restgewicht des Starts < 0,1 %).
    vorlauf = 4 * ema_n
    alle = kerzen_holen(c.get("base", "BTC"), c.get("intervall", "15m"), int(c.get("anzahl", 48)) + vorlauf)
    ema_werte = ema(alle, ema_n) if ema_n else []
    alle_rsi = list(alle)
    if ema_n:
        if len(alle) < int(c.get("anzahl", 48)) + 3 * ema_n:
            raise ValueError(f"zu wenige Kerzen fuer eine verlaessliche EMA {ema_n} ({len(alle)})")
        weg = len(alle) - int(c.get("anzahl", 48))
        alle, ema_werte = alle[weg:], ema_werte[weg:]
    k = alle
    if c.get("ab_ts"):   # ab der Stunde vor dem Ereignis (vorlauf_h: mehr Vorgeschichte, z. B. Kurs-Alarm)
        k = [x for x in alle if x["t"] >= (int(c["ab_ts"]) - float(c.get("vorlauf_h", 1)) * 3600) * 1000]
        if len(k) < 12 <= len(alle):   # 08.11.2026 ETH-Alarm: zu kurzer Ausschnitt -> leeres Bild. Dann alle Kerzen
            k = alle[-max(12, len(k)):]
    if len(k) < 12:
        raise ValueError(f"zu wenige Kerzen ({len(k)})")
    von, bis = k[0]["o"], k[-1]["c"]
    if c.get("ab_ts") and c.get("zahl_ab_ereignis"):   # 06.11.: Chart zeigt die Stunde davor, Zahl erst ab Ereignis
        nach = [x for x in k if x["t"] >= int(c["ab_ts"]) * 1000]
        if nach:
            von = nach[0]["o"]
    chg = (bis / von - 1) * 100
    img = Image.open(ordner / s["bild"]).convert("RGBA")
    th = design.thema_waehlen("markt", thema)
    titel = c.get("titel", "")
    if c.get("ab_ts"):
        titel = f"{titel} · {chg:+.1f}% since {c.get('ab_text', 'then')}".strip(" ·")
    preis = lambda x: f"${x:,.0f}" if x >= 100 else f"${x:,.2f}"
    werte = {"chg": f"{chg:+.1f}%", "von": preis(von), "bis": preis(bis),
             "hoch": preis(max(x["h"] for x in k)), "tief": preis(min(x["l"] for x in k)),
             "vom_hoch": f"{(bis / max(x['h'] for x in k) - 1) * 100:+.1f}%"}
    art, info = "linie", {}
    if ema_n:
        ew = ema_werte[-len(k):]
        art, info = "linien", {"linien": [{"werte": ew, "name": c.get("ema_name", f"EMA {ema_n}"),
                                           "farbe": "akzent2"}]}
        werte.update(ema=preis(ew[-1]), ema_abstand=f"{(bis / ew[-1] - 1) * 100:+.1f}%",
                     ema_lage="above" if bis >= ew[-1] else "below")
    wn = int(c.get("wochen_ma") or 0)   # 13.11.2026 Tobias: die ~68.000 sind die 200-WOCHEN-Linie, nicht die 200-Tage-EMA
    if wn:
        wk = kerzen_holen(c.get("base", "BTC"), "1w", wn)
        if len(wk) >= wn:
            wma = sum(x["c"] for x in wk[-wn:]) / wn
            art = "linien"
            info.setdefault("marken", []).append({"preis": wma, "name": f"MA {wn}W", "farbe": "akzent"})
            werte.update(wma=preis(wma), wma_abstand=f"{(bis / wma - 1) * 100:+.1f}%",
                         wma_lage="above" if bis >= wma else "below")
    rn = int(c.get("rsi") or 0)
    if rn:
        rw = rsi(alle_rsi, rn)[-len(k):]
        if rw and rw[-1] is not None:
            art = "linien"
            info["rsi"] = rw
            werte.update(rsi=f"{rw[-1]:.0f}")
    grafik.echt_chart(img, th, tuple(c["box"]), k, art, info, 3, c.get("lang", "en"), titel)
    ziel = ordner / f"chart_{Path(s['bild']).stem}.png"
    img.convert("RGB").save(ziel)
    return ziel, werte


def rsi(kerzen: list[dict], n: int = 14) -> list[float | None]:
    """RSI nach Wilder (wie TradingView), auf Schlusskursen."""
    out: list[float | None] = [None] * len(kerzen)
    if len(kerzen) <= n:
        return out
    d = [kerzen[i]["c"] - kerzen[i - 1]["c"] for i in range(1, len(kerzen))]
    auf = sum(max(x, 0) for x in d[:n]) / n
    ab = sum(max(-x, 0) for x in d[:n]) / n
    for i in range(n, len(d) + 1):
        if i > n:
            x = d[i - 1]
            auf = (auf * (n - 1) + max(x, 0)) / n
            ab = (ab * (n - 1) + max(-x, 0)) / n
        out[i] = 100.0 if ab == 0 else 100 - 100 / (1 + auf / ab)
    return out


def ema(kerzen: list[dict], n: int) -> list[float | None]:
    """Exponentieller gleitender Durchschnitt der Schlusskurse (Start: einfacher Schnitt der ersten n)."""
    out: list[float | None] = [None] * len(kerzen)
    if n < 1 or len(kerzen) < n:
        return out
    a = 2 / (n + 1)
    e = sum(x["c"] for x in kerzen[:n]) / n
    out[n - 1] = e
    for i in range(n, len(kerzen)):
        e = kerzen[i]["c"] * a + e * (1 - a)
        out[i] = e
    return out


def foto_szene(ordner: Path, s: dict, cfg: dict, fotos_dir: Path | None = None) -> Path:
    """Hochformat-Foto mit Schlagzeile (bildpaket.foto_titel, 1080x1920). s["foto"] = {person, kopf, unter, etikett}."""
    import os
    from . import bildpaket, fotos
    f = s["foto"]
    fotos_dir = fotos_dir or Path(os.environ.get("SOCIAL_FOTOS", Path(os.environ.get("SOCIAL_GEHEIM",
                                                                                  "/opt/volumen-social")) / "fotos"))
    foto = fotos.sicher(fotos_dir, str(f["person"]).lower(), ordner.name)
    if not foto:
        raise ValueError(f"kein freies Foto: {f['person']}")
    W, H = cfg["video"]["breite"], cfg["video"]["hoehe"]
    img = bildpaket.foto_titel(foto, f.get("kopf", ""), f.get("unter", ""), f.get("etikett", "BREAKING"),
                               groesse=(W, H))
    ziel = ordner / f"foto_{Path(s['bild']).stem}.png"
    img.convert("RGB").save(ziel)
    return ziel


class Abbruch(RuntimeError):
    """Live-Lage passt nicht mehr zum Text (z. B. Kurs eingebrochen, Funding gedreht): kein Reel, Tobias neu fragen."""


def _preis_txt(x: float) -> str:
    return f"${x:,.0f}" if x >= 100 else f"${x:,.2f}" if x >= 1 else f"${x:.4g}" if x >= 0.0001 else f"${x:.3g}"


def live_werte(lv: dict, kerzen_holen, web_dir: Path, jetzt: float | None = None) -> dict:
    """14.11.2026 Tobias (S30): „Posts nur mit LIVE-Daten“. Holt direkt vor dem Bauen Kurs (Boerse), Funding und das
    Kerzenbild (Bot, 5-Minuten-Stand) und rechnet die Zahlen fuer den Text: {preis}, {vom_tief}, {fach}, {funding},
    {funding_abs}, {marke_N_abstand}. Mit lv["abbruch"] = {preis_unter, funding_ueber} -> Abbruch statt alter Text."""
    import time as _t
    jetzt = jetzt or _t.time()
    base = lv["base"].upper()
    w: dict = {}
    ab = int(lv.get("tief_ab_ts") or jetzt - 3 * 86400)
    n = min(1000, int((jetzt - ab) / 3600) + 3)
    k = [x for x in kerzen_holen(base, "1h", n) if x["t"] >= ab * 1000]
    if len(k) < 3:
        raise ValueError(f"keine Live-Kurse fuer {base}")
    preis, tief = k[-1]["c"], min(x["l"] for x in k)
    w.update(preis=_preis_txt(preis), vom_tief=f"+{(preis / tief - 1) * 100:.0f}%", fach=f"{preis / tief:.1f}",
             tief=_preis_txt(tief), _preis=preis)
    try:   # Funding: Bot-Stand je Coin (alle 5 Min.), in Prozent
        c = json.loads((Path(web_dir) / "coins" / f"{base}.json").read_text())
        if c.get("funding") is not None and jetzt - float(c.get("ts") or 0) < 1800:
            f = float(c["funding"])
            w.update(funding=f"{f:+.2f}%", funding_abs=f"{abs(f):.2f}%", _funding=f)
    except Exception:
        pass
    try:   # Kerzenbild des Bots (Funding-Extrem oder Eilmeldung), hoechstens 6 Std. alt
        liq = json.loads((Path(web_dir) / "liquiditaet.json").read_text())
        for e in reversed((liq.get("funding_extrem") or []) + (liq.get("eilmeldungen") or [])):
            if str(e.get("base", "")).upper() == base and e.get("kerzen_png"):
                p = Path(web_dir) / e["kerzen_png"]
                if p.exists() and jetzt - p.stat().st_mtime < 6 * 3600:
                    w["_kerzen_png"] = str(p)
                    if "_funding" not in w and e.get("funding") is not None:
                        f = float(e["funding"])
                        w.update(funding=f"{f:+.2f}%", funding_abs=f"{abs(f):.2f}%", _funding=f)
                    break
    except Exception:
        pass
    for i, m in enumerate(lv.get("marken") or []):
        w[f"marke_{i}_abstand"] = f"{(float(m['preis']) / preis - 1) * 100:+.0f}%"
    a = lv.get("abbruch") or {}
    if a.get("preis_unter") is not None and preis < float(a["preis_unter"]):
        raise Abbruch(f"{base} steht bei {_preis_txt(preis)}, unter {a['preis_unter']}: Text passt nicht mehr")
    if a.get("funding_ueber") is not None and "_funding" in w and w["_funding"] > float(a["funding_ueber"]):
        raise Abbruch(f"{base}-Funding ist wieder {w['funding']}: Text passt nicht mehr")
    if a.get("funding_pflicht") and "_funding" not in w:
        raise Abbruch(f"kein aktuelles Funding fuer {base}")
    return w


def bot_bild_szene(ordner: Path, s: dict, png: str, cfg: dict) -> Path:
    """Kerzenbild des Bots in die Szene setzen (unter die Schlagzeile), optional Zoom-Ziel s["fokus"] = [fx, fy]
    als Anteil des Bot-Bilds (z. B. [0.9, 0.6] = rechtes Liquidationsprofil)."""
    img = Image.open(ordner / s["bild"]).convert("RGBA")
    bot = Image.open(png).convert("RGBA")
    W = img.width - 40
    bot = bot.resize((W, int(bot.height * W / bot.width)))
    y = int(s.get("bot_y", 430))
    if y + bot.height > img.height - 330:   # Platz fuer Untertitel lassen
        h = img.height - 330 - y
        bot = bot.resize((int(bot.width * h / bot.height), h))
    x = (img.width - bot.width) // 2
    img.alpha_composite(bot, (x, y))
    ziel = ordner / f"bot_{Path(s['bild']).stem}.png"
    img.convert("RGB").save(ziel)
    if s.get("fokus"):
        fx, fy = s["fokus"]
        ziel.with_suffix(".fokus.json").write_text(json.dumps({"fokus": [x + bot.width * fx, y + bot.height * fy]}))
    return ziel


def bauen(ordner: Path, cfg: dict, geheim: dict, kerzen_holen=None, sprechen=None, schneiden=None) -> str:
    """Baut ordner/video.mp4 aus reel.json. Gibt die Tonquelle zurueck ('elevenlabs', 'stille (...)', ...)."""
    from . import kurse, stimme, video
    kerzen_holen = kerzen_holen or (lambda b, i, n: kurse.kerzen(b, i, n, voll=i in ("1d", "1w")))
    sprechen = sprechen or stimme.sprechen
    schneiden = schneiden or video.bauen
    spec = json.loads((ordner / "reel.json").read_text(encoding="utf-8"))
    bilder, hinweise, zeilen = [], [], []
    live: dict | None = None
    if spec.get("live"):   # 14.11.2026: Zahlen direkt vor dem Bauen live holen; Abbruch geht durch
        try:
            live = live_werte(spec["live"], kerzen_holen, Path(cfg["daten"]["dir"]))
            (ordner / "live_werte.json").write_text(json.dumps({k: v for k, v in live.items() if not k.startswith("_")}))
            hinweise.append("Live: " + ", ".join(f"{k} {v}" for k, v in live.items() if not k.startswith("_")))
        except Abbruch:
            raise
        except Exception as e:
            hinweise.append(f"Live-Daten fehlen ({str(e)[:80]}), Texte ohne Zahlen")
    for s in spec["szenen"]:
        p, text = ordner / s["bild"], s["text"]
        if spec.get("live"):
            try:
                text = text.format(**live) if live else s.get("text_ohne", text)
            except KeyError:
                text = s.get("text_ohne", text)
        bot_ok = False
        if s.get("bot_kerzen") and live and live.get("_kerzen_png"):
            try:
                p, bot_ok = bot_bild_szene(ordner, s, live["_kerzen_png"], cfg), True
            except Exception as e:
                hinweise.append(f"Bot-Chart fehlt ({str(e)[:60]})")
        elif s.get("bot_kerzen"):
            hinweise.append("Kein Live-Kerzenbild vom Bot (Telegram: /kerzen COIN)"
                            + (", eigener Live-Chart statt dessen" if s.get("chart") else ", Szene ohne Chart"))
        if s.get("foto"):   # 13.11.2026: Foto-Szene (Person aus der Bibliothek), sonst bleibt das Bild aus dem Chat
            try:
                p = foto_szene(ordner, s, cfg)
            except Exception as e:
                hinweise.append(f"Foto fehlt ({str(e)[:60]})")
        if s.get("chart") and not bot_ok:   # Ersatz, wenn das Bot-Bild fehlt
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
    t = re.sub(r"https?://\S+", "", x_text).replace("×", "x")   # × ging sonst verloren (ALLO, 06.11.2026)
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
