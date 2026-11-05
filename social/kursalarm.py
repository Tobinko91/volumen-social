"""Kurs-Alarm (Wunsch Tobias 05.11.2026, Anlass Crash 05.11.): Bewegt sich BTC oder ETH in 60 Minuten um mindestens
4 %, baut der Server sofort eine Eilmeldung (Bild + Reel mit echtem Chart und Stimme) und schickt sie zur Freigabe.
Kurse nur aus echten Bitunix-Kerzen (nie aus Web-Seiten). Das Warum liefert die Redaktion danach (Hot Topic).
Hoechstens ein Alarm je Coin und Richtung in 3 Stunden."""
from __future__ import annotations

import html
import json
import time
from pathlib import Path

SCHWELLE = 4.0
SPERRE_S = 3 * 3600
COINS = ("BTC", "ETH")


def bewegung(k: list[dict]) -> dict | None:
    """15-Min-Kerzen: Veraenderung der letzten 60 Minuten (4 Kerzen) und 24 Std. (96 Kerzen)."""
    if len(k) < 5:
        return None
    jetzt, vor1h = k[-1]["c"], k[-5]["c"]
    vor24 = k[-97]["c"] if len(k) >= 97 else k[0]["c"]
    return {"jetzt": jetzt, "chg1h": (jetzt / vor1h - 1) * 100, "chg24": (jetzt / vor24 - 1) * 100,
            "ts": k[-1]["t"] // 1000, "ab_ts": k[-5]["t"] // 1000}


def pruefen(kerzen_holen, stand: dict, jetzt: float | None = None) -> list[dict]:
    """-> Alarme [{base, jetzt, chg1h, chg24, ...}], stand wird aktualisiert."""
    jetzt = jetzt or time.time()
    out = []
    for b in COINS:
        try:
            m = bewegung(kerzen_holen(b, "15m", 100))
        except Exception:
            m = None
        if not m or abs(m["chg1h"]) < SCHWELLE:
            continue
        key = f"{b}_{'hoch' if m['chg1h'] > 0 else 'runter'}"
        if key in stand and jetzt - stand[key] < SPERRE_S:
            continue
        stand[key] = jetzt
        out.append(dict(m, base=b))
    return out


def _pr(x: float) -> str:
    return f"${x:,.0f}" if x >= 100 else f"${x:,.2f}"


def bauen(alarme: list[dict], ordner_basis: Path, cfg: dict, jetzt: float | None = None) -> tuple[Path, Path]:
    """Bild-Ordner und Reel-Ordner (reel.json, Server spricht + Chart). -> (bild_ordner, reel_ordner)."""
    import datetime as dt
    from PIL import ImageDraw
    from . import design
    from .design import absatz, etikett, font, fuss, hintergrund, karte, marke, thema_waehlen, ueberschrift, rgb
    from .sprache import hinweis
    jetzt = jetzt or time.time()
    t = dt.datetime.fromtimestamp(jetzt, dt.timezone.utc)
    stempel = time.strftime("%Y%m%d-%H%M", time.localtime(jetzt))
    th = thema_waehlen("markt", f"alarm-{stempel}")
    a0 = max(alarme, key=lambda a: abs(a["chg1h"]))
    runter = a0["chg1h"] < 0
    farbe = th.minus if runter else th.plus
    wort = "DROP" if runter else "JUMP"
    kopf = f"{a0['base']} {'drops' if runter else 'jumps'} {abs(a0['chg1h']):.1f}% in one hour"
    zeit = f"{t:%H:%M} UTC"
    hw = hinweis(cfg, "en")
    bo = ordner_basis / f"{stempel}_redaktion_alarm"
    bo.mkdir(parents=True, exist_ok=True)
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=41)
    marke(img, th, 80, 64, 64, untertitel=f"{t:%b} {t.day}, {zeit}")
    d = ImageDraw.Draw(img)
    etikett(d, th, 80, 170, f"BREAKING · PRICE {wort}", farbe=farbe)
    y = ueberschrift(d, th, 80, 250, kopf, W - 160, groesse=60, max_zeilen=2) + 30
    for a in alarme:
        karte(img, th, (60, y, W - 60, y + 230))
        d = ImageDraw.Draw(img)
        d.text((96, y + 24), a["base"], font=font("Bold", 40), fill=th.text)
        d.text((96, y + 80), f"{a['chg1h']:+.1f}% in 1 hour", font=font("Bold", 62), fill=th.minus if a["chg1h"] < 0
               else th.plus)
        d.text((96, y + 160), f"Now {_pr(a['jetzt'])} · 24h {a['chg24']:+.1f}%", font=font("Medium", 32), fill=th.neben)
        y += 250
    absatz(d, th, 80, y + 10, "Why it happened: analysis follows.", W - 160, groesse=34, farbe=th.akzent,
           gewicht="Bold")
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    img.convert("RGB").save(bo / "post.png")
    zeilen = [f"{a['base']}: {a['chg1h']:+.1f}% in one hour, now {_pr(a['jetzt'])} (24h: {a['chg24']:+.1f}%)."
              for a in alarme]
    e = lambda s: html.escape(s, quote=False)
    (bo / "post_telegram.txt").write_text("\n".join(
        [f"🚨 <b>{e(kopf)}</b>", "", e(f"{t:%a, %b} {t.day}, {zeit}:"), ""] + [f"• {e(z)}" for z in zeilen]
        + ["", e("Why it happened: our analysis follows."), "", f"<i>{e(hw)}</i>"]), encoding="utf-8")
    x = "\n".join([f"🚨 {kopf}", *zeilen, "Analysis follows.", hw])
    (bo / "post_x.txt").write_text(x[:280], encoding="utf-8")
    # Reel: Kopf, echter Chart mit Prozent seit Beginn der Bewegung, Kommentar-Frage
    ro = ordner_basis / f"{stempel}_redaktion_alarm_video"
    ro.mkdir(parents=True, exist_ok=True)
    W, H = 1080, 1920
    szenen = []
    for i, (etik, k) in enumerate((("BREAKING", kopf), ("THE CHART", f"{a0['base']} · last hours"),
                                   ("WHAT NOW?", "Panic or overreaction?"))):
        img = hintergrund(th, W, H, saat=80 + i)
        marke(img, th, 80, 90, 72)
        d = ImageDraw.Draw(img)
        etikett(d, th, 80, 230, etik, farbe=farbe)
        ueberschrift(d, th, 80, 320, k, W - 160, groesse=74, max_zeilen=3)
        fuss(img, th, cfg["hinweise"]["fusszeile"])
        img.convert("RGB").save(ro / f"szene_{i}.png")
    szenen = [
        {"bild": "szene_0.png", "text": f"Breaking: {kopf}. It now trades at {_pr(a0['jetzt'])}."},
        {"bild": "szene_1.png", "text": f"Here is the real chart. {a0['base']} is {{chg}} since the move started.",
         "text_ohne": f"Here is how {a0['base']} traded in the last hours.",
         "chart": {"base": a0["base"], "intervall": "15m", "anzahl": 48, "box": [60, 620, 1020, 1400],
                   "titel": f"{a0['base']} · 15m", "ab_ts": a0["ab_ts"], "ab_text": "the move"}},
        {"bild": "szene_2.png", "text": "We are checking why. Panic or overreaction? Comment below."},
    ]
    (ro / "reel.json").write_text(json.dumps({"thema": f"alarm-{stempel}", "szenen": szenen}), encoding="utf-8")
    for f in ("post_telegram.txt", "post_x.txt"):
        (ro / f).write_text((bo / f).read_text(encoding="utf-8"), encoding="utf-8")
    (ro / "post.png").write_bytes((ro / "szene_0.png").read_bytes())
    return bo, ro
