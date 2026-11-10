"""S28 „Liquidity Map of the Day“ (Wunsch Tobias 09.11.2026): BTC + Coin des Tages (+ Flop) als Heatmap-Karussell
und Reel, taeglich zur Markt-Zeit. Daten: /opt/volumen-bot/web/liquidity_map_des_tages.json (Bot 9.37, ab 06:30).

Regeln: immer „estimated“, nie „target“, sondern „where liquidity sits“; keine Coinglass-Bilder (wir zeichnen aus den
Rohdaten selbst, Design „Nachtleuchten“); fehlt `top`, nur BTC; „Not financial advice.“
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from . import liquiditaet as L


def laden(ordner: Path) -> dict | None:
    p = Path(ordner) / "liquidity_map_des_tages.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return d if (d.get("btc") or {}).get("preis") else None


def _e(feld: dict, base: str) -> dict:
    e = dict(feld, base=feld.get("base") or base)
    e.setdefault("mit_liquidationen", bool(e.get("heatmap")))   # Heatmap gibt es nur mit Futures-Daten
    return e


def _naechste(e: dict) -> str:
    teile = []
    for k, wort in (("naechste_oben", "above"), ("naechste_unten", "below")):
        z = e.get(k)
        if z and abs(z.get("abstand_pct", 99)) <= L.MAX_ABSTAND:
            teile.append(f"{L.pr(z['mitte'])} ({z['abstand_pct']:+.1f}%) {wort}")
    return ", ".join(teile)


def texte(d: dict, cfg: dict) -> dict:
    from .sprache import hinweis
    hw = hinweis(cfg, "en")
    btc = _e(d["btc"], "BTC")
    top = _e(d["top"], d["top"].get("base", "")) if d.get("top") else None
    flop = _e(d["flop"], d["flop"].get("base", "")) if d.get("flop") else None
    zeilen_x = ["🗺 Liquidity Map of the Day", f"$BTC at {L.pr(btc['preis'])}. Nearest estimated zones: {_naechste(btc)}."]
    sprech = ["Liquidity map of the day.", f"Bitcoin trades at {L.pr(btc['preis'])} dollars."]
    h = L.hellster(btc)
    if h:
        sprech.append(f"The biggest estimated liquidation cluster sits {abs(h['abstand_pct']):.1f}% "
                      f"{'above' if h['abstand_pct'] >= 0 else 'below'} the price.")
    if top:
        r = L.erreicht(top)
        zeilen_x.append(f"Coin of the day: {top['base']} {top['chg24']:+.1f}%"
                        + (f", it already ran into the estimated {L.ZONE_EN[r['art']]} cluster at {L.pr(r['mitte'])}."
                           if r else "."))
        sprech.append(f"Coin of the day: {top['base']}, {top['chg24']:+.1f}% in 24 hours."
                      + (f" It already ran into an estimated {L.ZONE_EN[r['art']]} cluster." if r else ""))
    x = "\n".join(zeilen_x + ["Estimated, not targets.", hw])
    if len(x) > 280:
        x = "\n".join(zeilen_x[:2] + [hw])
    esc = lambda s: html.escape(s, quote=False)
    tg = ["🗺 <b>Liquidity Map of the Day</b>", "", f"<b>{esc('$BTC')}</b> {esc(L.pr(btc['preis']))}"
          f" · nearest estimated zones: {esc(_naechste(btc))}"]
    for e, name in ((top, "Coin of the day"), (flop, "Flop of the day")):
        if e:
            r = L.erreicht(e)
            tg.append(f"<b>{esc(name)}: {esc(e['base'])} {e['chg24']:+.1f}%</b> · next estimated zones: "
                      f"{esc(_naechste(e)) or '–'}" + (f" · already hit the estimated {esc(L.ZONE_EN[r['art']])} "
                                                         f"cluster at {esc(L.pr(r['mitte']))}" if r else ""))
    tg += ["", esc("Brighter band = bigger estimated liquidation cluster. Estimates from price, volume and open "
                   "interest, not targets."), "", f"<i>{esc(hw)}</i>"]
    sprech.append("Brighter bands mean bigger estimated liquidation clusters. Estimates, not targets. Follow for more.")
    return {"x": x, "telegram": "\n".join(tg), "sprech": sprech}


def bauen(d: dict, ordner: Path, cfg: dict, web_dir: Path | None = None) -> tuple[list[Path], list[Path]]:
    """Karussell (4:5) + Reel-Szenen (9:16). Zeichnet aus den Rohdaten; fehlen sie, nimmt es das fertige englische
    Bild des Bots (heatmap_png_en, eigenes Bild, keine Fremd-Heatmap)."""
    ordner.mkdir(parents=True, exist_ok=True)
    folien, szenen = [], []
    teile = [("btc", "BTC", "Where the liquidity sits for $BTC today")]
    if d.get("top"):
        b = d["top"].get("base", "")
        teile.append(("top", b, f"${b} {d['top'].get('chg24', 0):+.1f}%: here's where the liquidations are stacked"))
        if d.get("flop"):
            b = d["flop"].get("base", "")
            teile.append(("flop", b, f"Flop of the day: ${b} {d['flop'].get('chg24', 0):+.1f}%"))
    for i, (feld, base, titel) in enumerate(teile):
        e = _e(d[feld], base)
        f = L.heatmap_bild(e, ordner / f"folie_{i:02d}.png", titel=titel)
        if not f and e.get("heatmap_png_en") and web_dir and (Path(web_dir) / e["heatmap_png_en"]).exists():
            f = ordner / f"folie_{i:02d}.png"
            shutil.copy(Path(web_dir) / e["heatmap_png_en"], f)
        if f:
            folien.append(f)
            s = L.heatmap_bild(e, ordner / "bilder" / f"szene_{i:02d}.png", H=1920, titel=titel)
            if s:
                szenen.append(s)
    if folien:
        (ordner / "post.png").write_bytes(folien[0].read_bytes())
        (ordner / "karussell.json").write_text(json.dumps({"folien": [f.name for f in folien]}), encoding="utf-8")
    return folien, szenen
