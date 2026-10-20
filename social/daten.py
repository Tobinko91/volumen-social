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
