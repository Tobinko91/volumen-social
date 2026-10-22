"""Kursverlaeufe direkt von den oeffentlichen Boersen-Schnittstellen (dieselben Quellen wie der Bot).
Kein Schluessel noetig, der Bot wird nicht angefasst. Erst Bitunix-Futures, sonst Binance Spot."""
from __future__ import annotations

import requests

BITUNIX = "https://fapi.bitunix.com/api/v1/futures/market/kline"
BINANCE = "https://api.binance.com/api/v3/klines"


def _bitunix(base: str, intervall: str, anzahl: int, get) -> list[tuple[int, float]]:
    j = get(BITUNIX, {"symbol": f"{base}USDT", "interval": intervall, "limit": min(anzahl, 200)})
    rows = (j or {}).get("data") or []
    return sorted((int(r["time"]), float(r["close"])) for r in rows)


def _binance(base: str, intervall: str, anzahl: int, get) -> list[tuple[int, float]]:
    rows = get(BINANCE, {"symbol": f"{base}USDT", "interval": intervall, "limit": min(anzahl, 1000)}) or []
    return [(int(r[0]), float(r[4])) for r in rows]


def verlauf(base: str, intervall: str = "1h", anzahl: int = 72, get=None) -> list[tuple[int, float]]:
    """[(zeit_ms, schlusskurs)] aufsteigend; leer, wenn keine Boerse antwortet."""
    get = get or (lambda url, p: requests.get(url, params=p, timeout=15).json())
    for quelle in (_bitunix, _binance):
        try:
            k = quelle(base.upper(), intervall, anzahl, get)
            if len(k) >= 10:
                return k[-anzahl:]
        except Exception:
            continue
    return []
