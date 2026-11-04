"""„Why did it move?“ (Wunsch Tobias 04.11.2026, ersetzt das Markt-Video): EIN Coin, und WARUM er sich bewegt hat.

Tobias: „Coin X +52 %“ kann sich jeder raussuchen. Unser Wert ist die Erklaerung aus Daten:
- Ausloeser (news.json des Bots)
- Futures: Open Interest (Aenderung 4 Std.) und Funding -> Short-Squeeze, Short-Eindeckung, Hebel-Rally, Long-Flush
- Spot-Anteil am Volumen -> echte Kaeufe oder Futures-getrieben
- Wale und Boersen (7 Tage, Prozentpunkte)
- Chart (echte 1h-Kerzen, nur Server): Liquiditaets-Sweep, gebrochene Unterstuetzung, Fibonacci-Zone, an der die
  Bewegung stoppte (nur rueckblickend, NIE als Ziel)
Jede Erklaerung folgt einer festen Regel (kein Raten). Greift keine Regel: „No clear driver in the data.“
Liquidationen kommen spaeter (Entscheidung Tobias 04.11.: erst ohne).
"""
from __future__ import annotations

from .sprache import TAG, haken_art, outro_szene

FIB = (0.382, 0.5, 0.618, 0.786)
TAG_EN = {"Listing": "Listing", "Delisting": "Delisting", "Partnerschaft": "Partnership", "Upgrade": "Upgrade",
          "Unlock": "Unlock", "Rueckkauf": "Buyback", "Airdrop": "Airdrop", "Funding": "Funding round", "ETF": "ETF",
          "Hack": "Hack", "Klage": "Lawsuit", "Wale": "Whales"}

# Schwellen der Regeln (Prozent, wie der Bot liefert)
OI_STARK = 10.0       # Open Interest in 4 Std. um mindestens 10 %
FUNDING_AUFF = 0.03   # |Funding| ab 0,03 % je Periode ist auffaellig (neutral ~0,01 %)
SPOT_HOCH, SPOT_TIEF = 60.0, 30.0
WAL_PP = 1.0          # Wal-/Boersen-Anteil um mindestens 1 Prozentpunkt in 7 Tagen

LEKTION = {
    "Short squeeze": "Next time: open interest rising while funding is negative means shorts are crowded.",
    "Short covering": "Next time: price up while open interest falls means shorts are closing, not new money.",
    "Leverage rally": "Next time: when longs pay high funding, the move rests on borrowed money.",
    "Real spot buying": "Next time: a high spot share means buyers who actually hold the coin.",
    "Futures-driven": "Next time: when spot volume is small, futures traders set the price.",
    "Long flush": "Next time: falling open interest in a drop means leveraged longs were closed.",
    "New shorts": "Next time: rising open interest in a drop with negative funding means traders bet on more downside.",
    "Coins to exchanges": "Next time: watch the exchange share. Coins on exchanges can be sold quickly.",
    "Whales buying": "Next time: watch the whale share. Rising whale holdings show who is accumulating.",
}


def _p(x: float, n: int = 1) -> str:
    return f"{x:+.{n}f}%"


def auswahl(d, sperr: set[str]) -> dict | None:
    """Groesste Bewegung (24 Std.) aus news.json, die Futures-Daten hat; sonst die groesste ueberhaupt."""
    kand = []
    for n in d.news:
        b = (n.get("base") or "").upper()
        if not b or b in sperr or n.get("chg24") is None:
            continue
        c = d.coins.get(n["base"]) or d.coins.get(b) or {}
        kand.append((c.get("oi_chg4h") is not None, abs(n["chg24"]), n, c))
    if not kand:
        return None
    _, _, n, c = max(kand, key=lambda k: (k[0], k[1]))
    return {"base": n["base"], "chg24": round(n["chg24"], 1), "driver": n.get("driver"), "coin": c}


# ---------------------------------------------------------------- Regeln

def futures_befund(chg: float, oi: float | None, funding: float | None) -> dict | None:
    if oi is None or funding is None:
        return None
    hoch, f = chg >= 0, round(funding, 2)
    oi1 = round(oi, 1)
    if hoch and oi >= OI_STARK and funding < 0:
        return {"label": "Short squeeze", "gross": f"OI {_p(oi1)}", "klein": f"Funding {_p(f, 2)}",
                "satz": f"Open interest rose {abs(oi1)}% in 4 hours while funding was {_p(f, 2)}. Traders were betting "
                        "against it, and the rising price squeezed them.", "zahlen": [oi1, f]}
    if hoch and oi <= -OI_STARK:
        return {"label": "Short covering", "gross": f"OI {_p(oi1)}", "klein": f"Funding {_p(f, 2)}",
                "satz": f"Open interest fell {abs(oi1)}% while the price rose. Shorts were closing their bets, "
                        "no new money came in.", "zahlen": [oi1, f]}
    if hoch and oi >= OI_STARK and funding >= FUNDING_AUFF:
        return {"label": "Leverage rally", "gross": f"OI {_p(oi1)}", "klein": f"Funding {_p(f, 2)}",
                "satz": f"Open interest rose {abs(oi1)}% and longs paid {_p(f, 2)} funding. The move ran on leverage.",
                "zahlen": [oi1, f]}
    if not hoch and oi <= -OI_STARK:
        return {"label": "Long flush", "gross": f"OI {_p(oi1)}", "klein": f"Funding {_p(f, 2)}",
                "satz": f"Open interest dropped {abs(oi1)}% in 4 hours. Leveraged longs were closed, which added "
                        "to the selling.", "zahlen": [oi1, f]}
    if not hoch and oi >= OI_STARK and funding < 0:
        return {"label": "New shorts", "gross": f"OI {_p(oi1)}", "klein": f"Funding {_p(f, 2)}",
                "satz": f"Open interest rose {abs(oi1)}% while funding was {_p(f, 2)}. New shorts piled in "
                        "on the way down.", "zahlen": [oi1, f]}
    return None


def spot_befund(chg: float, spot: float | None) -> dict | None:
    if spot is None:
        return None
    s = round(spot)
    if spot >= SPOT_HOCH:
        return {"label": "Real spot buying" if chg >= 0 else None, "gross": f"{s}% spot",
                "klein": "share of volume",
                "satz": f"{s}% of the volume was on spot markets: real coins changing hands, not just leverage.",
                "zahlen": [s]}
    if spot <= SPOT_TIEF:
        return {"label": "Futures-driven", "gross": f"{s}% spot", "klein": "share of volume",
                "satz": f"Only {s}% of the volume was spot. Futures traders drove this move.", "zahlen": [s]}
    return None


def wal_befund(c: dict) -> dict | None:
    w7 = c.get("wale_7d") or {}
    wal, boe = w7.get("wal"), w7.get("boerse")
    if wal is None and boe is None:
        return None
    wal, boe = round(wal or 0, 1), round(boe or 0, 1)
    if boe >= WAL_PP and wal <= -WAL_PP:
        return {"label": "Coins to exchanges", "gross": f"Whales {wal:+.1f} pp", "klein": f"Exchanges {boe:+.1f} pp",
                "satz": f"In 7 days whales cut their share by {abs(wal)} percentage points and exchanges gained "
                        f"{boe}. Coins moved to where they can be sold.", "zahlen": [abs(wal), boe]}
    if boe >= WAL_PP:
        return {"label": "Coins to exchanges", "gross": f"Exchanges {boe:+.1f} pp", "klein": "7 days",
                "satz": f"The exchange share rose {boe} percentage points in 7 days. More coins sit where they "
                        "can be sold.", "zahlen": [boe]}
    if wal >= WAL_PP:
        return {"label": "Whales buying", "gross": f"Whales {wal:+.1f} pp", "klein": "7 days",
                "satz": f"Whales raised their share by {wal} percentage points in 7 days.", "zahlen": [wal]}
    if wal <= -WAL_PP:
        return {"label": None, "gross": f"Whales {wal:+.1f} pp", "klein": "7 days",
                "satz": f"Whales cut their share by {abs(wal)} percentage points in 7 days.", "zahlen": [abs(wal)]}
    return None


def chart_befund(k: list[dict], chg: float) -> dict | None:
    """Rueckblick auf 1h-Kerzen (7 Tage): Sweep vor dem Anstieg, gebrochene Unterstuetzung, Fibonacci-Stopp."""
    from . import muster
    if len(k) < 60:
        return None
    hoch = chg >= 0
    if hoch:
        s = muster.liquiditaet(k)
        if s and s["docht_index"] >= len(k) - 36:
            return {"art": "liquiditaet", "info": s, "label": None, "zahlen": [],
                    "satz": "Just before the jump, price dipped below a recent low and snapped back. "
                            "The stops under that low were taken first."}
    else:
        u = muster.unterstuetzung(k)
        if u and u.get("bruch_index") and u["bruch_index"] >= len(k) - 36:
            n = len(u["support"]["beruehrungen"])
            return {"art": "unterstuetzung", "info": u, "label": None, "zahlen": [n],
                    "satz": f"Price broke through a support zone it had held {n} times. Stops below it turned "
                            "into selling."}
    vor = k[:-24]
    lo, hi = min(x["l"] for x in vor), max(x["h"] for x in vor)
    if hi <= lo:
        return None
    letzt = k[-24:]
    if hoch:
        punkt = max(x["h"] for x in letzt)
        if punkt > hi:
            return {"art": "fib", "info": {"preis": hi, "label": "last week's high"}, "label": None, "zahlen": [],
                    "satz": "The rally broke above last week's high."}
        stufen = [(r, lo + r * (hi - lo)) for r in FIB]
    else:
        punkt = min(x["l"] for x in letzt)
        if punkt < lo:
            return {"art": "fib", "info": {"preis": lo, "label": "last week's low"}, "label": None, "zahlen": [],
                    "satz": "The drop broke below last week's low."}
        stufen = [(r, hi - r * (hi - lo)) for r in FIB]
    r, preis = min(stufen, key=lambda s: abs(s[1] - punkt))
    if abs(preis - punkt) / punkt > 0.012:
        return None
    rp = round(r * 100, 1)
    return {"art": "fib", "info": {"preis": preis, "label": f"Fib {rp:g}%"}, "label": None, "zahlen": [rp],
            "satz": f"The {'rally' if hoch else 'drop'} stopped right at the {rp:g}% Fibonacci level of last week's "
                    "range."}


# ---------------------------------------------------------------- Beitrag

def beitrag(d, sperr: set[str], kerzen: list[dict] | None, lang: str = "en", tag=None) -> dict:
    if lang != "en":
        raise ValueError("„Why did it move?“ gibt es nur auf Englisch")
    w = auswahl(d, sperr)
    if not w:
        raise ValueError("Keine Bewegung in news.json – kein Warum-Video")
    b, chg, c = w["base"], w["chg24"], w["coin"]
    hoch = chg >= 0
    zahlen = [abs(chg), 4, 7, 24]   # feste Zeitraeume im Sprechtext (4 hours, 7 days, 24 hours)
    art = haken_art(tag)
    verb = "jump" if hoch else "drop"
    if art == "frage":
        haken = f"Why did {b} {verb} {abs(chg)}% in 24 hours? Here is what the data shows."
        frage = f"WHY DID {b} {verb.upper()}?"
    else:
        haken = f"{b} {'jumped' if hoch else 'dropped'} {abs(chg)}% in 24 hours. Here is what the data shows."
        frage = None
    szenen = [{"typ": "warum_haken", "haken": art, "daten": {"base": b, "chg24": chg, "_frage": frage},
               "vorlage": haken}]
    labels, belege = [], []
    drv = w.get("driver") or {}
    tag_ = (drv.get("tags") or [None])[0]
    if tag_ and TAG["en"].get(tag_):
        belege.append({"titel": "TRIGGER", "label": TAG_EN.get(tag_, tag_), "gross": TAG_EN.get(tag_, tag_).upper(),
                       "klein": "news",
                       "satz": f"The trigger: {TAG['en'][tag_]}.", "zahlen": []})
    for titel, bef in (("FUTURES", futures_befund(chg, c.get("oi_chg4h"), c.get("funding"))),
                       ("SPOT VS FUTURES", spot_befund(chg, c.get("spot_anteil"))),
                       ("WHALES & EXCHANGES", wal_befund(c))):
        if bef:
            belege.append(dict(bef, titel=titel))
    for bf in belege[:3]:
        szenen.append({"typ": "warum_beleg", "daten": bf, "vorlage": bf["satz"]})
        zahlen += bf["zahlen"]
        if bf.get("label"):
            labels.append(bf["label"])
    ch = chart_befund(kerzen or [], chg) if kerzen else None
    if ch:
        szenen.append({"typ": "warum_chart", "daten": {"kerzen": kerzen, "art": ch["art"], "info": ch["info"],
                                                       "base": b}, "vorlage": ch["satz"]})
        zahlen += ch["zahlen"]
    if labels:
        lektion = next((LEKTION[l] for l in labels if l in LEKTION), "")
        urteil = f"Verdict: {' plus '.join(l.lower() for l in labels[:2])}. {lektion}".strip()
    else:
        urteil = "Verdict: no clear driver in the data. Sometimes a move is just thin trading."
    szenen.append({"typ": "warum_urteil", "daten": {"labels": labels[:2]}, "vorlage": urteil})
    szenen.append(outro_szene("warum", lang))
    return {"format": "warum", "titel": f"Why did {b} move?", "sprache": lang, "base": b,
            "fakten": {"base": b, "chg24": chg, "zahlen": zahlen, "labels": labels}, "szenen": szenen,
            "hashtags": ["#crypto", f"#{b.lower()}", "#altcoins", "#cryptonews", "#whalesqueeze"]}


def texte(bt: dict, cfg: dict) -> dict:
    """X und Telegram: Frage + Befunde als Punkte + Urteil."""
    import html
    from .sprache import hinweis
    hw = hinweis(cfg, "en")
    sz = bt["szenen"]
    kopf = sz[0]["vorlage"].split(". Here is")[0].split("? Here is")[0]
    kopf = kopf if kopf.endswith("?") or kopf.endswith(".") else kopf + ("?" if sz[0].get("haken") == "frage" else ".")
    punkte = [s["vorlage"] for s in sz if s["typ"] in ("warum_beleg", "warum_chart")]
    urteil = next(s["vorlage"] for s in sz if s["typ"] == "warum_urteil").split(". Next time")[0] + "."
    x_teile = [f"🔍 {kopf}", *[f"• {p.split('. ')[0].rstrip('.')}." for p in punkte], urteil.replace("..", "."), hw]
    x = "\n".join(x_teile)
    while len(x) > 280 and len(x_teile) > 3:
        x_teile.pop(-3)
        x = "\n".join(x_teile)
    e = lambda s: html.escape(s, quote=False)
    tg = [f"🔍 <b>{e(kopf)}</b>", ""] + [f"• {e(p)}" for p in punkte] + ["", f"<b>{e(urteil)}</b>"]
    lektion = next(s["vorlage"] for s in sz if s["typ"] == "warum_urteil").split(". ", 1)
    if len(lektion) > 1 and lektion[1].startswith("Next time"):
        tg.append(e(lektion[1]))
    tg += ["", f"<i>{e(hw)}</i>"]
    return {"x": x, "telegram": "\n".join(tg)}
