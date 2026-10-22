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


def kerzen(base: str, intervall: str = "1h", anzahl: int = 168, get=None) -> list[dict]:
    """Kerzen mit Volumen in USD: [{t, o, h, l, c, v}] aufsteigend; leer, wenn keine Boerse antwortet."""
    get = get or (lambda url, p: requests.get(url, params=p, timeout=15).json())
    b = base.upper()
    try:
        out, ende = [], None
        while len(out) < anzahl:   # Bitunix liefert hoechstens 200 je Abruf
            p = {"symbol": f"{b}USDT", "interval": intervall, "limit": min(200, anzahl - len(out))}
            if ende:
                p["endTime"] = ende
            rows = (get(BITUNIX, p) or {}).get("data") or []
            if not rows:
                break
            neu = [{"t": int(r["time"]), "o": float(r["open"]), "h": float(r["high"]), "l": float(r["low"]),
                    "c": float(r["close"]), "v": float(r.get("quoteVol") or 0)} for r in rows]
            out = neu + out
            ende = min(k["t"] for k in neu) - 1
            if len(rows) < p["limit"]:
                break
        out = sorted({k["t"]: k for k in out}.values(), key=lambda k: k["t"])
        if len(out) >= 24:
            return out[-anzahl:]
    except Exception:
        pass
    try:
        rows = get(BINANCE, {"symbol": f"{b}USDT", "interval": intervall, "limit": min(anzahl, 1000)}) or []
        out = [{"t": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4]),
                "v": float(r[7])} for r in rows]
        return out if len(out) >= 24 else []
    except Exception:
        return []


def volumenprofil(k: list[dict], faecher: int = 48) -> tuple[list[float], list[float]]:
    """Volumen je Preisbereich (Grenzen, Volumen). Volumen jeder Kerze gleichmaessig ueber ihre Spanne verteilt."""
    lo, hi = min(x["l"] for x in k), max(x["h"] for x in k)
    if hi <= lo:
        return [lo, hi], [0.0]
    schritt = (hi - lo) / faecher
    grenzen = [lo + i * schritt for i in range(faecher + 1)]
    vol = [0.0] * faecher
    for x in k:
        a = max(0, min(faecher - 1, int((x["l"] - lo) / schritt)))
        b = max(0, min(faecher - 1, int((x["h"] - lo) / schritt)))
        anteil = x["v"] / (b - a + 1)
        for i in range(a, b + 1):
            vol[i] += anteil
    return grenzen, vol


def zonen(k: list[dict], anzahl: int = 1) -> dict:
    """Staerkste Volumen-Bereiche ober- und unterhalb des letzten Kurses (reine Marktdaten, keine Ziele)."""
    grenzen, vol = volumenprofil(k)
    letzt = k[-1]["c"]
    faecher = sorted(range(len(vol)), key=lambda i: -vol[i])
    oben, unten = [], []
    for i in faecher:
        z = {"lo": grenzen[i], "hi": grenzen[i + 1], "vol": vol[i]}
        mitte = (z["lo"] + z["hi"]) / 2
        liste = oben if mitte > letzt else unten
        if len(liste) < anzahl and all(abs(mitte - (y["lo"] + y["hi"]) / 2) > (grenzen[1] - grenzen[0]) * 6
                                       for y in oben + unten):
            liste.append(z)
    return {"oben": sorted(oben, key=lambda z: z["lo"]), "unten": sorted(unten, key=lambda z: -z["lo"]),
            "grenzen": grenzen, "vol": vol}
