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
            k = kerzen_holen(b, "15m", 100)
            m = bewegung(k)
            if m:
                m["kerzen"] = k[-48:]   # fuer den Chart im Bild (08.11.2026)
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
    y = absatz(d, th, 80, y + 10, "Panic or overreaction? Comment below.", W - 160, groesse=34, farbe=th.akzent,
               gewicht="Bold")
    if a0.get("kerzen") and len(a0["kerzen"]) >= 12 and y < 1000:   # echter Chart statt leerer Flaeche (08.11.2026)
        from . import grafik
        grafik.echt_chart(img, th, (60, y + 30, W - 60, 1240), a0["kerzen"], "linie", {}, 3, "en",
                          f"{a0['base']} · 15m · last 12 hours")
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    img.convert("RGB").save(bo / "post.png")
    zeilen = [f"{a['base']}: {a['chg1h']:+.1f}% in one hour, now {_pr(a['jetzt'])} (24h: {a['chg24']:+.1f}%)."
              for a in alarme]
    e = lambda s: html.escape(s, quote=False)
    (bo / "post_telegram.txt").write_text("\n".join(
        [f"🚨 <b>{e(kopf)}</b>", "", e(f"{t:%a, %b} {t.day}, {zeit}:"), ""] + [f"• {e(z)}" for z in zeilen]
        + ["", e("Panic or overreaction? Comment below."), "", f"<i>{e(hw)}</i>"]), encoding="utf-8")
    x = "\n".join([f"🚨 {kopf}", *zeilen, "Panic or overreaction?", hw])
    (bo / "post_x.txt").write_text(x[:280], encoding="utf-8")
    # Reel: Kopf mit grosser Zahl, echter Chart (6 Std. Vorgeschichte, Prozent seit Beginn der Bewegung), Frage.
    # 08.11.2026 Tobias: kein leeres Bild mehr. Jede Szene traegt Zahlen; der Chart liegt ueber einer Zahlen-Karte,
    # die nur sichtbar bleibt, wenn keine Kurse kommen.
    ro = ordner_basis / f"{stempel}_redaktion_alarm_video"
    ro.mkdir(parents=True, exist_ok=True)
    W, H = 1080, 1920
    chg = f"{a0['chg1h']:+.1f}%".replace("-", "−")
    chg24 = f"{a0['chg24']:+.1f}%".replace("-", "−")

    def gross(img, y, text, fa, g=230):
        d = ImageDraw.Draw(img)
        f = font("Bold", g)
        d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fa)

    def kachel(img, y, zeilen_):
        karte(img, th, (60, y, W - 60, y + 110 * len(zeilen_) + 50))
        d = ImageDraw.Draw(img)
        for j, (l, w_, fa) in enumerate(zeilen_):
            d.text((110, y + 40 + j * 110), l, font=font("SemiBold", 40), fill=th.neben)
            f = font("Bold", 60)
            d.text((W - 110 - d.textlength(w_, font=f), y + 28 + j * 110), w_, font=f, fill=fa)

    for i, (etik, k) in enumerate((("BREAKING", f"{a0['base']} in one hour"), ("THE CHART", f"{a0['base']} · last 7 hours"),
                                   ("WHAT NOW?", "Panic or overreaction?"))):
        img = hintergrund(th, W, H, saat=80 + i)
        marke(img, th, 80, 90, 72)
        d = ImageDraw.Draw(img)
        etikett(d, th, 80, 230, etik, farbe=farbe)
        ueberschrift(d, th, 80, 320, k, W - 160, groesse=74, max_zeilen=3)
        if i == 0:
            gross(img, 560, chg, farbe)
            kachel(img, 880, [("Now", _pr(a0["jetzt"]), th.text), ("24 hours", chg24, th.minus if a0["chg24"] < 0
                                                                     else th.plus)])
        elif i == 1:   # Zahlen unter dem Chart (Chart-Box 520..1100), bleiben auch ohne Kurse stehen
            kachel(img, 1130, [("1 hour", chg, farbe), ("Now", _pr(a0["jetzt"]), th.text)])
        else:
            kachel(img, 620, [("1 hour", chg, farbe), ("24 hours", chg24, th.minus if a0["chg24"] < 0 else th.plus)])
        fuss(img, th, cfg["hinweise"]["fusszeile"])
        img.convert("RGB").save(ro / f"szene_{i}.png")
    szenen = [
        {"bild": "szene_0.png", "text": f"Breaking: {a0['base']} {chg} in one hour. It now trades at {_pr(a0['jetzt'])}."},
        {"bild": "szene_1.png", "text": f"Here is the real chart. {a0['base']} is {{chg}} since the move started.",
         "text_ohne": f"Over 24 hours {a0['base']} is {chg24}.",
         "chart": {"base": a0["base"], "intervall": "5m", "anzahl": 100, "box": [60, 520, 1020, 1100],
                   "titel": f"{a0['base']} 5m", "ab_ts": a0["ab_ts"], "ab_text": "the move",
                   "vorlauf_h": 6, "zahl_ab_ereignis": True}},
        {"bild": "szene_2.png", "text": f"Over 24 hours: {chg24}. Panic or overreaction? Comment below."},
    ]
    (ro / "reel.json").write_text(json.dumps({"thema": f"alarm-{stempel}", "szenen": szenen}), encoding="utf-8")
    for f in ("post_telegram.txt", "post_x.txt"):
        (ro / f).write_text((bo / f).read_text(encoding="utf-8"), encoding="utf-8")
    (ro / "post.png").write_bytes((ro / "szene_0.png").read_bytes())
    return bo, ro
