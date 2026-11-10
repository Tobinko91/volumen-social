"""S29 Reihe „The textbook is WRONG“ (Wunsch Tobias 10.11.2026): 1 Video pro Woche, im Wechsel mit S27.

Bekannte Lehrbuch-Regeln mit echten Daten widerlegt. Daten: /opt/volumen-bot/web/muster_des_tages.json →
`lehrbuch_falsch[]` (Bot 9.38): je Formation das juengste echte Beispiel, bei dem es gegen das Lehrbuch lief, mit
`muster, name_en, lehrbuch, coin, kerzen_vorher, kerzen_nachher, ergebnis{r1,r3,r6}, statistik{n, treffer_pct,
zufall_pct, vorsprung_pp}`. Folgen in fester Reihenfolge (config `lehrbuch.reihe`), danach der Abschluss
„The ONE pattern that actually works: the Hammer“ (braucht die Hammer-Statistik, sonst entfaellt er).

Aufbau (25–35 s): Lehrbuch-Behauptung → echtes Beispiel, bei dem es falsch lief → Jahreszahl gegen Zufall →
Erklaerung in einem Satz → „Follow for the next myth“. Regeln: immer Fallzahl und Zufall nennen, keine Kauf-/
Verkaufsaufforderung, „Not financial advice.“ Zeichnen wie S27 (formation.bild).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import formation
from .formation import _pz

REIHE = ["double_top", "range_breakdown", "double_bottom", "three_white_soldiers"]
ABSCHLUSS = "hammer"
# Behauptung (Lehrbuch) und ein Satz Erklaerung je Formation; vorsichtig formuliert („one likely reason“)
TEXTE = {
    "double_top": ("Everyone sells the Double Top.", "One likely reason: by the time it's obvious, the sellers are "
                   "already out."),
    "range_breakdown": ("The breakdown is a classic sell signal.", "One likely reason: many breakdowns get bought "
                        "back fast."),
    "double_bottom": ("The famous W bottom is supposed to rise.", "One likely reason: many W bottoms are just a "
                      "pause in a downtrend."),
    "three_white_soldiers": ("Three green candles in a row. The textbook says: more to come.",
                             "One likely reason: after three green candles, the easy move is often over."),
}


def _schluessel(e: dict) -> str:
    return str(e.get("muster") or e.get("name_en", "")).lower().replace(" ", "_").replace("-", "_")


def laden(web_dir: str | Path) -> dict:
    """-> {muster: Beispiel} aus lehrbuch_falsch[] (nur vollstaendige) plus 'statistik_alle', falls vorhanden."""
    try:
        d = json.loads((Path(web_dir) / "muster_des_tages.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    aus = {}
    for e in d.get("lehrbuch_falsch") or []:
        s = e.get("statistik") or {}
        if (e.get("kerzen_vorher") and len(e.get("kerzen_nachher") or []) >= 6 and (e.get("ergebnis") or {})
                .get("r6") is not None and s.get("n") and s.get("treffer_pct") is not None
                and s.get("zufall_pct") is not None):
            aus[_schluessel(e)] = e
    # Hammer-Statistik fuer den Abschluss: als Eintrag in lehrbuch_falsch, in statistik_alle oder als Tagesmuster
    alle = {str(k).lower(): v for k, v in (d.get("statistik_alle") or {}).items()}
    if _schluessel(d) == ABSCHLUSS and d.get("statistik"):
        alle.setdefault(ABSCHLUSS, d["statistik"])
    if ABSCHLUSS in aus:
        alle.setdefault(ABSCHLUSS, aus[ABSCHLUSS]["statistik"])
    aus["_statistik"] = alle
    return aus


def naechste(daten: dict, erledigt: list[str], reihe: list[str] | None = None) -> str | None:
    """Naechste Folge: erste Formation der Reihe, die noch fehlt und Daten hat; danach der Hammer-Abschluss."""
    reihe = reihe or REIHE
    for m in reihe:
        if m not in erledigt:
            return m if m in daten else None   # Reihenfolge halten: fehlt das Beispiel, diese Woche keine Folge
    if ABSCHLUSS not in erledigt and (daten.get("_statistik") or {}).get(ABSCHLUSS):
        return ABSCHLUSS
    return None


def _zahl(s: dict) -> tuple[float, float, float]:
    t, z = float(s["treffer_pct"]), float(s["zufall_pct"])
    return t, z, float(s.get("vorsprung_pp", t - z))


def texte(e: dict) -> dict:
    """Sprechtext je Szene + X-Text fuer eine Mythos-Folge."""
    m = _schluessel(e)
    name, coin, s = e["name_en"], e["coin"], e["statistik"]
    runter = e["lehrbuch"] == "down"
    behaupt, grund = TEXTE.get(m, (f"The textbook loves the {name}.", ""))
    t, z, vor = _zahl(s)
    richtung = "fell" if runter else "rose"
    urteil = "Worse than random." if vor <= -2 else "No real edge."
    zeilen = [
        f"{behaupt} The textbook says price {'falls' if runter else 'rises'} next.",
        f"Here is a real {name} on {coin}, 4 hour chart.",
        f"{coin} moved {_pz(e['ergebnis']['r6'])} in 24 hours. The textbook was wrong.",
        f"And it's not just this one. Across {int(s['n']):,} cases in one year, price {richtung} after a {name} "
        f"{t:.1f}% of the time. With no pattern at all: {z:.1f}%. {urteil}",
    ]
    if grund:
        zeilen.append(grund)
    zeilen.append("Follow for the next myth.")
    x = (f"The textbook is WRONG: {name} 📉\n{int(s['n']):,} cases in one year: price {richtung} after it "
         f"{t:.1f}% of the time. No pattern at all: {z:.1f}%.\nReal example: ${coin} {_pz(e['ergebnis']['r6'])} "
         f"in 24h.\nNot financial advice.")
    return {"zeilen": zeilen, "x": x[:280], "urteil": urteil}


def szenen(e: dict, ordner: Path) -> tuple[list, dict]:
    from . import design
    th = design.THEMEN["nacht"]
    ordner.mkdir(parents=True, exist_ok=True)
    tx = texte(e)
    s, name = e["statistik"], e["name_en"]
    t, z, vor = _zahl(s)
    runter = e["lehrbuch"] == "down"
    bild = formation.bild

    def sp(img, n):
        p = ordner / f"{n}.png"
        img.convert("RGB").save(p)
        return p

    lb = "price falls next" if runter else "price rises next"
    folgen = [
        [(sp(bild(e, 0, "The textbook says", f"{name} → {lb}", markieren=False, saat=11), "behauptung"), 1.5)],
        [(sp(bild(e, 0, "The textbook says", f"{name} → {lb}", saat=11), "beispiel"), 1.2),
         (sp(bild(e, 0, "The textbook says", f"{name} → {lb}", pfeile=False, saat=11,
                  gross=(f"${e['coin']} · real chart", th.akzent2)), "beispiel_coin"), 1.0)],
        [(sp(bild(e, n, "What really happened", "the next 24 hours", saat=11), f"nach_{n}"), 0.45)
         for n in range(1, 7)]
        + [(sp(bild(e, 6, "Textbook: WRONG", f"It said: {lb}",
                    gross=(f"{_pz(e['ergebnis']['r6'])} in 24h", th.plus if e['ergebnis']['r6'] >= 0 else th.minus),
                    saat=11), "falsch"), 1.6)],
        [(sp(bild(e, 6, "Not just this one", "one year of data", markieren=False, saat=11, karte_zeilen=[
            (f"{name}: {int(s['n']):,} cases", th.text),
            (f"Price {'fell' if runter else 'rose'} after it: {t:.1f}%", th.text),
            (f"With no pattern at all: {z:.1f}%", th.akzent2),
            (f"→ {tx['urteil'].rstrip('.').lower()} ({vor:+.1f} pts)".replace("-", "−"), th.minus)]), "zahl"), 5.0)],
    ]
    if len(tx["zeilen"]) == 6:
        folgen.append([(sp(bild(e, 6, "Why?", "", markieren=False, saat=11, karte_zeilen=[
            ("One likely reason:", th.akzent), *[(z_, th.text) for z_ in _umbruch(tx["zeilen"][4][19:], 34)]]),
                           "warum"), 3.0)])
    folgen.append([(sp(bild(e, 6, "Next week: new myth", "The textbook is WRONG · series", markieren=False, saat=11,
                            gross=("Follow", th.akzent)), "folgen"), 2.0)])
    return folgen, tx


def _umbruch(t: str, breite: int) -> list[str]:
    t = t[:1].upper() + t[1:]
    zeilen, z = [], ""
    for w in t.split():
        if len(z) + len(w) + 1 > breite and z:
            zeilen.append(z)
            z = w
        else:
            z = f"{z} {w}".strip()
    return zeilen + ([z] if z else [])


# ---------------------------------------------------------------- Abschluss: der Hammer

def abschluss_texte(s: dict) -> dict:
    t, z, vor = _zahl(s)
    zeilen = ["Four famous patterns, four myths. So does anything work?",
              f"Yes, one. The Hammer. Across {int(s['n']):,} cases in one year, price rose after it {t:.1f}% of the "
              f"time. With no pattern at all: {z:.1f}%.",
              "A small edge, not a guarantee. And not yet tested as a trade after fees.",
              "That's why we now test it live, in our Signal Lab. Follow to see how it does."]
    x = (f"The textbook is WRONG, mostly. One pattern held up: the Hammer.\n{int(s['n']):,} cases in one year: price "
         f"rose after it {t:.1f}% of the time. No pattern: {z:.1f}%.\nNow tested live in our Signal Lab.\n"
         "Not financial advice.")
    return {"zeilen": zeilen, "x": x[:280]}


def abschluss_szenen(s: dict, ordner: Path) -> tuple[list, dict]:
    """Ohne echten Chart (kein Gegenbeispiel noetig): Schema-Hammer + Zahlen-Karten."""
    from PIL import ImageDraw
    from . import design
    from .design import font, rgb
    th = design.THEMEN["nacht"]
    ordner.mkdir(parents=True, exist_ok=True)
    tx = abschluss_texte(s)
    t, z, vor = _zahl(s)
    W, H = formation.W, formation.H

    def bild_(titel, unter, zeilen, hammer=False):
        img = design.hintergrund(th, W, H, saat=12)
        design.marke(img, th, 80, 90, 72)
        d = ImageDraw.Draw(img)
        f = font("Bold", 86)
        d.text(((W - d.textlength(titel, font=f)) / 2, 260), titel, font=f, fill=th.text)
        fu = font("SemiBold", 40)
        d.text(((W - d.textlength(unter, font=fu)) / 2, 380), unter, font=fu, fill=th.neben)
        if hammer:   # Schema, beschriftet
            cx = W // 2
            d.line([(cx, 560), (cx, 1060)], fill=rgb(th.plus), width=10)
            d.rectangle([cx - 60, 560, cx + 60, 680], fill=rgb(th.plus))
            fs = font("Medium", 30)
            d.text(((W - d.textlength("Schema", font=fs)) / 2, 1090), "Schema", font=fs, fill=th.neben)
        yy = 1200 if hammer else 560
        for j, (txt, farbe, gr) in enumerate(zeilen):
            fz = font("Bold", gr)
            d.text(((W - d.textlength(txt, font=fz)) / 2, yy), txt, font=fz, fill=farbe)
            yy += int(gr * 1.35)
        design.fuss(img, th, "Not financial advice.")
        return img

    def sp(img, n):
        p = ordner / f"{n}.png"
        img.convert("RGB").save(p)
        return p

    folgen = [
        [(sp(bild_("4 patterns, 4 myths", "The textbook is WRONG · finale", [
            ("Double Top", th.minus, 64), ("Range Breakdown", th.minus, 64), ("Double Bottom", th.minus, 64),
            ("Three White Soldiers", th.minus, 64), ("So does anything work?", th.akzent, 60)]), "mythen"), 2.5)],
        [(sp(bild_("The Hammer", f"{int(s['n']):,} cases · one year", [
            (f"{t:.1f}% rose after it", th.akzent, 80), (f"{z:.1f}% with no pattern", th.akzent2, 64),
            (f"{vor:+.1f} pts".replace("-", "−"), th.akzent, 110)], hammer=True), "hammer"), 5.0)],
        [(sp(bild_("A small edge", "not a guarantee", [("Not yet tested as a trade", th.text, 56),
                                                       ("after fees.", th.text, 56)]), "kante"), 2.5)],
        [(sp(bild_("Now tested live", "in our Signal Lab", [("Follow", th.akzent, 140)]), "folgen"), 2.5)],
    ]
    return folgen, tx


def video(folgen: list, tx: dict, ordner: Path, cfg: dict, geheim: dict, sprechen=None, schneiden=None):
    from . import stimme
    from . import video as _video
    sprechen = sprechen or stimme.sprechen
    schneiden = schneiden or _video.bauen
    toene, dauern, quelle = sprechen(tx["zeilen"], ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    dauern = [max(du, sum(sek for _, sek in f) + 0.2) for du, f in zip(dauern, folgen)]
    schneiden(folgen, toene, dauern, ordner / "video.mp4", cfg, texte=tx["zeilen"], untertitel_y=1590)
    return ordner / "video.mp4", quelle
