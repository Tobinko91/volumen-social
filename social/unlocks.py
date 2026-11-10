"""S22 „Frühere Unlocks“ (Wunsch Tobias 03.11.2026) + S26 Nachfolge-Reels (06.11.2026).

Daten: /opt/volumen-bot/web/unlock_historie.json (Bot 9.26 / 9.32), eintraege[] je kommendem bzw. vergangenem Unlock:
  base, unlock_ts, zeit_offen, pct, basis (umlauf|marktwert|menge), usd_mio, groesse_vergleich, nach7_median,
  muster[], vergangen[{ts, vor10, nach7, kurve[[tag, %]]}], jetzt[[tag, %]], erstmals, folge (tag1|tag7), nachher{...}.
Kurven sind auf den Kurs 10 Tage vor dem jeweiligen Unlock normiert (0 % = Start), Tag 0 = Unlock.

Eigenes Format: andere Kanaele nie nennen. Ehrlich: Fallzahl immer nennen, keine Vorhersage, kein Kauf-/Verkaufsaufruf,
im Nachfolge-Reel auch sagen, wenn es anders kam („History didn't repeat this time.“).
"""
from __future__ import annotations

import html
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

BASIS_EN = {"umlauf": "OF CIRCULATING", "marktwert": "OF MARKET CAP", "menge": "OF SUPPLY"}


def laden(ordner: Path) -> list[dict]:
    try:
        return json.loads((Path(ordner) / "unlock_historie.json").read_text(encoding="utf-8")).get("eintraege") or []
    except Exception:
        return []


def schluessel(e: dict) -> str:
    return f"{e['base'].upper()}-{int(e['unlock_ts'])}"


def _pz(x: float, d: int = 1) -> str:
    return f"{x:+.{d}f}%".replace("-", "−")


def geschichte(e: dict) -> dict | None:
    """Frühere Unlocks: Anzahl, wie oft danach gefallen, Median 7 Tage danach, wie oft davor gestiegen."""
    v = [x for x in e.get("vergangen") or [] if x.get("nach7") is not None]
    if not v:
        return None
    n7 = [x["nach7"] for x in v]
    v10 = [x["vor10"] for x in v if x.get("vor10") is not None]
    return {"n": len(v), "gefallen": sum(1 for x in n7 if x < 0), "median7": statistics.median(n7),
            "min7": min(n7), "max7": max(n7), "vor_hoch": sum(1 for x in v10 if x > 0), "vor_n": len(v10)}


def gross(e: dict) -> bool:
    return (e.get("pct") or 0) >= 5 or (e.get("groesse_vergleich") or 0) >= 3


def kandidat(e: dict) -> str | None:
    """S22-Regeln: 'muster' | 'gemischt' (gross, Geschichte ohne klares Muster) | 'kurz' (gross, keine Geschichte)."""
    if e.get("muster") and geschichte(e):
        return "muster"
    if gross(e):
        return "gemischt" if geschichte(e) else "kurz"
    return None


def termin(e: dict) -> str:
    t = datetime.fromtimestamp(e["unlock_ts"], timezone.utc)
    return t.strftime("%b %-d") + ("" if e.get("zeit_offen") else t.strftime(" %H:%M UTC"))


def texte(e: dict, cfg: dict) -> dict:
    from .sprache import hinweis
    hw = hinweis(cfg, "en")
    b, g, art = e["base"], geschichte(e), kandidat(e)
    groesse = f"{e['pct']:.1f}% {BASIS_EN.get(e.get('basis'), 'OF SUPPLY').lower()}" if e.get("pct") else ""
    kopf = f"${b} unlock on {termin(e)}" + (f": {groesse}" if groesse else "")
    tag = datetime.fromtimestamp(e["unlock_ts"], timezone.utc).strftime("%B %-d")
    zeilen, sprech = [], [f"{b} unlocks {groesse.replace('of ', 'of its ') if groesse else 'new tokens'} on {tag}."]
    if g:
        if g["gefallen"] == g["n"]:
            f = f"In {g['n']} of the last {g['n']} {b} unlocks, price fell in the 7 days after, median {_pz(g['median7'])}."
        elif g["gefallen"] == 0:
            f = f"In {g['n']} of the last {g['n']} {b} unlocks, price rose in the 7 days after, median {_pz(g['median7'])}."
        else:
            f = (f"History is mixed: after {g['gefallen']} of the last {g['n']} {b} unlocks price fell within "
                 f"7 days, median {_pz(g['median7'])}.")
        zeilen.append(f)
        sprech.append(f)
        if g["vor_n"]:
            zeilen.append(f"In the 10 days before: {g['vor_hoch']} rises, {g['vor_n'] - g['vor_hoch']} drops.")
            sprech.append(zeilen[-1])
    if (e.get("groesse_vergleich") or 0) >= 3:
        zeilen.append(f"This unlock is about {e['groesse_vergleich']:.0f} times bigger than the previous ones.")
        sprech.append(zeilen[-1])
    if e.get("usd_mio"):
        zeilen.append(f"Value: about ${e['usd_mio']:.1f}M.")
    frage = "Will history repeat? Comment below." if g else "Watch the unlock date. Comment below."
    sprech.append(frage)
    x = "\n".join([f"🔓 {kopf}", *zeilen[:2], frage, hw])
    if len(x) > 280:
        x = "\n".join([f"🔓 {kopf}", zeilen[0] if zeilen else "", frage, hw])
    esc = lambda s: html.escape(s, quote=False)
    tg = [f"🔓 <b>{esc(kopf)}</b>", ""] + [f"• {esc(z)}" for z in zeilen]
    if g:
        tg += ["", "<b>Previous unlocks · 10D before · 7D after</b>"]
        for v in e["vergangen"]:
            d = datetime.fromtimestamp(v["ts"], timezone.utc).strftime("%b %-d, %Y")
            tg.append(f"• {d}: {_pz(v.get('vor10') or 0)} · {_pz(v['nach7'])}")
        tg.append(esc(f"Only {g['n']} cases, no rule."))
    tg += ["", esc(frage), "", f"<i>{esc(hw)}</i>"]
    return {"kopf": kopf, "x": x, "telegram": "\n".join(tg), "sprech": sprech, "art": art}


# ---------------------------------------------------------------- Grafik

def _chart(img, th, box, e: dict, jetzt_linie: bool = True, titel: str = ""):
    from .design import font, karte, rgb
    karte(img, th, box)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    px0, px1, py0, py1 = x0 + 70, x1 - 30, y0 + 60, y1 - 50
    kurven = [v.get("kurve") or [] for v in e.get("vergangen") or []]
    jetzt = e.get("jetzt") or []
    werte = [p for k in kurven + ([jetzt] if jetzt_linie else []) for _, p in k] or [0]
    lo, hi = min(werte + [0]), max(werte + [0])
    pad = (hi - lo) * 0.08 or 5
    lo, hi = lo - pad, hi + pad
    X = lambda t: px0 + (px1 - px0) * (t + 10) / 17
    Y = lambda p: py1 - (py1 - py0) * (p - lo) / (hi - lo)
    d.text((x0 + 24, y0 + 16), titel or f"${e['base']} · price around previous unlocks (0% = 10 days before)",
           font=font("SemiBold", 24), fill=th.neben)
    for p in (lo + pad, 0, hi - pad):
        d.text((x0 + 14, Y(p) - 12), f"{p:+.0f}%", font=font("Medium", 20), fill=th.neben)
    d.line([(px0, Y(0)), (px1, Y(0))], fill=rgb(th.linie), width=1)
    gedaempft = ["#7E74B8", "#6B8FA3", "#9B7FB8", "#5E7A8F", "#8C84C8", "#6F6A9E"]
    for i, k in enumerate(kurven):
        if len(k) > 1:
            d.line([(X(t), Y(p)) for t, p in k], fill=rgb(gedaempft[i % len(gedaempft)]), width=3)
    d.line([(X(0), py0), (X(0), py1)], fill=rgb("#F2F0FF"), width=3)
    d.text((X(0) + 8, py0), "UNLOCK", font=font("Bold", 22), fill=th.text)
    for t in (-10, -5, 0, 5):
        d.text((X(t) - 18, py1 + 12), f"{t:+d}d" if t else "0", font=font("Medium", 20), fill=th.neben)
    if jetzt_linie and len(jetzt) > 1:
        d.line([(X(t), Y(p)) for t, p in jetzt], fill=rgb(th.akzent), width=6)
        t, p = jetzt[-1]
        d.text((X(t) + 10, Y(p) - 14), "NOW", font=font("Bold", 26), fill=th.akzent)


def _tabelle(img, th, box, e: dict, jetzt_text: tuple[str, str] = ("?", "?")):
    from .design import font, karte
    karte(img, th, box)
    d = ImageDraw.Draw(img)
    x0, y0, x1, _ = box
    sp = [x0 + 30, x0 + (x1 - x0) * 0.48, x0 + (x1 - x0) * 0.75]
    for s, t in zip(sp, ("UNLOCK", "10D BEFORE", "7D AFTER")):
        d.text((s, y0 + 20), t, font=font("Bold", 24), fill=th.neben)
    yy = y0 + 62
    for v in (e.get("vergangen") or [])[-5:]:
        dat = datetime.fromtimestamp(v["ts"], timezone.utc).strftime("%b %-d, %Y")
        d.text((sp[0], yy), dat, font=font("SemiBold", 32), fill=th.text)
        for s, w in zip(sp[1:], (v.get("vor10"), v.get("nach7"))):
            if w is not None:
                d.text((s, yy), _pz(w, 0), font=font("Bold", 34), fill=th.plus if w > 0 else th.minus)
        yy += 50
    d.text((sp[0], yy + 4), "NOW", font=font("Bold", 34), fill=th.akzent)
    for s, w in zip(sp[1:], jetzt_text):
        d.text((s, yy + 4), w, font=font("Bold", 34), fill=th.akzent)


def bild(e: dict, cfg: dict, ziel: Path, kopf: str, H: int = 1350) -> Path:
    from . import design
    th = design.THEMEN["nacht"]
    W = 1080
    img = design.hintergrund(th, W, H, saat=41)
    design.marke(img, th, 80, 64 if H < 1600 else 90, 64 if H < 1600 else 72)
    d = ImageDraw.Draw(img)
    y0 = 170 if H < 1600 else 230
    zeile = f"${e['base']} UNLOCK · {termin(e).upper()}" + (
        f" · {e['pct']:.1f}% {BASIS_EN.get(e.get('basis'), 'OF SUPPLY')}" if e.get("pct") else "")
    design.etikett(d, th, 80, y0, zeile, farbe=th.minus)
    g = geschichte(e)
    schlag = kopf
    if g:
        schlag = (f"The last {g['n']} {e['base']} unlocks: price fell after {g['gefallen']} of {g['n']}. This one: ?"
                  if g["gefallen"] else f"The last {g['n']} {e['base']} unlocks: price rose after all of them. This one: ?")
    y = design.ueberschrift(d, th, 80, y0 + 80, schlag, W - 160, groesse=50 if H < 1600 else 62, max_zeilen=3) + 20
    if g:
        unten = H - (130 if H < 1600 else 720)
        tab_h = 62 + 50 * min(5, len(e["vergangen"])) + 70
        _chart(img, th, (60, y, W - 60, unten - tab_h - 20), e)
        vor = (e.get("jetzt_seit_start"))
        _tabelle(img, th, (60, unten - tab_h, W - 60, unten), e,
                 (_pz(vor, 0) if vor is not None else "?", "?"))
    else:
        d = ImageDraw.Draw(img)
        f = design.font("Bold", 150)
        txt = f"{e['pct']:.1f}%" if e.get("pct") else termin(e)
        d.text(((W - d.textlength(txt, font=f)) / 2, y + 120), txt, font=f, fill=th.minus)
        unter = " · ".join(z for z in (BASIS_EN.get(e.get("basis"), "").lower() if e.get("pct") else "",
                                        f"~${e['usd_mio']:.1f}M" if e.get("usd_mio") else "",
                                        "first unlock we track" if not e.get("vergangen") else "") if z)
        fu = design.font("SemiBold", 40)
        d.text(((W - d.textlength(unter, font=fu)) / 2, y + 320), unter, font=fu, fill=th.neben)
    design.fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel


# ---------------------------------------------------------------- S26 Nachfolge

def nachfolge_texte(e: dict, cfg: dict) -> dict:
    """Reel „24h after“ / „7 days later“. Ehrlicher Vergleich mit dem, was die Geschichte nahelegte."""
    from .sprache import hinweis
    hw = hinweis(cfg, "en")
    b, n, g = e["base"], e.get("nachher") or {}, geschichte(e)
    tag7 = e.get("folge") == "tag7"
    wert = n.get("tag7") if tag7 else n.get("tag1")
    kopf = f"${b}: {'7 days' if tag7 else '24h'} after the unlock"
    sprech = [f"We asked: pump first or straight down? Here is what {b} actually did."]
    zahlen = []
    if n.get("vor10") is not None:
        zahlen.append(f"10 days before: {_pz(n['vor10'])}")
    if wert is not None:
        zahlen.append(f"{'7 days' if tag7 else '24h'} after: {_pz(wert)}")
    if n.get("tief") is not None:
        zahlen.append(f"lowest point: {_pz(n['tief'])}")
    if zahlen:
        sprech.append(". ".join(z[0].upper() + z[1:] for z in zahlen) + ".")
    if g and wert is not None:
        richtung_hist = "fell" if g["gefallen"] * 2 > g["n"] else "rose" if g["gefallen"] * 2 < g["n"] else None
        if richtung_hist:
            gleich = (wert < 0) == (richtung_hist == "fell")
            sprech.append(f"Our data said: price {richtung_hist} after {g['gefallen'] if richtung_hist == 'fell' else g['n'] - g['gefallen']}"
                          f" of {g['n']} previous unlocks. " + ("This time it did too." if gleich
                                                                 else "History didn't repeat this time."))
    sprech.append("Follow for the next unlock check.")
    x = "\n".join([f"🔓 {kopf}", " · ".join(zahlen), sprech[2] if len(sprech) > 3 else "", hw]).replace("\n\n", "\n")
    esc = lambda s: html.escape(s, quote=False)
    tg = "\n".join([f"🔓 <b>{esc(kopf)}</b>", ""] + [f"• {esc(z)}" for z in zahlen]
                   + ["", esc(" ".join(sprech[2:-1])), "", f"<i>{esc(hw)}</i>"])
    return {"kopf": kopf, "x": x[:280], "telegram": tg, "sprech": sprech}


def nachfolge_bild(e: dict, cfg: dict, ziel: Path, kopf: str, H: int = 1920) -> Path:
    from . import design
    th = design.THEMEN["nacht"]
    W = 1080
    img = design.hintergrund(th, W, H, saat=43)
    design.marke(img, th, 80, 90, 72)
    d = ImageDraw.Draw(img)
    design.etikett(d, th, 80, 230, f"${e['base']} UNLOCK · WHAT HAPPENED", farbe=th.akzent2)
    y = design.ueberschrift(d, th, 80, 310, kopf, W - 160, groesse=64, max_zeilen=2) + 20
    n = e.get("nachher") or {}
    vor = n.get("vor10")
    wert = n.get("tag7") if e.get("folge") == "tag7" else n.get("tag1")
    unten = H - 720
    tab_h = 62 + 50 * min(5, len(e.get("vergangen") or [])) + 70
    _chart(img, th, (60, y, W - 60, unten - tab_h - 20), e)
    _tabelle(img, th, (60, unten - tab_h, W - 60, unten), e,
             (_pz(vor, 0) if vor is not None else "–",
              (_pz(wert, 0) + ("" if e.get("folge") == "tag7" else " 24h")) if wert is not None else "–"))
    design.fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel


# ---------------------------------------------------------------- Auswahl (alle 10 Min. aus live.sh)

def auswahl(eintraege: list[dict], stand: dict, jetzt: float, sperr: set, schon: list | None = None) -> list[tuple]:
    """-> [(art, eintrag)] mit art in post | tag1 | tag7. Ruhezeit 22-7 Uhr, je Unlock hoechstens 1 Post und
    2 Nachfolger; tag7 nur, wenn tag1 gepostet wurde oder |tag7| >= 10 %."""
    from zoneinfo import ZoneInfo
    stunde = datetime.fromtimestamp(jetzt, ZoneInfo("Europe/Berlin")).hour
    if stunde >= 22 or stunde < 7:
        return []
    gepostet = stand.setdefault("gepostet", {})
    for b in schon or []:   # z. B. ALLO (S25 aus dem Redaktions-Chat)
        for e in eintraege:
            if e["base"].upper() == b.upper():
                gepostet.setdefault(schluessel(e), ["post"])
    out = []
    for e in eintraege:
        if e["base"].upper() in sperr:
            continue
        k = schluessel(e)
        schon_k = gepostet.get(k, [])
        if e["unlock_ts"] > jetzt and "post" not in schon_k and kandidat(e):
            out.append(("post", e))
        elif e.get("folge") in ("tag1", "tag7") and "post" in schon_k and e["folge"] not in schon_k:
            if e["folge"] == "tag1" or "tag1" in schon_k or abs((e.get("nachher") or {}).get("tag7") or 0) >= 10:
                out.append((e["folge"], e))
    return out


def merken(stand: dict, art: str, e: dict) -> None:
    stand.setdefault("gepostet", {}).setdefault(schluessel(e), []).append(art)
