"""Spar-Rennen zweier Aktien als Reel-Szene (Wunsch Tobias 19.11.2026, Vorbild: „$100/month in Apple vs Nvidia since
1999 with dividends reinvested“).

Jeden Monat wird derselbe Betrag in beide Aktien gesteckt. Die Kurve waechst Monat fuer Monat, darueber laufen
„Invested“, Wert A und Wert B mit. Kurse kommen auf dem Server live von Yahoo (Monatskurse, „adjclose“ = um Splits
und Dividenden bereinigt, Dividenden also wieder angelegt). Nie Kurse aus dem Chat oder von Webseiten abtippen.

reel.json, Szene: {"bild": "szene_1.png", "text": "...{a_wert}...", "rennen": {
    "a": {"symbol": "AAPL", "name": "Apple", "person": "jobs"},
    "b": {"symbol": "NVDA", "name": "NVIDIA", "person": "huang"},
    "ab": "1999-01", "monat": 100, "sekunden": 30}}
Platzhalter im Text: {investiert} {a_wert} {b_wert} {a_fach} {b_fach} {monate} {ab_jahr}
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from . import design
from .design import font, rgb

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{s}"
FARBE_A, FARBE_B = design.TEXT, design.MINZE


def monatskurse(symbol: str, ab: str, get=requests.get) -> list[tuple[str, float]]:
    """[(JJJJ-MM, bereinigter Schlusskurs)] von Yahoo, Monatswerte ab 'ab' (JJJJ-MM)."""
    j, m = map(int, ab.split("-"))
    p1 = int(dt.datetime(j, m, 1, tzinfo=dt.timezone.utc).timestamp())
    r = get(YAHOO.format(s=symbol), params={"period1": p1, "period2": int(dt.datetime.now(dt.timezone.utc).timestamp()),
                                             "interval": "1mo", "events": "div,splits"},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    res = r.json()["chart"]["result"][0]
    ts = res["timestamp"]
    adj = res["indicators"]["adjclose"][0]["adjclose"]
    out = {}
    for t, k in zip(ts, adj):
        if k:
            out[dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m")] = float(k)
    if len(out) < 12:
        raise ValueError(f"zu wenige Monatskurse fuer {symbol}")
    return sorted(out.items())


def sparplan(a: list[tuple[str, float]], b: list[tuple[str, float]], monat: float) -> list[dict]:
    """Je Monat {m, inv, a, b}: Wert beider Depots am Monatsende, Kauf zum Monatskurs (nur gemeinsame Monate)."""
    kb = dict(b)
    sa = sb = inv = 0.0
    out = []
    for m, pa in a:
        pb = kb.get(m)
        if not pb:
            continue
        sa += monat / pa
        sb += monat / pb
        inv += monat
        out.append({"m": m, "inv": inv, "a": sa * pa, "b": sb * pb})
    return out


def geld(x: float) -> str:
    return f"${x:,.0f}"


def achse(x: float) -> str:
    return f"${x / 1e6:g}M" if x >= 1e6 else f"${x / 1e3:g}K" if x >= 1e3 else f"${x:g}"


def _schritte(hoch: float) -> list[float]:
    roh = hoch / 4
    p = 10 ** len(str(int(roh))) / 10
    for f in (1, 2, 2.5, 5, 10):
        if roh <= f * p:
            s = f * p
            break
    return [s * i for i in range(0, int(hoch / s) + 1)]


def bild(werte: list[dict], spec: dict, fotos: dict, W: int = 1080, H: int = 1920) -> Image.Image:
    th = design.THEMEN["nacht"]
    img = design.hintergrund(th, W, H, saat=1999)
    design.marke(img, th, 70, 70, 64)
    d = ImageDraw.Draw(img)
    na, nb = spec["a"]["name"], spec["b"]["name"]
    # Kopf: Foto A · Name A  vs  Name B · Foto B
    y0 = 180
    for seite, key in ((0, "a"), (1, "b")):
        f = fotos.get(key)
        x = 70 if seite == 0 else W - 70 - 200
        if f is not None:
            img.paste(f, (x, y0), f)
        else:
            d.rounded_rectangle((x, y0, x + 200, y0 + 200), 100, outline=rgb(FARBE_A if key == "a" else FARBE_B), width=6)
    d = ImageDraw.Draw(img)
    fk = font("Bold", 64)
    d.text((290, y0 + 60), na, font=fk, fill=FARBE_A)
    d.text((W - 290 - d.textlength(nb, font=fk), y0 + 60), nb, font=fk, fill=FARBE_B)
    fv = font("Medium", 40)
    d.text(((W - d.textlength("vs", font=fv)) / 2, y0 + 76), "vs", font=fv, fill=design.NEBEN)
    letzt = werte[-1]
    # Zahlenzeile
    y1 = y0 + 250
    fz, fl = font("Bold", 42), font("Medium", 28)
    for i, (lab, wert, farbe) in enumerate((("Invested", letzt["inv"], design.NEBEN), (na, letzt["a"], FARBE_A),
                                             (nb, letzt["b"], FARBE_B))):
        x = 70 + i * 320
        d.text((x, y1), lab, font=fl, fill=design.NEBEN)
        d.text((x, y1 + 36), geld(wert), font=fz, fill=farbe)
    # Diagramm
    L, R, O, U = 190, W - 70, y1 + 190, 1620
    monate = [w["m"] for w in werte]   # Zeitachse waechst mit (wie im Vorbild)
    alle = max(len(monate), 12)
    hoch = max(max(w["a"], w["b"], w["inv"]) for w in werte) * 1.1
    fa = font("Medium", 26)
    for s in _schritte(hoch):
        y = U - (U - O) * s / hoch
        d.line((L, y, R, y), fill=rgb(design.LINIE), width=2)
        d.text((L - 14 - d.textlength(achse(s), font=fa), y - 15), achse(s), font=fa, fill=design.NEBEN)
    jahre = sorted({m[:4] for m in monate})
    schritt = max(1, len(jahre) // 6)
    for k, jahr in enumerate(jahre):
        if k % schritt:
            continue
        i = next(n for n, m in enumerate(monate) if m.startswith(jahr))
        x = L + (R - L) * i / max(1, alle - 1)
        d.text((x - d.textlength(jahr, font=fa) / 2, U + 16), jahr, font=fa, fill=design.NEBEN)
    pos = lambda i, v: (L + (R - L) * i / max(1, alle - 1), U - (U - O) * v / hoch)
    inv = [pos(i, w["inv"]) for i, w in enumerate(werte)]
    for i in range(0, len(inv) - 1, 2):   # gestrichelt
        d.line((inv[i], inv[i + 1]), fill=rgb(design.NEBEN), width=3)
    for key, farbe in (("a", FARBE_A), ("b", FARBE_B)):
        pk = [pos(i, w[key]) for i, w in enumerate(werte)]
        if len(pk) > 1:
            d.line(pk, fill=rgb(farbe), width=6, joint="curve")
    # Beschriftung am Linienende (nicht uebereinander)
    fe = font("Bold", 30)
    ya, yb = pos(len(werte) - 1, letzt["a"])[1], pos(len(werte) - 1, letzt["b"])[1]
    if abs(ya - yb) < 44:   # Beschriftungen nicht uebereinander
        ya, yb = (ya, ya + 44) if ya <= yb else (yb + 44, yb)
    for name, wert, y, farbe in ((na, letzt["a"], ya, FARBE_A), (nb, letzt["b"], yb, FARBE_B)):
        t = f"{name} {geld(wert)}"
        d.text((R - d.textlength(t, font=fe), max(O - 40, y - 44)), t, font=fe, fill=farbe)
    d.text((70, U + 70), f"${spec.get('monat', 100):g}/month since {spec['_monate'][0][:4]} · dividends reinvested",
           font=font("Medium", 32), fill=design.NEBEN)
    design.fuss(img, th, "Not financial advice.")
    return img.convert("RGB")


def _rund(foto: dict | None, groesse: int = 200) -> Image.Image | None:
    if not foto:
        return None
    try:
        f = Image.open(foto["pfad"]).convert("RGB")
        s = min(f.size)
        f = f.crop(((f.width - s) // 2, 0, (f.width + s) // 2, s)).resize((groesse, groesse))
        m = Image.new("L", (groesse, groesse), 0)
        ImageDraw.Draw(m).ellipse((0, 0, groesse, groesse), fill=255)
        f.putalpha(m)
        return f
    except Exception:
        return None


def szene(ordner: Path, s: dict, fotos_dir: Path | None = None, holen=None) -> tuple[list, dict, float]:
    """-> (Bildfolge [(png, Sekunden)], Platzhalter, Mindestdauer der Szene)."""
    from . import fotos
    r = dict(s["rennen"])
    holen = holen or monatskurse
    ab = r.get("ab", "1999-01")
    werte = sparplan(holen(r["a"]["symbol"], ab), holen(r["b"]["symbol"], ab), float(r.get("monat", 100)))
    r["_monate"] = [w["m"] for w in werte]
    bilder = {}
    for key in ("a", "b"):
        person = r[key].get("person")
        bilder[key] = _rund(fotos.sicher(fotos_dir, person, ordner.name)) if person and fotos_dir else None
    ziel = ordner / "rennen"
    ziel.mkdir(exist_ok=True)
    sek = float(r.get("sekunden", 30))
    n = len(werte)
    schritt = max(1, n // 300)   # hoechstens ~300 Bilder
    idx = list(range(schritt - 1, n, schritt))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    folge = []
    for k, i in enumerate(idx):
        p = ziel / f"r_{k:04d}.png"
        bild(werte[:i + 1], r, bilder).save(p)
        folge.append((p, sek / len(idx)))
    e = werte[-1]
    platz = {"investiert": geld(e["inv"]), "a_wert": geld(e["a"]), "b_wert": geld(e["b"]),
             "a_fach": f"{e['a'] / e['inv']:.0f}x", "b_fach": f"{e['b'] / e['inv']:.0f}x",
             "monate": str(n), "ab_jahr": ab[:4]}
    return folge, platz, sek
