"""S23 Wochen-Post „Signal Lab · Week N“ (Wunsch Tobias 04.11.2026), montags zur Markt-Zeit.

Daten: /opt/volumen-bot/web/strategien.json (Bot 9.28). Ehrlich: Verlierer und schlechte Wochen genauso zeigen,
Fallzahl immer nennen, vor `urteil_ab` (17.11.) kein „winner“, kein Coin-Name als Kaufsignal.
„Virtual trades, fees included. Not financial advice.“
"""
from __future__ import annotations

import html
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import ImageDraw


def laden(ordner: Path) -> dict | None:
    try:
        d = json.loads((Path(ordner) / "strategien.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    return d if d.get("strategien") else None


def woche_nr(d: dict, jetzt: float) -> int:
    return max(1, int((jetzt - d["start"]) // (7 * 86400)) + 1)


def _r(x) -> str:
    return "–" if x is None else f"{x:+.2f}R".replace("-", "−")


def zeilen(d: dict) -> list[dict]:
    out = []
    for s in d["strategien"]:
        w = (s.get("wochen") or [{}])[-1]
        besser = None if s.get("r") is None or s.get("zufall_r") is None else s["r"] > s["zufall_r"]
        out.append({"name": s["name_en"], "n": s.get("n") or 0, "r": s.get("r"), "zufall": s.get("zufall_r"),
                    "besser": besser, "woche_n": w.get("n") or 0, "woche_r": w.get("r"), "woche_zufall": w.get("zufall_r"),
                    "status": s.get("status", "offen")})
    return out


def texte(d: dict, cfg: dict, jetzt: float) -> dict:
    from .sprache import hinweis
    n = woche_nr(d, jetzt)
    vor_urteil = jetzt < (d.get("urteil_ab") or 0)
    z = zeilen(d)
    kopf = f"Signal Lab · Week {n}: 4 strategies vs. random coins"
    x_z = [f"{'✅' if s['besser'] else '❌'} {s['name']} {_r(s['r'])} · random {_r(s['zufall'])} · {s['n']} trades"
           for s in z]
    schlecht = [s for s in z if s["woche_r"] is not None and s["woche_zufall"] is not None and s["woche_r"] < s["woche_zufall"]]
    satz = []
    if schlecht:
        s = min(schlecht, key=lambda s: s["woche_r"] - s["woche_zufall"])
        satz.append(f"{s['name']} lost to random this week: {_r(s['woche_r'])} vs {_r(s['woche_zufall'])}.")
    satz.append("No winner yet: too few trades for a verdict." if vor_urteil else
                "Verdict: only strategies that beat random with 30+ trades pass.")
    fuss = "Virtual trades, fees included. " + hinweis(cfg, "en")
    x = "\n".join([f"🧪 Signal Lab · Week {n}", *x_z, *satz[:1], fuss])
    if len(x) > 280:
        x = "\n".join([f"🧪 Signal Lab · Week {n}", *x_z, fuss])
    if len(x) > 280:   # nie abschneiden, lieber Zeilen weglassen
        x = "\n".join([f"🧪 Signal Lab · Week {n}", *x_z[:3], fuss])
    esc = lambda t: html.escape(t, quote=False)
    tg = [f"🧪 <b>{esc(kopf)}</b>", "", esc("Each signal is compared with 3 random coins at the same time and the "
                                            "same rules."), ""]
    for s in z:
        tg.append(f"<b>{esc(s['name'])}</b>: {esc(_r(s['r']))} vs random {esc(_r(s['zufall']))} · {s['n']} trades"
                  f" · this week {esc(_r(s['woche_r']))} ({s['woche_n']})")
    tg += ["", *[esc(t) for t in satz], "", f"<i>{esc(fuss)}</i>"]
    return {"kopf": kopf, "x": x, "telegram": "\n".join(tg), "satz": satz, "zeilen": z, "fuss": fuss}


def bild(d: dict, cfg: dict, ziel: Path, jetzt: float, H: int = 1350) -> Path:
    from . import design
    from .design import font, rgb
    th = design.THEMEN["nacht"]
    W = 1080
    tx = texte(d, cfg, jetzt)
    img = design.hintergrund(th, W, H, saat=51)
    design.marke(img, th, 80, 64 if H < 1600 else 90, 64 if H < 1600 else 72)
    dr = ImageDraw.Draw(img)
    y0 = 170 if H < 1600 else 230
    design.etikett(dr, th, 80, y0, f"SIGNAL LAB · WEEK {woche_nr(d, jetzt)}", farbe=th.akzent2)
    y = design.ueberschrift(dr, th, 80, y0 + 80, "Our live test: 4 strategies vs. random coins", W - 160,
                            groesse=54 if H < 1600 else 64, max_zeilen=2) + 30
    for s in tx["zeilen"]:
        design.karte(img, th, (60, y, W - 60, y + 170))
        dr = ImageDraw.Draw(img)
        dr.text((96, y + 18), s["name"], font=font("Bold", 38), fill=th.text)
        dr.text((96, y + 66), f"{s['n']} trades · this week {_r(s['woche_r'])} vs {_r(s['woche_zufall'])}",
                font=font("Medium", 26), fill=th.neben)
        farbe = th.plus if (s["r"] or 0) > 0 else th.minus
        fr = font("Bold", 52)
        t = _r(s["r"])
        dr.text((W - 96 - dr.textlength(t, font=fr), y + 14), t, font=fr, fill=farbe)
        z = f"random {_r(s['zufall'])} " + ("↑" if s["besser"] else "↓" if s["besser"] is False else "")
        fz = font("SemiBold", 28)
        dr.text((W - 96 - dr.textlength(z, font=fz), y + 82), z, font=fz,
                fill=th.akzent if s["besser"] else th.minus if s["besser"] is False else th.neben)
        dr.text((96, y + 112), {"besteht": "PASSED", "besteht_nicht": "FAILED"}.get(s["status"], "TESTING"),
                font=font("Bold", 24), fill={"besteht": th.akzent, "besteht_nicht": th.minus}.get(s["status"], th.akzent2))
        y += 186
    dr = ImageDraw.Draw(img)
    for t in tx["satz"]:
        y = design.absatz(dr, th, 80, y + 6, t, W - 160, groesse=30, farbe=th.text, gewicht="SemiBold")
    design.fuss(img, th, tx["fuss"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel
