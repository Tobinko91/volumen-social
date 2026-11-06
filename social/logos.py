"""Coin-Logos als Hingucker (Wunsch Tobias 06.11.2026: „Why did it move?“ und Wal des Tages mit Logo im Titelbild).

Quelle: CoinGecko-Schnittstelle (Coin-Bilder der Projekte; gezeigt unveraendert, nur im News-Zusammenhang).
Gleiches Kuerzel bei mehreren Coins (z. B. ALT): es zaehlt nur der Coin, dessen Marktwert zum Bot passt
(Faktor 0,5 bis 2). Passt keiner, gibt es kein Logo (lieber keins als ein falsches).
Ablage: <BASIS>/logos/<BASE>.png, Fehlversuche 24 Std. gemerkt (logos.json).
"""
from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path

import requests

MARKETS = "https://api.coingecko.com/api/v3/coins/markets"


def kandidat(rows: list[dict], base: str, mcap: float | None) -> dict | None:
    rows = [r for r in rows or [] if str(r.get("symbol", "")).upper() == base.upper() and r.get("image")]
    if not rows:
        return None
    if not mcap:
        return rows[0] if len(rows) == 1 else None   # ohne Marktwert nur eindeutige Kuerzel
    passend = [r for r in rows if r.get("market_cap") and 0.5 <= r["market_cap"] / mcap <= 2]
    return min(passend, key=lambda r: abs(r["market_cap"] / mcap - 1)) if passend else None


def logo(base: str, mcap: float | None, ziel: Path, get=requests.get, jetzt: float | None = None) -> Path | None:
    """Pfad zum Logo (PNG, quadratisch) oder None."""
    from PIL import Image
    jetzt = jetzt or time.time()
    ziel.mkdir(parents=True, exist_ok=True)
    p = ziel / f"{base.upper()}.png"
    if p.exists():
        return p
    stand_p = ziel / "logos.json"
    try:
        stand = json.loads(stand_p.read_text())
    except Exception:
        stand = {}
    if jetzt - stand.get(base.upper(), 0) < 86400:   # gestern schon erfolglos
        return None
    try:
        rows = get(MARKETS, params={"vs_currency": "usd", "symbols": base.lower(), "include_tokens": "all"},
                   timeout=20).json()
        k = kandidat(rows if isinstance(rows, list) else [], base, mcap)
        if not k:
            raise ValueError("kein passender Coin")
        bild = Image.open(BytesIO(get(k["image"], timeout=20).content)).convert("RGBA")
        bild.thumbnail((400, 400))
        bild.save(p)
        return p
    except Exception as e:
        print("Logo nicht geholt:", base, e)
        stand[base.upper()] = jetzt
        stand_p.write_text(json.dumps(stand))
        return None
