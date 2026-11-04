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
    "Stops taken": "Next time: old highs and lows are where stops cluster. Price often runs through them fast.",
    "Volume spike": "Next time: a volume spike shows real interest. Watch whether it lasts after the first day.",
    "Whales buying": "Next time: watch the whale share. Rising whale holdings show who is accumulating.",
}


def _p(x: float, n: int = 1) -> str:
    return f"{x:+.{n}f}%"


def coin_wahl(d, base: str) -> dict | None:
    """Wunsch-Coin (/warum COIN): Werte aus coins/<BASE>.json (Bitunix, wie der Bot), Ausloeser aus news.json."""
    b = base.upper()
    c = d.coins.get(b) or next((v for k, v in d.coins.items() if k.upper() == b), None)
    if not c or c.get("chg24") is None:
        return None
    n = next((x for x in d.news if (x.get("base") or "").upper() == b), {})
    return {"base": c.get("base") or b, "chg24": round(c["chg24"], 1), "driver": n.get("driver"), "coin": c}


def auswahl(d, sperr: set[str], richtung: str = "hoch") -> dict | None:
    """richtung 'hoch' (14:30): groesster Gewinner; 'runter' (18:30, Wunsch Tobias 04.11.): groesster Verlierer.
    Coins mit Futures-Daten zuerst. Gibt es keinen in der Richtung: 'hoch' nimmt die groesste Bewegung, 'runter' nichts."""
    kand = []
    for n in d.news:
        b = (n.get("base") or "").upper()
        if not b or b in sperr or n.get("chg24") is None:
            continue
        if richtung == "runter" and n["chg24"] >= 0:
            continue
        c = d.coins.get(n["base"]) or d.coins.get(b) or {}
        passt = (n["chg24"] > 0) if richtung == "hoch" else True
        kand.append((passt, c.get("oi_chg4h") is not None, abs(n["chg24"]), n, c))
    if not kand:
        return None
    *_, n, c = max(kand, key=lambda k: k[:3])
    return {"base": n["base"], "chg24": round(n["chg24"], 1), "driver": n.get("driver"), "coin": c}


def verlauf_satz(verlauf: list[dict] | None, jetzt: float | None = None) -> dict | None:
    """Funding vor 6 Std. -> jetzt, wenn es sich um mindestens 0,03 Prozentpunkte geaendert hat (Wunsch 04.11.)."""
    from . import verlauf as _v
    if not verlauf:
        return None
    jetzt_f = verlauf[-1].get("funding")
    vorher = _v.vor(verlauf, 6, "funding", jetzt or verlauf[-1]["ts"])
    if jetzt_f is None or vorher is None or abs(jetzt_f - vorher) < FUNDING_AUFF:
        return None
    a, b = round(vorher, 2), round(jetzt_f, 2)
    return {"satz": f"Funding went from {_p(a, 2)} to {_p(b, 2)} in 6 hours.", "zahlen": [a, b, 6]}


# ---------------------------------------------------------------- Regeln

def futures_befund(chg: float, oi: float | None, funding: float | None) -> dict | None:
    if oi is None or funding is None:
        return None
    hoch, f = chg >= 0, round(funding, 2)
    oi1 = round(oi, 1)
    if hoch and oi >= OI_STARK and funding < 0:
        return {"label": "Short squeeze", "gross": f"OI {_p(oi1)}", "klein": f"Funding {_p(f, 2)}",
                "satz": f"Open interest rose {abs(oi1)}% in 4 hours with funding at {_p(f, 2)}. Shorts got squeezed.",
                "zahlen": [oi1, f]}
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
                "satz": f"{s}% of the volume was spot: real buying, not just leverage.",
                "zahlen": [s]}
    if spot <= SPOT_TIEF:
        return {"label": "Futures-driven", "gross": f"{s}% spot", "klein": "share of volume",
                "satz": f"Only {s}% of the volume was spot. Futures traders drove this move.", "zahlen": [s]}
    return None


def wal_befund(c: dict) -> dict | None:
    from .daten import wal_plausibel
    if not wal_plausibel(c):   # Datenfehler wie CARV 04.11. nie als Erklaerung
        return None
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


# ---------------------------------------------------------------- Kurs, Volumen, Zonen, Halter, Long/Short (04.11.)
# Tobias 04.11.2026: „Wir brauchen echte Werte: wie ist der Kurs verlaufen, wie weit runter, Holder (Wale, Boersen),
# Long-Short-Ratio, Volumen, welche Liquidationszonen wurden abgeholt.“ Alles aus Bitunix-Kerzen (Server) und Bot-Daten.

def pr(x: float) -> str:
    """Preis wie an der Boerse: 23.23, 0.4512, 1,234."""
    return f"${x:,.0f}" if x >= 100 else (f"${x:.2f}" if x >= 1 else f"${x:.4g}")


def _pz(x: float) -> float:
    return float(pr(x).replace("$", "").replace(",", ""))


def kurs_befund(k: list[dict], hoch: bool) -> dict | None:
    """Verlauf der letzten 24 Std. aus echten 1h-Kerzen: Start, Hoch/Tief, jetzt, Abstand zum Extrem."""
    if len(k) < 26:
        return None
    letzt = k[-24:]
    start, jetzt = k[-25]["c"], k[-1]["c"]
    hi, lo = max(x["h"] for x in letzt), min(x["l"] for x in letzt)
    if hoch:
        abst = round((hi - jetzt) / hi * 100, 1)
        satz = f"From {pr(start)} to a high of {pr(hi)} in 24 hours. Now {pr(jetzt)}, {abst}% below the high."
    else:
        abst = round((jetzt - lo) / lo * 100, 1)
        satz = f"From {pr(start)} to a low of {pr(lo)} in 24 hours. Now {pr(jetzt)}, {abst}% above the low."
    return {"satz": satz, "zahlen": [_pz(start), _pz(hi), _pz(lo), _pz(jetzt), abst]}


def volumen_befund(k: list[dict]) -> dict | None:
    """24-Std.-Volumen gegen den Tagesschnitt der Tage davor (mindestens 3 volle Tage)."""
    vor = k[:-24]
    tage = [sum(x["v"] for x in vor[i:i + 24]) for i in range(len(vor) % 24, len(vor), 24)]
    tage = [t for t in tage if t > 0]
    jetzt = sum(x["v"] for x in k[-24:])
    if len(tage) < 3 or jetzt <= 0:
        return None
    r = round(jetzt / (sum(tage) / len(tage)), 1)
    if r < 1.5:
        return None
    return {"r": r, "satz": f"Volume was {r}x the daily average of the days before.", "zahlen": [r],
            "label": "Volume spike" if r >= 3 else None}


def zonen_befund(k: list[dict], hoch: bool) -> dict | None:
    """Liquiditaetszonen, die abgeholt wurden: alte Hochs (Stops der Shorts) bzw. alte Tiefs (Stops der Longs) aus
    den Tagen davor, die in den letzten 24 Std. ueberschritten/unterschritten wurden."""
    from . import muster
    if len(k) < 60:
        return None
    vor, letzt = k[:-24], k[-24:]
    start = k[-25]["c"]
    if hoch:
        hi = max(x["h"] for x in letzt)
        z = sorted({round(vor[i]["h"], 8) for i in muster._hochs(vor) if start < vor[i]["h"] < hi})
    else:
        lo = min(x["l"] for x in letzt)
        z = sorted({round(vor[i]["l"], 8) for i in muster._tiefs(vor) if lo < vor[i]["l"] < start}, reverse=True)
    if not z:
        return None
    z = z[-3:] if hoch else z[:3]
    wer = "short sellers" if hoch else "long traders"
    liste = ", ".join(pr(x) for x in z)
    satz = f"It took out {len(z)} old {'highs' if hoch else 'lows'} where {wer} had their stops: {liste}."
    return {"zonen": z, "satz": satz, "zahlen": [len(z)] + [_pz(x) for x in z]}


def halter_befund(c: dict) -> dict | None:
    """Wie viel halten Wale und Boersen (Prozent der Gesamtmenge), nur bei plausiblen Daten."""
    from .daten import wal_plausibel
    if not wal_plausibel(c):
        return None
    w = c.get("wale") or {}
    wal, boe = round(w.get("wal") or 0, 1), round(w.get("boerse") or 0, 1)
    satz = f"Holders: whales hold {wal}% of the supply, exchanges {boe}%."
    zahlen = [wal, boe]
    wb = wal_befund(c)
    if wb:
        satz += " " + wb["satz"]
        zahlen += wb["zahlen"]
    return {"titel": "HOLDERS", "gross": f"Whales {wal}%", "klein": f"Exchanges {boe}%",
            "label": wb["label"] if wb else None, "satz": satz, "zahlen": zahlen}


def lsr_satz(lsr: dict | None) -> dict | None:
    """Long/Short-Verhaeltnis (Konten, Binance-Futures, oeffentlich): jetzt und vor 24 Std."""
    if not lsr or lsr.get("jetzt") is None:
        return None
    r, lp = round(lsr["jetzt"], 2), round(lsr["long_pct"])
    satz = f"Long/short ratio on Binance: {r}, so {lp}% of accounts are long"
    zahlen = [r, lp]
    if lsr.get("vor24") is not None:
        r0 = round(lsr["vor24"], 2)
        satz += f" (24 hours ago: {r0})"
        zahlen.append(r0)
    return {"satz": satz + ".", "zahlen": zahlen}


# ---------------------------------------------------------------- Beitrag

def beitrag(d, sperr: set[str], kerzen: list[dict] | None, lang: str = "en", tag=None, richtung: str = "hoch",
            verlauf: list[dict] | None = None, wahl: dict | None = None, lsr: dict | None = None) -> dict:
    """Szenen: Haken, Kurs-Chart (Verlauf + abgeholte Zonen), Ausloeser, Futures (+ Funding-Verlauf, Long/Short),
    Volumen + Spot, Halter, Urteil, Kommentar-Frage. Nur was die Daten hergeben."""
    if lang != "en":
        raise ValueError("„Why did it move?“ gibt es nur auf Englisch")
    w = wahl or auswahl(d, sperr, richtung)
    if not w:
        raise ValueError("Keine Bewegung in news.json – kein Warum-Video")
    b, chg, c = w["base"], w["chg24"], w["coin"]
    hoch = chg >= 0
    k = kerzen or []
    zahlen = [abs(chg), 4, 6, 7, 24]   # feste Zeitraeume im Sprechtext
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
    labels = []

    # 1. Kurs: echter Chart (3 Tage, 1h) mit Verlauf und abgeholten Zonen
    kb, zb = kurs_befund(k, hoch), zonen_befund(k, hoch)
    if kb:
        satz = kb["satz"] + (" " + zb["satz"] if zb else "")
        zahlen += kb["zahlen"] + (zb["zahlen"] if zb else [])
        szenen.append({"typ": "warum_chart", "daten": {"kerzen": k[-72:], "art": "zonen",
                                                       "info": {"zonen": zb["zonen"] if zb else [], "hoch": hoch},
                                                       "base": b}, "vorlage": satz})
        if zb:
            labels.append("Stops taken")
    # 2. Ausloeser
    drv = w.get("driver") or {}
    tag_ = (drv.get("tags") or [None])[0]
    if tag_ and TAG["en"].get(tag_):
        szenen.append({"typ": "warum_beleg", "daten": {"titel": "TRIGGER", "label": None,
                                                        "gross": TAG_EN.get(tag_, tag_).upper(), "klein": "news"},
                       "vorlage": f"The trigger: {TAG['en'][tag_]}."})
        labels.insert(0, TAG_EN.get(tag_, tag_))
    # 3. Futures: OI/Funding-Regel + Funding-Verlauf + Long/Short
    fb = futures_befund(chg, c.get("oi_chg4h"), c.get("funding"))
    teile, fz = [], []
    if fb:
        teile.append(fb["satz"]); fz += fb["zahlen"]
        labels.append(fb["label"])
    elif c.get("oi_chg4h") is not None and c.get("funding") is not None:
        oi, f = round(c["oi_chg4h"], 1), round(c["funding"], 2)
        teile.append(f"Futures: open interest {_p(oi)} in 4 hours, funding {_p(f, 2)}."); fz += [oi, f]
    vs = verlauf_satz(verlauf)
    if vs:
        teile.append(vs["satz"]); fz += vs["zahlen"]
    ls = lsr_satz(lsr)
    if ls:
        teile.append(ls["satz"]); fz += ls["zahlen"]
    if teile:
        gross = (fb or {}).get("gross") or (f"OI {_p(round(c['oi_chg4h'], 1))}" if c.get("oi_chg4h") is not None
                                            else f"L/S {round(lsr['jetzt'], 2)}")
        klein = (f"Long/short {round(lsr['jetzt'], 2)}" if ls else
                 (f"Funding {_p(round(c['funding'], 2), 2)}" if c.get("funding") is not None else ""))
        szenen.append({"typ": "warum_beleg", "daten": {"titel": "FUTURES", "label": (fb or {}).get("label"),
                                                        "gross": gross, "klein": klein}, "vorlage": " ".join(teile)})
        zahlen += fz
    # 4. Volumen + Spot-Anteil
    vb, sb = volumen_befund(k), spot_befund(chg, c.get("spot_anteil"))
    if vb or sb:
        satz = " ".join(x["satz"] for x in (vb, sb) if x)
        zahlen += (vb["zahlen"] if vb else []) + (sb["zahlen"] if sb else [])
        for x in (vb, sb):
            if x and x.get("label"):
                labels.append(x["label"])
        szenen.append({"typ": "warum_beleg", "daten": {"titel": "VOLUME",
                                                        "gross": f"{vb['r']}x volume" if vb else sb["gross"],
                                                        "klein": sb["gross"] if (vb and sb) else "vs. daily average",
                                                        "label": (vb or {}).get("label") or (sb or {}).get("label")},
                       "vorlage": satz})
    # 5. Halter (Wale, Boersen) nur mit plausiblen Daten
    hb = halter_befund(c)
    if hb:
        szenen.append({"typ": "warum_beleg", "daten": hb, "vorlage": hb["satz"]})
        zahlen += hb["zahlen"]
        if hb.get("label"):
            labels.append(hb["label"])
    prio = ["Short squeeze", "Short covering", "Leverage rally", "Long flush", "New shorts", "Real spot buying",
            "Futures-driven", "Coins to exchanges", "Whales buying", "Volume spike", "Stops taken"]
    labels = [l for i, l in enumerate(labels) if l and l not in labels[:i]]
    trig = [l for l in labels if l not in prio]   # Ausloeser (Listing ...) zuerst
    labels = trig + sorted([l for l in labels if l in prio], key=prio.index)
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


def pruef_cfg(cfg: dict) -> dict:
    """Warum-Video darf etwas laenger sein (ca. 40 Sek. statt 30): text.max_woerter_warum, Standard 110."""
    return dict(cfg, text=dict(cfg["text"], max_woerter=cfg["text"].get("max_woerter_warum", 150)))


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
