"""Coin-Check: ein Coin mit allen Daten auf einem Bild (nach Vorbild beliebter X-Posts, 22.10.2026).

Kurs 7 Tage mit Volumenprofil und den staerksten Volumen-Bereichen, Open Interest, Funding, Spot-Anteil,
Wal-Anteile, Termine. Bewusst OHNE Bewertung, Kursziel oder Kauf-/Verkaufssignal: reine Marktdaten + Erklaerung.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from .design import absatz, de, etikett, font, fuss, hintergrund, karte, marke, punkte, rgb, thema_waehlen
from .sprache import MONATE_DE


def preis(p: float) -> str:
    if p >= 100:
        return de(p, 0) + " $"
    if p >= 1:
        return de(p, 2) + " $"
    stellen = 2
    while p < 10 ** -(stellen - 1) and stellen < 8:
        stellen += 1
    return de(p, stellen + 1) + " $"


def mio(x: float | None) -> str:
    if x is None:
        return "–"
    if x >= 1e9:
        return de(x / 1e9, 2) + " Mrd. $"
    return de(x / 1e6, 1) + " Mio. $"


def auswahl(coins: dict, sperr: set[str], stand: dict, min_mcap: float = 20e6) -> str | None:
    """Auffaelligster Coin: groesste OI-Veraenderung (4 Std.) plus Kursbewegung, nicht in den letzten 7 Tagen."""
    jetzt = time.time()
    kandidaten = []
    for b, c in coins.items():
        if b in sperr or (c.get("mcap") or 0) < min_mcap or c.get("oi") is None:
            continue
        if jetzt - stand.get(b, 0) < 7 * 86400:
            continue
        kandidaten.append((abs(c.get("oi_chg4h") or 0) + abs(c.get("chg24") or 0) / 2, b))
    return max(kandidaten)[1] if kandidaten else None


def fakten(c: dict, k: list[dict], z: dict) -> dict:
    f = {"coin": c["base"], "kurs": c.get("price"), "zeitraeume_stunden_tage": [4, 24, 7],
         "open_interest_mio": round(c["oi"] / 1e6, 1) if c.get("oi") else None,
         "marktkapitalisierung_mio": round(c["mcap"] / 1e6, 1) if c.get("mcap") else None, "marktkapitalisierung": c.get("mcap"),
         "veraenderung_24h_prozent": c.get("chg24"), "open_interest_usd": c.get("oi"),
         "open_interest_veraenderung_4h_prozent": c.get("oi_chg4h"), "funding_prozent": c.get("funding"),
         "spot_anteil_volumen_prozent": c.get("spot_anteil"), "wale_prozent_der_menge": c.get("wale"),
         "termine": c.get("termine") or []}
    if k:
        f["kurs_7_tage"] = {"hoch": max(x["h"] for x in k), "tief": min(x["l"] for x in k),
                            "veraenderung_prozent": round((k[-1]["c"] / k[0]["o"] - 1) * 100, 1)}
        f["volumen_bereiche"] = {"oberhalb": [[round(y["lo"], 8), round(y["hi"], 8)] for y in z["oben"]],
                                 "unterhalb": [[round(y["lo"], 8), round(y["hi"], 8)] for y in z["unten"]]}
    return f


SYSTEM = """Du bist Analyst bei WhaleSqueeze (deutscher Krypto-Kanal). Erkläre die Daten zu EINEM Coin sachlich.
Regeln:
- Nur Zahlen aus dem JSON (deutsche Schreibweise, Komma). Keine eigenen Rechnungen, keine Prognose, kein Kursziel,
  keine Bewertung wie "unterbewertet" oder "Potenzial", keine Aufforderung zu kaufen oder zu verkaufen.
- Erkläre, was die Daten bedeuten: z. B. negatives Funding = Short-Positionen zahlen, steigendes Open Interest =
  neue Positionen, hoher Börsen-Anteil der Wale = mögliches Verkaufsangebot, Volumen-Bereiche = dort wurde viel gehandelt.
- Ruhig, verständlich, keine Emojis, keine Hype-Wörter.
Antworte NUR mit JSON:
{"schlagzeile": "höchstens 60 Zeichen, nennt den Coin",
 "punkte": ["3 kurze Sätze, je höchstens 150 Zeichen"],
 "x": "Text für X, höchstens 220 Zeichen, nennt Coin mit $-Zeichen, ohne Link"}"""


def schreiben(f: dict, cfg: dict, api_key: str | None) -> dict:
    if api_key:
        try:
            r = requests.post("https://api.anthropic.com/v1/messages",
                              headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                                       "content-type": "application/json"},
                              json={"model": cfg["text"]["modell"], "max_tokens": 700, "system": SYSTEM,
                                    "messages": [{"role": "user", "content": json.dumps(f, ensure_ascii=False)}]},
                              timeout=90)
            r.raise_for_status()
            t = "".join(b.get("text", "") for b in r.json().get("content", []))
            d = json.loads(t[t.find("{"): t.rfind("}") + 1])
            if d.get("schlagzeile") and d.get("punkte") and d.get("x"):
                d["punkte"] = d["punkte"][:3]
                return d
        except Exception as e:
            print("Claude-Fehler Coin-Check:", e)
    return vorlage(f)


def vorlage(f: dict) -> dict:
    c = f["coin"]
    p = []
    if f.get("open_interest_veraenderung_4h_prozent") is not None:
        v = f["open_interest_veraenderung_4h_prozent"]
        p.append(f"Open Interest {mio(f['open_interest_usd'])}, in 4 Stunden {de(v)} %: "
                 f"{'neue Positionen kommen dazu' if v > 0 else 'Positionen werden geschlossen'}.")
    if f.get("funding_prozent") is not None:
        fu = f["funding_prozent"]
        p.append(f"Funding {de(fu, 4)} %: {'Short-Positionen zahlen an Longs' if fu < 0 else 'Long-Positionen zahlen an Shorts'}.")
    w = f.get("wale_prozent_der_menge") or {}
    if w.get("boerse") is not None:
        p.append(f"{de(w['boerse'])} % der Menge liegen auf Börsen-Adressen, {de(w.get('wal') or 0)} % bei Walen.")
    return {"schlagzeile": f"${c} im Coin-Check", "punkte": p[:3],
            "x": f"${c} im Coin-Check: " + " ".join(p[:2])[:200]}


def texte(d: dict, cfg: dict) -> dict:
    import html
    x = d["x"].strip()
    if "Keine Anlageberatung" not in x:
        x = f"{x}\n{cfg['hinweise']['post_text']}"
    tg = [f"🔎 <b>{html.escape(d['schlagzeile'])}</b>", ""] + [f"• {html.escape(p)}" for p in d["punkte"]]
    tg += ["", f"<i>{cfg['hinweise']['post_text']}</i>"]
    return {"x": x[:280], "telegram": "\n".join(tg)}


def bild(c: dict, k: list[dict], z: dict, d: dict, cfg: dict, ziel: Path) -> Path:
    tag = dt.date.today().isoformat()
    th = thema_waehlen("markt", f"{tag}:{c['base']}")
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=len(c["base"]))
    t = dt.datetime.now()
    marke(img, th, 80, 64, 64, untertitel=f"{t.day}. {MONATE_DE[t.month - 1]} {t.year}")
    dr = ImageDraw.Draw(img)
    etikett(dr, th, 80, 170, "COIN-CHECK")
    dr.text((80, 246), f"${c['base']}", font=font("Bold", 92), fill=th.text)
    fw = font("Bold", 50)
    ch = c.get("chg24") or 0
    s = f"{preis(c['price'])}   {'+' if ch >= 0 else ''}{de(ch)} %"
    dr.text((W - 80 - dr.textlength(s, font=fw), 276), s, font=fw, fill=th.plus if ch >= 0 else th.minus)

    # Kurs 7 Tage mit Volumenprofil
    box = (80, 370, W - 80, 800)
    karte(img, th, box)
    dr = ImageDraw.Draw(img)
    dr.text((116, 392), "Kurs 7 Tage · Volumenprofil · stärkste Handelsbereiche", font=font("Medium", 24), fill=th.neben)
    if k:
        lo, hi = z["grenzen"][0], z["grenzen"][-1]
        px0, px1, py0, py1 = 116, W - 300, 440, 770

        def py(p):
            return py1 - (py1 - py0) * (p - lo) / ((hi - lo) or 1)
        ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
        e = ImageDraw.Draw(ebene)
        for y in z["oben"] + z["unten"]:
            farbe = th.akzent2
            e.rectangle([px0, py(y["hi"]), W - 116, py(y["lo"])], fill=rgb(farbe, 48))
        vmax = max(z["vol"]) or 1
        for i, v in enumerate(z["vol"]):   # Profil rechts
            y0, y1 = py(z["grenzen"][i + 1]), py(z["grenzen"][i])
            e.rectangle([W - 116 - 150 * v / vmax, y0 + 1, W - 116, y1 - 1], fill=rgb(th.akzent2, 120))
        img.alpha_composite(ebene)
        dr = ImageDraw.Draw(img)
        pts = [(px0 + (px1 - px0) * i / (len(k) - 1), py(x["c"])) for i, x in enumerate(k)]
        dr.line(pts, fill=th.text, width=4, joint="curve")
        dr.ellipse([pts[-1][0] - 8, pts[-1][1] - 8, pts[-1][0] + 8, pts[-1][1] + 8], fill=th.akzent)
        fz = font("SemiBold", 22)
        for y, wo in [(y, "oben") for y in z["oben"]] + [(y, "unten") for y in z["unten"]]:
            txt = f"{preis(y['lo'])} – {preis(y['hi'])}"
            ty = py(y["hi"]) - 30 if wo == "oben" else py(y["lo"]) + 6
            ty = min(max(ty, py0 - 4), py1 - 24)
            ebene = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(ebene).rounded_rectangle([px0, ty - 2, px0 + dr.textlength(txt, font=fz) + 16, ty + 28],
                                                    radius=8, fill=rgb(th.grund, 210))
            img.alpha_composite(ebene)
            dr = ImageDraw.Draw(img)
            dr.text((px0 + 8, ty), txt, font=fz, fill=th.akzent2)

    # Kacheln
    w = c.get("wale") or {}
    termin = (c.get("termine") or [{}])[0]
    kacheln = [
        ("Open Interest", mio(c.get("oi")), f"4 Std.: {'+' if (c.get('oi_chg4h') or 0) >= 0 else ''}{de(c.get('oi_chg4h') or 0)} %"
         if c.get("oi_chg4h") is not None else ""),
        ("Funding", f"{de(c['funding'], 4)} %" if c.get("funding") is not None else "–",
         ("Shorts zahlen" if (c.get("funding") or 0) < 0 else "Longs zahlen") if c.get("funding") is not None else ""),
        ("Marktkap.", mio(c.get("mcap")), f"Spot-Anteil {de(c['spot_anteil'], 0)} %" if c.get("spot_anteil") is not None else ""),
        ("Wale", f"{de(w['wal'])} %" if w.get("wal") is not None else "–",
         f"auf Börsen {de(w['boerse'])} %" if w.get("boerse") is not None else ""),
    ]
    kb, y0 = (W - 160 - 3 * 20) / 4, 826
    for i, (titel, wert, unter) in enumerate(kacheln):
        x0 = 80 + i * (kb + 20)
        karte(img, th, (x0, y0, x0 + kb, y0 + 150), radius=22)
        dr = ImageDraw.Draw(img)
        dr.text((x0 + 18, y0 + 16), titel, font=font("Medium", 22), fill=th.neben)
        fwert = font("Bold", 34)
        while dr.textlength(wert, font=fwert) > kb - 30 and fwert.size > 20:
            fwert = font("Bold", fwert.size - 2)
        dr.text((x0 + 18, y0 + 52), wert, font=fwert, fill=th.text)
        dr.text((x0 + 18, y0 + 104), unter, font=font("Medium", 20), fill=th.akzent)
    y = y0 + 180
    if termin.get("text"):
        y = absatz(dr, th, 80, y, "Termin: " + termin["text"], W - 160, groesse=26, farbe=th.akzent2,
                   gewicht="SemiBold") + 6
    punkte(dr, th, 80, y, d["punkte"], W - 160, groesse=27, bis_y=H - 110)
    fuss(img, th, cfg["hinweise"]["fusszeile"] + " · Daten: Börsen, Bot")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel
