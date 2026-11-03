"""Muster in ECHTEN Kerzen finden (Wunsch Tobias 03.11.2026): Lern-Videos zeigen bei Chart-Themen einen echten
BTC-Chart statt einer Illustration, mit der markierten Stelle.

- liquiditaet: ein auffaelliges Tief (lokales Minimum), spaeter kurz unterschritten (Docht, hoechstens 4 % darunter),
  Schluss wieder darueber, danach steigt der Kurs = „Stops geholt, dann Wende“.
- unterstuetzung: Preiszone mit mindestens 2 Tiefs (Unterstuetzung) bzw. 2 Hochs (Widerstand) innerhalb 1,5 %;
  dazu ehrlich, ob die Unterstuetzung spaeter klar gebrochen wurde oder bisher hielt.
Pump-and-dump bleibt IMMER Illustration: einen echten Coin so zu zeigen, waere eine Unterstellung.
Nichts gefunden -> None, dann zeigt das Video die Illustration.
"""
from __future__ import annotations


def _tiefs(k: list[dict], breite: int = 3) -> list[int]:
    return [i for i in range(breite, len(k) - breite)
            if k[i]["l"] == min(x["l"] for x in k[i - breite:i + breite + 1])]


def _hochs(k: list[dict], breite: int = 3) -> list[int]:
    return [i for i in range(breite, len(k) - breite)
            if k[i]["h"] == max(x["h"] for x in k[i - breite:i + breite + 1])]


def liquiditaet(k: list[dict], max_unter: float = 0.04, nachlauf: int = 3, anstieg: float = 0.01) -> dict | None:
    """Juengster Fall: Tief i, spaeter Kerze j mit Docht unter l[i] (hoechstens max_unter), Schluss ueber l[i],
    und nachlauf Kerzen spaeter liegt der Schluss mindestens anstieg ueber dem Schluss von j."""
    tiefs = _tiefs(k)
    for j in range(len(k) - 1 - nachlauf, 5, -1):
        for i in reversed([t for t in tiefs if 5 <= j - t <= 40]):
            tief = k[i]["l"]
            if not (tief * (1 - max_unter) <= k[j]["l"] < tief and k[j]["c"] > tief):
                continue
            if any(x["l"] < tief for x in k[i + 1:j]):   # dazwischen schon unterschritten -> kein sauberes Tief
                continue
            if k[j + nachlauf]["c"] >= k[j]["c"] * (1 + anstieg):
                return {"tief_index": i, "docht_index": j, "tief": tief, "docht": k[j]["l"]}
    return None


def _zone(punkte: list[tuple[int, float]], band: float = 0.015) -> dict | None:
    beste = None
    for i, p in punkte:
        treffer = [(j, q) for j, q in punkte if abs(q - p) <= p * band]
        treffer = [t for n, t in enumerate(treffer) if n == 0 or t[0] - treffer[n - 1][0] >= 5]
        if len(treffer) >= 2:
            kandidat = (len(treffer), max(j for j, _ in treffer), treffer)
            if not beste or kandidat[:2] > beste[:2]:
                beste = kandidat
    if not beste:
        return None
    werte = [q for _, q in beste[2]]
    return {"unten": min(werte), "oben": max(werte), "beruehrungen": [j for j, _ in beste[2]]}


def unterstuetzung(k: list[dict]) -> dict | None:
    s = _zone([(i, k[i]["l"]) for i in _tiefs(k)])
    r = _zone([(i, k[i]["h"]) for i in _hochs(k)])
    if not s or not r or r["unten"] <= s["oben"] * 1.01:
        return None
    letzte = max(s["beruehrungen"])
    bruch = next((j for j in range(letzte + 1, len(k)) if k[j]["c"] < s["unten"] * 0.99), None)
    return {"support": s, "resistance": r, "bruch_index": bruch}
