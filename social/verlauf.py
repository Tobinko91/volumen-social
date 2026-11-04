"""Funding- und Open-Interest-Verlauf je Coin (Wunsch Tobias 04.11.2026). Der Bot liefert nur den aktuellen Stand,
darum schreibt die Redaktion stuendlich mit: ausgabe/verlauf/<BASE>.jsonl, eine Zeile je Stunde, 7 Tage.
Damit kann „Why did it move?“ sagen: „Funding went from +0.01% to -0.29% in 6 hours.“"""
from __future__ import annotations

import json
import time
from pathlib import Path

FELDER = ("price", "funding", "oi", "oi_chg4h", "spot_anteil")
HALTEN = 7 * 86400


def speichern(coins: dict, ordner: Path, jetzt: float | None = None) -> int:
    jetzt = jetzt or time.time()
    ordner.mkdir(parents=True, exist_ok=True)
    n = 0
    for base, c in coins.items():
        if c.get("funding") is None and c.get("oi") is None:
            continue
        p = ordner / f"{Path(base).name.upper()}.jsonl"
        alt = laden(ordner, base, jetzt)
        if alt and jetzt - alt[-1]["ts"] < 1800:   # hoechstens eine Zeile je halbe Stunde
            continue
        zeilen = [z for z in alt if jetzt - z["ts"] <= HALTEN]
        zeilen.append({"ts": int(jetzt), **{k: c.get(k) for k in FELDER}})
        p.write_text("".join(json.dumps(z) + "\n" for z in zeilen))
        n += 1
    return n


def laden(ordner: Path, base: str, jetzt: float | None = None) -> list[dict]:
    p = ordner / f"{Path(base).name.upper()}.jsonl"
    if not p.exists():
        return []
    out = []
    for z in p.read_text().splitlines():
        try:
            out.append(json.loads(z))
        except ValueError:
            continue
    return sorted(out, key=lambda z: z["ts"])


def vor(verlauf: list[dict], stunden: float, feld: str, jetzt: float | None = None) -> float | None:
    """Wert vor etwa `stunden` Stunden (naechster Eintrag innerhalb +-1 Std.), sonst None."""
    ziel = (jetzt or time.time()) - stunden * 3600
    beste = min(verlauf, key=lambda z: abs(z["ts"] - ziel), default=None)
    if not beste or abs(beste["ts"] - ziel) > 3600:
        return None
    return beste.get(feld)
