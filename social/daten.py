"""Liest die JSON-Dateien, die der Bot nach /opt/volumen-bot/web schreibt (nur lesen)."""
from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path


class DatenFehler(Exception):
    pass


@dataclass
class Daten:
    ordner: Path
    stand: dict
    news: list
    signale: list
    divergenzen: list
    bilanz: dict
    coins: dict = field(default_factory=dict)
    markt: dict | None = None   # markt.json (Bot 9.10), None = Datei fehlt -> Ersatzrechnung aus coins/

    @property
    def ts(self) -> int:
        return int(self.stand.get("ts") or 0)


def _lies(p: Path, default):
    if not p.exists():
        return default
    try:
        with p.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise DatenFehler(f"{p.name} nicht lesbar: {e}") from e


def laden(ordner: str | Path, max_alter_min: float | None = None, jetzt: float | None = None) -> Daten:
    o = Path(ordner)
    if not o.is_dir():
        raise DatenFehler(f"Datenordner fehlt: {o}")
    stand = _lies(o / "stand.json", None)
    if not stand:
        raise DatenFehler("stand.json fehlt – laeuft der Bot?")
    if max_alter_min is not None:
        alter = ((jetzt or time.time()) - stand.get("ts", 0)) / 60
        if alter > max_alter_min:
            raise DatenFehler(f"Daten sind {alter:.0f} Minuten alt (Grenze {max_alter_min})")
    coins = {}
    cdir = o / "coins"
    if cdir.is_dir():
        for p in sorted(cdir.glob("*.json")):
            c = _lies(p, None)
            if c and c.get("base"):
                coins[c["base"]] = c
    return Daten(
        ordner=o,
        stand=stand,
        news=_lies(o / "news.json", []),
        signale=_lies(o / "signale.json", []),
        divergenzen=_lies(o / "divergenzen.json", []),
        bilanz=_lies(o / "bilanz.json", {"trades": []}),
        coins=coins,
        markt=_lies(o / "markt.json", None),
    )


def marktbreite(d: Daten) -> dict | None:
    """Altcoin-Breite aus allen Coins im Scan: Median 24h und Anteil im Plus."""
    werte = [c["chg24"] for c in d.coins.values() if isinstance(c.get("chg24"), (int, float))]
    if len(werte) < 10:
        return None
    return {
        "median_24h": round(statistics.median(werte), 1),
        "anteil_plus": round(100 * sum(1 for w in werte if w > 0) / len(werte)),
        "anzahl": len(werte),
    }


def _zahl(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def marktlage(d: Daten) -> dict | None:
    """Altcoin-Breite und BTC/ETH. Bevorzugt markt.json vom Bot, sonst Ersatzrechnung aus coins/*.json.

    Rueckgabe wie marktbreite() plus 'quelle' ("bot" oder "ersatz") und, wenn vorhanden, 'btc_24h', 'eth_24h'.
    """
    ersatz = marktbreite(d)
    m = d.markt or {}
    if _zahl(m.get("alt_median_24h")) and _zahl(m.get("alt_anteil_plus")):
        anzahl = ersatz["anzahl"] if ersatz else sum(1 for c in d.coins.values() if _zahl(c.get("chg24")))
        out = {"median_24h": round(m["alt_median_24h"], 1), "anteil_plus": round(m["alt_anteil_plus"]),
               "anzahl": anzahl, "quelle": "bot"}
    elif ersatz:
        out = dict(ersatz, quelle="ersatz")
    else:
        return None
    for k, key in (("btc", "btc_24h"), ("eth", "eth_24h")):
        v = (m.get(k) or {}).get("chg24")
        if _zahl(v):
            out[key] = round(v, 1)
    return out


def wal_des_tages(d: Daten, sperrliste: set[str], min_mcap: float = 20e6) -> dict | None:
    """Coin mit der groessten Wal-Veraenderung in 7 Tagen (Prozentpunkte der Gesamtmenge, Bot 9.10).

    Rueckfall, solange wale_7d fehlt (aelterer Bot oder < 7 Tage Daten): hoechster aktueller Wal-Anteil.
    """
    neu, alt = [], []
    for b, c in d.coins.items():
        if b.upper() in sperrliste or (c.get("mcap") or 0) < min_mcap:
            continue
        w7 = (c.get("wale_7d") or {}).get("wal")
        w = (c.get("wale") or {}).get("wal")
        if _zahl(w7) and w7 != 0:
            neu.append((abs(w7), b))
        elif _zahl(w):
            alt.append((w, b))
    if neu:
        base, quelle = max(neu)[1], "7d"
    elif alt:
        base, quelle = max(alt)[1], "anteil"
    else:
        return None
    c = d.coins[base]
    w7 = c.get("wale_7d") or {}
    verlauf = [p for p in (c.get("wale_verlauf") or []) if len(p) >= 3 and _zahl(p[1])]
    return {
        "base": base, "quelle": quelle,
        "wal": (c.get("wale") or {}).get("wal"), "boerse": (c.get("wale") or {}).get("boerse"),
        "wal_7d": w7.get("wal") if quelle == "7d" else None,
        "boerse_7d": w7.get("boerse") if quelle == "7d" else None,
        "holder": c.get("holder"), "holder_7d": c.get("holder_7d"),
        "chg24": c.get("chg24"),
        "verlauf": verlauf,
    }
