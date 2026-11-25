"""Eilmeldungen aus grossen X-Konten (Wunsch Tobias 25.11.2026: „Ich will, dass du solche Kurse und Nachrichten selber
entdeckst. Ich habe keine Zeit, taeglich nachzuschauen.“).

Die Schnell-Antwort (tools/schnellantwort.py) liest ohnehin alle 10 Minuten die frischen Posts der grossen Konten
(Kobeissi, Watcher Guru ...). Beginnt ein Post mit „BREAKING“ oder „JUST IN“ und geht es um Krypto, baut der Server
daraus sofort ein Eil-Reel:
- Claude schreibt den Text in EIGENEN Worten (nie kopieren), jede Zahl muss im Post stehen, keine Quelle im Beitrag.
- Echter Live-Chart des Coins (Bitunix/Binance), wenn der Post einen Coin nennt.
- Einheitlicher Schluss (Follow · Like · Comment) und Countdown-Frage.
Gepostet wird erst nach Tobias' Freigabe (News und Eilmeldungen bleiben immer manuell). Hoechstens eil_x.max_pro_tag.
Reine Kursmeldungen zu BTC/ETH entfallen, wenn der eigene Kurs-Alarm denselben Coin in den letzten 3 Std. gemeldet hat.
"""
from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path

EIL = re.compile(r"^\W*(breaking|just in)\b", re.I)
KRYPTO = re.compile(r"\b(bitcoin|btc|ethereum|eth|crypto|xrp|solana|sol|binance|coinbase|stablecoin|tether|usdt|usdc|"
                    r"etf|liquidat\w*|saylor|microstrategy|strategy|blackrock|defi|altcoins?|memecoin|doge)\b", re.I)
COINS = ("BTC", "ETH", "XRP", "SOL", "DOGE", "BNB")

SYSTEM = """You write a short breaking-news reel for WhaleSqueeze, a crypto channel. English only.
Input: one breaking post from a large news account. Write in YOUR OWN words, never copy sentences.
Rules (strict):
- Use ONLY facts and numbers that appear in the post. No other numbers, no prices from memory.
- No source names, no "reportedly", no links, no hashtags except one cashtag.
- No buy/sell calls, no price targets, no profit promises.
- 3 scenes. Each scene: "etikett" (2-3 words, caps), "kopf" (headline, max 8 words), "text" (one or two spoken
  sentences, max 28 words). Scene 1 starts with "Breaking:". Scene 3 asks the viewers' opinion.
- "coin": the main coin ticker if the post is about one (BTC, ETH, XRP, SOL, DOGE, BNB), else null.
- "nur_kurs": true if the post is only about a price move of BTC or ETH, else false.
- "x": the X text, max 230 characters, own words, ending with the cashtag if a coin is named.
Answer with JSON only: {"szenen":[{"etikett":"","kopf":"","text":""}],"coin":null,"nur_kurs":false,"x":""}"""


def erkennen(posts: list[dict]) -> list[dict]:
    """Nur echte Eilmeldungen zu Krypto."""
    return [p for p in posts if EIL.search(p.get("text") or "") and KRYPTO.search(p.get("text") or "")]


def zahlen_ok(spec: dict, quelle: str) -> bool:
    """Jede Zahl im Sprechtext muss im Original-Post stehen (Schutzregel)."""
    norm = lambda s: s.replace(",", "").replace("$", "")
    q = norm(quelle)
    for sz in spec.get("szenen") or []:
        for z in re.findall(r"\d[\d,.]*", sz.get("text", "") + " " + sz.get("kopf", "")):
            z = norm(z).rstrip(".")
            if z and z not in q:
                return False
    return True


def schreiben(post: dict, cfg: dict, api_key: str, post_fn=None) -> dict:
    from . import claude
    kw = {"post": post_fn} if post_fn else {}
    return claude.json_antwort(SYSTEM, f"Post (from @{post.get('konto')}):\n{post['text']}", cfg, api_key,
                               max_tokens=1500, **kw)


def bauen(post: dict, spec: dict, ziel_basis: Path, cfg: dict, jetzt: float | None = None) -> Path:
    from PIL import ImageDraw
    from . import design
    from .design import etikett, fuss, hintergrund, marke, ueberschrift
    jetzt = jetzt or time.time()
    th = design.THEMEN["nacht"]
    W, H = cfg["video"]["breite"], cfg["video"]["hoehe"]
    o = ziel_basis / f"{time.strftime('%Y%m%d-%H%M', time.localtime(jetzt))}_redaktion_eilx_{post['id'][-6:]}_video"
    o.mkdir(parents=True, exist_ok=True)
    coin = (spec.get("coin") or "").upper().lstrip("$") or None
    coin = coin if coin in COINS else None
    szenen = []
    for i, sz in enumerate((spec.get("szenen") or [])[:3]):
        img = hintergrund(th, W, H, saat=300 + i)
        marke(img, th, 70, 70, 64)
        d = ImageDraw.Draw(img)
        etikett(d, th, 70, 190, (sz.get("etikett") or "BREAKING")[:28], farbe=th.minus if i == 0 else th.akzent)
        ueberschrift(d, th, 70, 260, sz.get("kopf") or "", W - 140, groesse=72, max_zeilen=3)
        fuss(img, th, "Not financial advice.")
        img.convert("RGB").save(o / f"szene_{i}.png")
        s = {"bild": f"szene_{i}.png", "text": sz.get("text") or ""}
        if i == 1 and coin:   # echter Live-Chart unter der Ueberschrift
            s.update(chart={"base": coin, "intervall": "15m", "anzahl": 48, "titel": f"{coin} · 15m · live",
                            "box": [40, 560, 1040, 1560]})
            s["text_ohne"] = s["text"]
        szenen.append(s)
    spec_reel = {"thema": f"eilx-{post['id'][-6:]}", "szenen": szenen}
    if coin:
        spec_reel["frage"] = {"name": f"${coin}"}
    (o / "reel.json").write_text(json.dumps(spec_reel), encoding="utf-8")
    (o / "post.png").write_bytes((o / "szene_0.png").read_bytes())
    e = lambda s: html.escape(s, quote=False)
    x = (spec.get("x") or szenen[0]["text"])[:230] + "\n\nNot financial advice."
    (o / "post_x.txt").write_text(x, encoding="utf-8")
    tg = [f"🚨 <b>{e(spec['szenen'][0].get('kopf', ''))}</b>", ""] + [e(s["text"]) for s in szenen] + \
         ["", "Follow us for more. Like and comment below 👇", "", "<i>Not financial advice.</i>"]
    (o / "post_telegram.txt").write_text("\n".join(tg), encoding="utf-8")
    return o


def verarbeiten(posts: list[dict], cfg: dict, geheim: dict, ausgabe: Path, schreiber=None, senden=None,
                reel_bauen=None, jetzt: float | None = None) -> list[Path]:
    """Erkennen -> Text -> Reel -> an Tobias. Merkt sich bearbeitete Posts in eil_x_stand.json."""
    e_cfg = cfg.get("eil_x") or {}
    if not e_cfg.get("aktiv", True):
        return []
    jetzt = jetzt or time.time()
    sp = ausgabe / "eil_x_stand.json"
    try:
        stand = json.loads(sp.read_text())
    except Exception:
        stand = {}
    tag = time.strftime("%Y-%m-%d", time.localtime(jetzt))
    erledigt = stand.setdefault("ids", [])
    try:
        ka = json.loads((ausgabe / "kursalarm_stand.json").read_text())
    except Exception:
        ka = {}
    out = []
    for p in erkennen(posts):
        if p["id"] in erledigt or stand.get("anzahl", {}).get(tag, 0) >= int(e_cfg.get("max_pro_tag", 6)):
            continue
        erledigt.append(p["id"])
        try:
            spec = (schreiber or (lambda q: schreiben(q, cfg, geheim["anthropic_api_key"])))(p)
        except Exception as ex:
            print("Eil-X: Claude-Fehler", ex)
            continue
        coin = (spec.get("coin") or "").upper()
        if spec.get("nur_kurs") and coin in ("BTC", "ETH") and any(
                k.startswith(coin + "_") and not k.endswith("_preis") and jetzt - v < 3 * 3600
                for k, v in ka.items() if isinstance(v, (int, float))):
            continue   # der eigene Kurs-Alarm hat es schon gemeldet
        if not zahlen_ok(spec, p["text"]) or len(spec.get("szenen") or []) < 2:
            print("Eil-X: verworfen (Zahl nicht im Post oder zu kurz)", p["id"])
            continue
        o = bauen(p, spec, ausgabe, cfg, jetzt)
        stand.setdefault("anzahl", {})[tag] = stand.get("anzahl", {}).get(tag, 0) + 1
        out.append(o)
        if senden:
            hinweis = f"🚨 Eilmeldung automatisch erkannt · Quelle (nur für dich): @{p.get('konto')} {p.get('link', '')}"
            try:
                ton = (reel_bauen or (lambda ordner: __import__("social.reel", fromlist=["bauen"]).bauen(
                    ordner, cfg, geheim)))(o)
                senden(geheim, o, f"{hinweis}\n🎙 Ton: {ton}")
            except Exception as ex:
                senden(geheim, o, f"{hinweis}\n⚠️ Reel nicht gebaut: {str(ex)[:150]}")
    stand["ids"] = erledigt[-500:]
    stand["anzahl"] = {t: n for t, n in stand.get("anzahl", {}).items() if t >= tag}
    ausgabe.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(stand))
    return out
