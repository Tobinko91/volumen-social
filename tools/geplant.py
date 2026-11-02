"""S31: geplante Kanaele posten, sobald ihre Zeit da ist (laeuft alle 10 Minuten, deploy/plan.cron).

Liest gepostet.json aller Vorschlaege. Eintrag "geplant": {kanal: zeitpunkt}. Faellige Kanaele werden ueber
freigabe.posten gepostet (wie ein Knopfdruck), das Ergebnis geht an Tobias. Verworfene Beitraege und /pause
stoppen geplante Posts.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freigabe  # noqa: E402

KUERZEL = {"telegram": "tg", "x": "x", "instagram": "ig", "tiktok": "tt", "youtube": "yt"}


def faellige(ausgabe: Path, jetzt: float) -> list[tuple[str, str]]:
    out = []
    for p in sorted(ausgabe.glob("*/gepostet.json")):
        try:
            st = json.loads(p.read_text())
        except Exception:
            continue
        if st.get("verworfen"):
            continue
        for k, wann in (st.get("geplant") or {}).items():
            if wann <= jetzt and k not in st:
                out.append((p.parent.name, k))
    return out


def austragen(ausgabe: Path, ordner: str, kanal: str) -> None:
    p = ausgabe / ordner / "gepostet.json"
    st = json.loads(p.read_text())
    (st.get("geplant") or {}).pop(kanal, None)
    p.write_text(json.dumps(st))


def main(jetzt: float | None = None, senden: bool = True) -> list[str]:
    if freigabe.PAUSE.exists():
        return []
    g = freigabe.geheim()
    meldungen = []
    for ordner, kanal in faellige(freigabe.AUSGABE, jetzt or time.time()):
        ergebnis = freigabe.posten(g, ordner, KUERZEL[kanal])
        austragen(freigabe.AUSGABE, ordner, kanal)
        meldungen.append(f"⏰ Geplant gepostet ({ordner}):\n{ergebnis}")
    if senden:
        for m in meldungen:
            freigabe.tg(g, "sendMessage", chat_id=g.get("telegram_chat_id"), text=m[:4000],
                        disable_web_page_preview=True)
    for m in meldungen:
        print(m)
    return meldungen


if __name__ == "__main__":
    main()
