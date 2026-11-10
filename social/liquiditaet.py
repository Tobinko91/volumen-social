"""S24 Liquiditaetszonen „Top/Flop Coin of the Day“ + Liquiditaets-Eilmeldungen (Wunsch Tobias 06.11.2026).

Daten vom Bot (ab 9.30/9.31): /opt/volumen-bot/web/liquiditaet.json, stuendlich neu
  coins[] (3 x top, 3 x flop), eilmeldungen[] (Pump/Dump sofort), pruefung[] (wirken die Zonen?), hinweis.
Zonen sind SCHAETZUNGEN (Volumenprofil, Swings, Orderbuch, OI-Modell). Darum im Text immer „estimated“, nie „target“
oder „will reach“, sondern „next zone“ / „where liquidity sits“. „our estimated zones held X %“ erst, wenn der Bot
fuer diese Zonenart `wirkt: true` meldet.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from PIL import Image, ImageDraw

ART_EN = {"Widerstand": "resistance", "Unterstuetzung": "support", "Short-Liquidationen": "short liquidations",
          "Long-Liquidationen": "long liquidations"}
LIQ = ("Short-Liquidationen", "Long-Liquidationen")
ZONE_EN = {"Widerstand": "resistance", "Unterstuetzung": "support", "Short-Liquidationen": "short-liquidation",
           "Long-Liquidationen": "long-liquidation"}
MAX_ABSTAND = 35.0   # Zonen weiter als 35 % weg zeigen wir nicht (Chart wuerde unlesbar)


def laden(ordner: Path) -> dict:
    p = Path(ordner) / "liquiditaet.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"coins": [], "eilmeldungen": []}


def pr(x: float) -> str:
    """Preis wie an der Boerse: 23.23 · 0.8421 · 1,234 · 0.0004512."""
    if x >= 100:
        return f"{x:,.0f}"
    if x >= 1:
        return f"{x:.2f}"
    import math
    stellen = max(2, -int(math.floor(math.log10(x))) + 3) if x > 0 else 2   # 4 gueltige Stellen, nie 1.7e-05
    return f"{x:.{stellen}f}".rstrip("0").rstrip(".")


def _pz(x: float) -> float:
    return float(pr(x).replace(",", ""))


def _usd(z: dict) -> str:
    u = z.get("usd")
    if not u:
        return ""
    return f" ~${u / 1e6:.1f}M" if u >= 1e6 else f" ~${u / 1e3:.0f}K"


def zonen(e: dict, n: int = 3) -> tuple[list[dict], list[dict]]:
    """Die naechsten n Zonen oben/unten innerhalb MAX_ABSTAND; ohne Liquidationsmodell nur Widerstand/Unterstuetzung."""
    ok = lambda z: abs(z["abstand_pct"]) <= MAX_ABSTAND and (e.get("mit_liquidationen") or z["art"] not in LIQ)
    return ([z for z in e.get("zonen_oben", []) if ok(z)][:n], [z for z in e.get("zonen_unten", []) if ok(z)][:n])


def erreicht(e: dict) -> dict | None:
    """Die Zone, in die die Bewegung gelaufen ist: bei Top die hoechste erreichte oben, bei Flop die tiefste unten."""
    hoch = (e.get("chg24") or e.get("chg1h") or 0) >= 0
    rz = [z for z in e.get("erreicht_24h", []) if z.get("richtung") == ("oben" if hoch else "unten")
          and (e.get("mit_liquidationen") or z["art"] not in LIQ)]
    if not rz:
        return None
    return max(rz, key=lambda z: z["mitte"]) if hoch else min(rz, key=lambda z: z["mitte"])


def wirkt(pruefung: list[dict], art: str) -> float | None:
    """Abprall-Quote der Zonenart, aber NUR wenn der Bot sie als wirksam bestaetigt (gegen Zufall, >= 30 Faelle)."""
    for r in pruefung or []:
        if r.get("art") == art and r.get("wirkt") is True:
            return (r.get("zone") or {}).get("abprall_pct")
    return None


def texte(e: dict, cfg: dict, pruefung: list[dict] | None = None, eil: bool = False) -> dict:
    from .sprache import hinweis
    hw = hinweis(cfg, "en")
    b = e["base"]
    if eil:
        bew = (e.get("anlass") or "").replace(" Std.", "h").replace(" % in 1h", "% in 1h").replace(" % in 24h", "% in 24h")
        ch = e.get("chg1h") if "1h" in bew else e.get("chg24")
        kopf = f"${b} {ch:+.1f}% in {'1h' if '1h' in bew else '24h'}: where the liquidity sits"
    else:
        kopf = f"${b} {e['chg24']:+.1f}% today: where the liquidity sits"
    satz = []
    r = erreicht(e)
    preis = pr(e["preis"])
    if r:
        satz.append(f"It ran into the estimated {ZONE_EN[r['art']]} zone at {pr(r['mitte'])}.")
    else:
        satz.append(f"{b} trades at {preis}, between estimated zones.")
    no, nu = e.get("naechste_oben"), e.get("naechste_unten")
    nxt, sp = [], []
    if no and abs(no["abstand_pct"]) <= MAX_ABSTAND and (e.get("mit_liquidationen") or no["art"] not in LIQ):
        nxt.append(f"{pr(no['mitte'])} ({no['abstand_pct']:+.1f}%) above")
        sp.append(f"{abs(no['abstand_pct']):.1f}% above")
    if nu and abs(nu["abstand_pct"]) <= MAX_ABSTAND and (e.get("mit_liquidationen") or nu["art"] not in LIQ):
        nxt.append(f"{pr(nu['mitte'])} ({nu['abstand_pct']:+.1f}%) below")
        sp.append(f"{abs(nu['abstand_pct']):.1f}% below")
    if nxt:
        satz.append("Next zones: " + ", ".join(nxt) + ".")
    quote = wirkt(pruefung, r["art"]) if r else None
    if quote is not None:
        satz.append(f"Our estimated {ZONE_EN[r['art']]} zones held {quote:.0f}% of the time.")
    x = "\n".join([f"💧 {kopf}", *satz, "Estimated zones, not targets.", hw])
    if len(x) > 280:
        x = "\n".join([f"💧 {kopf}", satz[0], hw])
    oben, unten = zonen(e)
    esc = lambda s: html.escape(s, quote=False)
    tg = [f"💧 <b>{esc(kopf)}</b>", "", *[esc(s) for s in satz], ""]
    if oben:
        tg.append("<b>Estimated zones above</b>")
        tg += [f"• {pr(z['mitte'])} ({z['abstand_pct']:+.1f}%) · {ART_EN[z['art']]}{_usd(z)}" for z in oben]
    if unten:
        tg.append("<b>Estimated zones below</b>")
        tg += [f"• {pr(z['mitte'])} ({z['abstand_pct']:+.1f}%) · {ART_EN[z['art']]}{_usd(z)}" for z in unten]
    if not e.get("mit_liquidationen"):
        tg.append(esc("No futures data for a liquidation estimate: support and resistance only."))
    tg += ["", esc("Zones are estimates from price, volume, order book and open interest. Not targets."), "",
           f"<i>{esc(hw)}</i>"]
    # Sprechtext: ohne $ und ohne Klammern, Abstaende statt langer Preise
    sprech = [kopf.replace("$", "") + ".", satz[0]]
    if sp:
        sprech.append("Next estimated zones: " + " and ".join(sp) + ".")
    sprech += [z for z in satz[1:] if z.startswith("Our estimated")]
    return {"x": x, "telegram": "\n".join(tg), "sprech": sprech, "kopf": kopf}


def fakten(e: dict, pruefung: list[dict] | None = None) -> dict:
    """Alle Zahlen, die im Text stehen duerfen (gerundet wie angezeigt), fuer social/pruefung.py."""
    zs = e.get("zonen_oben", []) + e.get("zonen_unten", []) + e.get("erreicht_24h", [])
    werte = [_pz(e["preis"]), 1, 24] + [_pz(z["mitte"]) for z in zs] + [round(z["abstand_pct"], 1) for z in zs]
    werte += [round(e.get("chg24") or 0), round(e.get("chg1h") or 0)]
    werte += [round((z.get("usd") or 0) / 1e6, 1) for z in zs] + [round((z.get("usd") or 0) / 1e3) for z in zs]
    werte += [round(r["zone"]["abprall_pct"]) for r in pruefung or [] if (r.get("zone") or {}).get("abprall_pct")]
    return {"base": e["base"], "zahlen": werte}


def bild(e: dict, cfg: dict, ziel: Path, kopf: str, hoch: int = 1350, eil: bool = False) -> Path:
    """4:5 (1080x1350) oder 9:16 (1080x1920): 7-Tage-Kerzen, Zonen als halbtransparente Baender, erreichte Zone
    mit HIT, rechts Abstand in % und (bei Liquidationen) geschaetzte Summe."""
    from . import design
    from .design import etikett, font, fuss, hintergrund, marke, rgb, thema_waehlen, ueberschrift
    W, H = 1080, hoch
    th = thema_waehlen("markt", f"liq-{e['base']}")
    img = hintergrund(th, W, H, saat=17)
    marke(img, th, 80, 64 if H < 1600 else 90, 64 if H < 1600 else 72)
    d = ImageDraw.Draw(img)
    y0 = 170 if H < 1600 else 230
    etikett(d, th, 80, y0, ("BREAKING · " if eil else "") + ("TOP COIN" if (e.get("chg24") or 0) >= 0 else "FLOP COIN")
            + " · LIQUIDITY", farbe=th.minus if (e.get("chg24") or 0) < 0 else th.plus)
    y = ueberschrift(d, th, 80, y0 + 80, kopf, W - 160, groesse=54 if H < 1600 else 66, max_zeilen=2) + 20
    box = (60, y, W - 60, H - (130 if H < 1600 else 720))   # 9:16: unten Platz fuer die Untertitel (ab 1230)
    _chart(img, th, box, e)
    d = ImageDraw.Draw(img)
    d.text((80, box[3] + 14), "Estimated zones · not targets", font=font("Medium", 24), fill=th.neben)
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel


def _chart(img, th, box, e: dict):
    from .design import font, karte, rgb
    karte(img, th, box)
    x0, y0, x1, y1 = box
    k = e.get("kerzen") or []
    oben, unten = zonen(e)
    preise = [v for c in k for v in (c[2], c[3])] + [z[s] for z in oben + unten for s in ("von", "bis")]
    if not preise:
        return
    lo, hi = min(preise), max(preise)
    pad = (hi - lo) * 0.06 or hi * 0.02
    lo, hi = lo - pad, hi + pad
    px0, px1, py0, py1 = x0 + 30, x1 - 300, y0 + 30, y1 - 30
    Y = lambda p: py1 - (py1 - py0) * (p - lo) / (hi - lo)
    ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ed = ImageDraw.Draw(ebene)
    r = erreicht(e)
    for z in oben + unten:
        liq = z["art"] in LIQ
        ed.rectangle([px0, Y(z["bis"]), x1 - 20, Y(z["von"])], fill=rgb("#B69CFF" if liq else "#F2F0FF", 70 if liq else 38))
    img.alpha_composite(ebene)
    d = ImageDraw.Draw(img)
    n = len(k)
    if n:
        bw = (px1 - px0) / n
        for i, (t, o, h, l, c, v) in enumerate(k):
            xm = px0 + bw * (i + 0.5)
            farbe = th.plus if c >= o else th.minus
            d.line([(xm, Y(h)), (xm, Y(l))], fill=farbe, width=1)
            d.rectangle([xm - max(1, bw * 0.35), Y(max(o, c)), xm + max(1, bw * 0.35), Y(min(o, c)) + 1], fill=farbe)
        d.line([(px0, Y(k[-1][4])), (x1 - 20, Y(k[-1][4]))], fill=th.text, width=2)
    fl, fk = font("Bold", 24), font("Medium", 20)
    belegt = []
    for z in oben + unten:
        yy = Y(z["mitte"])
        if any(abs(yy - b) < 46 for b in belegt):   # Beschriftungen nie uebereinander
            continue
        belegt.append(yy)
        txt = f"{z['abstand_pct']:+.1f}% · {pr(z['mitte'])}"
        art = ART_EN[z["art"]].replace("liquidations", "liq.") + _usd(z)
        farbe = th.akzent2 if z["art"] in LIQ else th.text
        d.text((px1 + 16, yy - 26), txt, font=fl, fill=farbe)
        d.text((px1 + 16, yy + 2), art, font=fk, fill=th.neben)
    if r:
        yy = Y(r["mitte"])
        d.rounded_rectangle([px0 + 8, yy - 16, px0 + 78, yy + 16], radius=10, fill=th.akzent)
        d.text((px0 + 16, yy - 13), "HIT", font=font("Bold", 22), fill=rgb("#140F2E"))


# ---------------------------------------------------------------- Heatmap (S24/S28, Bot 9.34/9.35)

def heatmap_bild(e: dict, ziel: Path, W: int = 1080, H: int = 1350, titel: str | None = None) -> Path | None:
    """Liquidations-Heatmap aus den Rohdaten des Bots, englisch, Design „Nachtleuchten“:
    x = Zeit, y = Preis, Farbe = geschaetzte USD (dunkel -> Flieder -> Minze), Kurs als weisse Linie.
    Nie fremde Heatmaps (Coinglass & Co. verbieten kommerzielle Nutzung)."""
    from . import design
    from .design import font, rgb
    hm = e.get("heatmap")
    if not hm or not hm.get("zeiten") or not hm.get("preise"):
        return None
    th = design.THEMEN["nacht"]
    img = design.hintergrund(th, W, H, saat=23)
    design.marke(img, th, 80, 64 if H < 1600 else 90, 64 if H < 1600 else 72)
    d = ImageDraw.Draw(img)
    y0 = 170 if H < 1600 else 230
    design.etikett(d, th, 80, y0, f"${e['base']} · ESTIMATED LIQUIDATION HEATMAP", farbe=th.akzent2)
    y = design.ueberschrift(d, th, 80, y0 + 80, titel or heat_kopf(e), W - 160, groesse=50 if H < 1600 else 62,
                            max_zeilen=2) + 20
    box = (60, y, W - 60, H - (140 if H < 1600 else 720))
    design.karte(img, th, box)
    x0, by0, x1, by1 = box
    px0, px1, py0, py1 = x0 + 24, x1 - 150, by0 + 24, by1 - 44
    zeiten, preise = hm["zeiten"], hm["preise"]
    mx = hm.get("max_usd") or max(max(a + b for a, b in zip(lz, sz)) for lz, sz in zip(hm["long_usd"], hm["short_usd"])) or 1
    nt, npr = len(zeiten), len(preise)
    import math
    lo, hi = math.log(preise[0]), math.log(preise[-1])
    Y = lambda p: min(py1, max(py0, py1 - (py1 - py0) * (math.log(max(p, 1e-12)) - lo) / (hi - lo)))   # im Rahmen
    def farbe(w):   # 0..1 -> Mitternacht -> Flieder -> Minze
        w = max(0.0, min(1.0, w)) ** 0.6
        a, b, c = (28, 22, 64), (182, 156, 255), (60, 242, 192)
        if w < 0.6:
            t = w / 0.6
            return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
        t = (w - 0.6) / 0.4
        return tuple(int(b[i] + (c[i] - b[i]) * t) for i in range(3))
    bw = (px1 - px0) / nt
    for ti in range(nt):
        for pj in range(npr):
            w = (hm["long_usd"][ti][pj] + hm["short_usd"][ti][pj]) / mx
            if w < 0.08:   # Grundrauschen weglassen
                continue
            ya = Y(preise[pj])
            yb = Y(preise[pj + 1]) if pj + 1 < npr else ya - (py1 - py0) / npr
            d.rectangle([px0 + ti * bw, yb, px0 + (ti + 1) * bw, ya], fill=farbe(w))
    k = [c for c in e.get("kerzen") or [] if c[0] >= zeiten[0]]
    if len(k) > 1:
        t0_, t1_ = zeiten[0], zeiten[-1] + (zeiten[-1] - zeiten[-2] if nt > 1 else 3600)
        X = lambda t: px0 + (px1 - px0) * (t - t0_) / (t1_ - t0_)
        d.line([(X(c[0]), Y(c[4])) for c in k], fill=rgb(design.TEXT), width=3)
    fl = font("SemiBold", 22)
    belegt = [Y(e["preis"])]
    d.text((px1 + 14, Y(e["preis"]) - 12), pr(e["preis"]), font=font("Bold", 24), fill=th.text)
    for p in (preise[0], preise[npr // 2], preise[-1]):
        if all(abs(Y(p) - b) > 40 for b in belegt):
            belegt.append(Y(p))
            d.text((px1 + 14, Y(p) - 12), pr(p), font=fl, fill=th.neben)
    d.text((px0, by1 - 34), "WhaleSqueeze · estimated liquidation heatmap · brighter = more estimated liquidations",
           font=font("Medium", 20), fill=th.neben)
    h = hellster(e)
    if h:   # Mittelpunkt des hellsten Bandes fuer den Zoom im Reel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.with_suffix(".fokus.json").write_text(json.dumps({"fokus": [round(px0 + (px1 - px0) * 0.75),
                                                                         round(Y(h["preis"]))]}))
    design.fuss(img, th, "Not financial advice.")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel


def hellster(e: dict) -> dict | None:
    """Hellstes Band (groesste geschaetzte Liquidationssumme in der letzten Zeitspalte)."""
    hm = e.get("heatmap")
    if not hm:
        return None
    letzte = [a + b for a, b in zip(hm["long_usd"][-1], hm["short_usd"][-1])]
    j = max(range(len(letzte)), key=lambda i: letzte[i])
    p = hm["preise"][j]
    return {"preis": p, "abstand_pct": round((p / e["preis"] - 1) * 100, 1), "usd": letzte[j]}


def heat_kopf(e: dict) -> str:
    h = hellster(e)
    if not h:
        return f"Where the liquidity sits for ${e['base']}"
    return f"Brightest band = biggest estimated liquidation cluster at {pr(h['preis'])} ({h['abstand_pct']:+.1f}%)"


# ---------------------------------------------------------------- Beitrag: Bild + Reel

def beitrag(e: dict, ordner: Path, cfg: dict, pruefung: list | None, eil: bool = False) -> dict:
    """post.png (4:5) + post_x.txt + post_telegram.txt; Szenen fuer das Reel (9:16). Rueckgabe: Texte + Szenen."""
    tx = texte(e, cfg, pruefung, eil)
    ordner.mkdir(parents=True, exist_ok=True)
    bild(e, cfg, ordner / "post.png", tx["kopf"], eil=eil)
    (ordner / "post_x.txt").write_text(tx["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(tx["telegram"], encoding="utf-8")
    szenen = [(bild(e, cfg, ordner / "bilder" / "zonen.png", tx["kopf"], hoch=1920, eil=eil), " ".join(tx["sprech"][:2]))]
    if len(tx["sprech"]) > 2:
        szenen.append((szenen[0][0], " ".join(tx["sprech"][2:])))
    h = hellster(e)
    hb = heatmap_bild(e, ordner / "bilder" / "heatmap.png", H=1920)
    if hb and h:
        szenen.append((hb, f"The brightest band is the biggest estimated liquidation cluster, "
                           f"{abs(h['abstand_pct']):.1f}% {'above' if h['abstand_pct'] >= 0 else 'below'} the price."))
        heatmap_bild(e, ordner / "heatmap.png")   # 4:5: zweites Bild (Pflicht laut S24, wenn vorhanden)
        (ordner / "karussell.json").write_text(json.dumps({"folien": ["post.png", "heatmap.png"]}), encoding="utf-8")
    szenen[-1] = (szenen[-1][0], szenen[-1][1] + " Estimated zones, not targets. Follow for more.")
    return dict(tx, szenen=szenen)


def reel(b: dict, ordner: Path, cfg: dict, geheim: dict, sprechen=None, schneiden=None) -> tuple[Path, str]:
    from . import stimme, video
    sprechen = sprechen or stimme.sprechen
    schneiden = schneiden or video.bauen
    bilder = [p for p, _ in b["szenen"]]
    zeilen = [t for _, t in b["szenen"]]
    toene, dauern, quelle = sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    schneiden(bilder, toene, dauern, ordner / "video.mp4", cfg, **video.ut_formate(cfg, zeilen))
    return ordner / "video.mp4", quelle


# ---------------------------------------------------------------- Eilmeldungen (live.sh, alle 10 Min.)

def eil_auswahl(d: dict, stand: dict, jetzt: float, sperr: set, max_tag: int = 4) -> list[dict]:
    """Neue Eilmeldungen: noch nicht gemeldet, je Coin hoechstens 1 in 12 Std., hoechstens max_tag am Tag,
    nicht in der Ruhezeit 22-7 Uhr (deutsche Zeit)."""
    import time as _t
    from datetime import datetime
    from zoneinfo import ZoneInfo
    stunde = datetime.fromtimestamp(jetzt, ZoneInfo("Europe/Berlin")).hour
    if stunde >= 22 or stunde < 7:
        return []
    tag = datetime.fromtimestamp(jetzt, ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
    heute = stand.get("tage", {}).get(tag, 0)
    out = []
    for e in d.get("eilmeldungen") or []:
        b = e["base"].upper()
        if b in sperr or str(e.get("erstmals")) in stand.get("gemeldet", []):
            continue
        if jetzt - stand.get("coin", {}).get(b, 0) < 12 * 3600:
            continue
        if heute + len(out) >= max_tag:
            break
        out.append(e)
    _ = _t
    return out


def eil_merken(stand: dict, e: dict, jetzt: float) -> dict:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tag = datetime.fromtimestamp(jetzt, ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
    stand.setdefault("gemeldet", []).append(str(e.get("erstmals")))
    stand["gemeldet"] = stand["gemeldet"][-500:]
    stand.setdefault("coin", {})[e["base"].upper()] = jetzt
    stand.setdefault("tage", {})[tag] = stand.get("tage", {}).get(tag, 0) + 1
    stand["tage"] = dict(list(stand["tage"].items())[-14:])
    return stand
