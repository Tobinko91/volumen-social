"""Taeglicher Gesundheits-Check (Wunsch Tobias 02.11.2026), 09:00 an Tobias im Redaktions-Bot.

Anlass: Folge-Liste und Kommentar-Vorschlaege kamen tagelang nicht an, die Fehler standen nur im Server-Protokoll.
Prueft fuer GESTERN:
- Tagesplan: lief jeder feste Termin (Marker „Plan HH:MM erledigt“ im Plan-Protokoll)?
- Vorschlaege je Format, gepostet / verworfen / offen (Ordner + protokoll.jsonl)
- Fehler im Plan-Protokoll: Claude, X, Telegram, Programmabsturz, Stimme; News-Quellen, die bei jedem Lauf scheitern
- haengende geplante Posts (S31), Update-Stand (Tests fehlgeschlagen?), Alter der Bot-Daten, freier Speicher, Stimme
    sudo -u redaktion env SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe \
      python3 tools/gesundheit.py [--senden] [--datum 2026-11-02]
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))
PLAN_LOG = Path("/var/log/volumen-social-plan.log")
UPDATE_LOG = Path("/var/log/volumen-social-update.log")

# Feste Termine (deutsche Zeit) mit Namen, wie in tools/plan.sh
TERMINE = {"14:30": "Markt", "15:00": "News", "15:30": "Kommentare", "16:00": "Coin-Check", "17:30": "Folge-Liste",
           "19:00": "Wal", "20:00": "News", "20:30": "Kommentare", "21:00": "News", "21:30": "Lernen"}
FEHLER = [("Claude-Fehler", "Claude-Antwort unlesbar"), ("X-Posts nicht geholt", "X-Abfrage fehlgeschlagen"),
          ("Telegram hat die Nachricht abgelehnt", "Telegram lehnte Nachricht ab"),
          ("Traceback", "Programmabsturz"), ("Stimme fehlgeschlagen", "Stimme fehlgeschlagen"),
          ("Keine Wal-Daten", "keine Wal-Daten"), ("DatenFehler", "Bot-Daten fehlen/zu alt")]
FORMAT_NAMEN = {"markt": "Markt", "markt_video": "Markt-Video", "news": "News", "coincheck": "Coin-Check",
                "wal": "Wal", "wal_video": "Wal-Video", "wissen": "Lernen", "wissen_video": "Lern-Video",
                "karussell": "Karussell", "termine": "Termine", "redaktion": "Redaktion",
                "warum_video": "Why did it move?"}


def plan_abschnitte(text: str, tag: str) -> dict[str, list[str]]:
    """Plan-Protokoll in Abschnitte je Termin von TAG zerlegen: {'14:30': [Zeilen der Ausgabe], ...}."""
    out, puffer = {}, []
    for z in text.splitlines():
        m = re.match(r"(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2} Plan (\d{2}:\d{2}) erledigt", z)
        if m:
            if m.group(1) == tag:
                out[m.group(2)] = puffer
            puffer = []
        else:
            puffer.append(z)
    return out


def fehler_zaehlen(abschnitte: dict[str, list[str]]) -> tuple[Counter, Counter, int]:
    """-> (Fehlerarten mit Termin, Quellen-Fehler je Quelle, Anzahl News-Laeufe)."""
    arten, quellen, laeufe = Counter(), Counter(), 0
    for slot, zeilen in abschnitte.items():
        for z in zeilen:
            for muster, name in FEHLER:
                if muster in z:
                    arten[f"{name} ({TERMINE.get(slot, slot)})"] += 1
            if z.startswith("Quellen:"):
                laeufe += 1
                for q, _ in re.findall(r"([\w .\-]+?): Fehler: (\w+)", z[len("Quellen:"):]):
                    quellen[q.strip(" ,")] += 1
    return arten, quellen, laeufe


def vorschlaege(ausgabe: Path, tag: str) -> dict:
    """Ordner von TAG (JJJJMMTT-HHMM_...): je Format Anzahl und Status."""
    from social import bericht
    kurz = tag.replace("-", "")
    je, status = Counter(), Counter()
    for o in ausgabe.glob(f"{kurz}-*"):
        if not o.is_dir():
            continue
        fmt = bericht.format_aus_ordner(o.name)
        je[fmt] += 1
        st = {}
        try:
            st = json.loads((o / "gepostet.json").read_text())
        except Exception:
            pass
        if st.get("verworfen"):
            status["verworfen"] += 1
        elif any(k in st for k in ("telegram", "x", "instagram", "tiktok", "youtube")):
            status["gepostet"] += 1
        else:
            status["offen"] += 1
    for o in ausgabe.glob("chat_*"):   # aus dem Redaktions-Chat (Warteschlange)
        if o.is_dir() and dt.date.fromtimestamp(o.stat().st_mtime).isoformat() == tag:
            je["redaktion"] += 1
    return {"je": je, "status": status}


def haengend(ausgabe: Path, jetzt: float) -> list[str]:
    """Geplante Kanaele (S31), die seit ueber einer Stunde ueberfaellig sind."""
    out = []
    for p in ausgabe.glob("*/gepostet.json"):
        try:
            st = json.loads(p.read_text())
        except Exception:
            continue
        if st.get("verworfen"):
            continue
        for k, wann in (st.get("geplant") or {}).items():
            if k not in st and wann < jetzt - 3600:
                out.append(f"{p.parent.name} → {k}")
    return out


def update_stand(text: str) -> tuple[str, bool]:
    zeilen = [z for z in text.splitlines() if " Update auf " in z or "Tests fehlgeschlagen" in z]
    if not zeilen:
        return "keine Update-Meldung im Protokoll", False
    letzte = zeilen[-1]
    return letzte.strip(), "Tests fehlgeschlagen" in letzte


def daten_alter_min(cfg: dict, jetzt: float) -> float | None:
    try:
        st = json.loads((Path(cfg["daten"]["dir"]) / "stand.json").read_text())
        return (jetzt - st.get("ts", 0)) / 60
    except Exception:
        return None


def bericht_text(tag: str, abschnitte: dict, vs: dict, arten: Counter, quellen: Counter, laeufe: int,
                 haengt: list[str], update: tuple[str, bool], alter: float | None, frei_prozent: float,
                 stimme_ok: bool, pause: bool) -> tuple[str, int]:
    """-> (Nachricht, Anzahl Warnungen)."""
    d = dt.date.fromisoformat(tag)
    z, warn = [f"🩺 <b>Gesundheits-Check {d.day}.{d.month}.</b>", ""], 0
    gelaufen = [s for s in TERMINE if s in abschnitte]
    fehlt = [f"{s} {TERMINE[s]}" for s in TERMINE if s not in abschnitte]
    if pause:
        z.append("⏸ Pause ist an (/weiter schaltet sie aus)")
        warn += 1
    if fehlt:
        z.append(f"⚠️ Tagesplan: {len(gelaufen)}/{len(TERMINE)} Termine gelaufen, fehlt: {', '.join(fehlt)}")
        warn += 1
    else:
        z.append(f"✅ Tagesplan: alle {len(TERMINE)} Termine gelaufen")
    je, st = vs["je"], vs["status"]
    if je:
        teile = ", ".join(f"{FORMAT_NAMEN.get(f, f)} {n}" for f, n in sorted(je.items(), key=lambda x: -x[1]))
        z.append(f"📝 Vorschläge: {sum(je.values())} ({teile})")
        z.append(f"    gepostet {st['gepostet']} · verworfen {st['verworfen']} · ohne Knopfdruck {st['offen']}")
    else:
        z.append("⚠️ Vorschläge: keine")
        warn += 1
    if arten:
        z.append("⚠️ Fehler: " + "; ".join(f"{k} {n}×" for k, n in arten.most_common(6)))
        warn += 1
    else:
        z.append("✅ Fehler: keine")
    kaputt = [q for q, n in quellen.items() if laeufe and n >= max(2, 0.8 * laeufe)]
    if kaputt:
        z.append(f"⚠️ News-Quellen scheitern bei jedem Lauf: {', '.join(sorted(kaputt))}")
        warn += 1
    if haengt:
        z.append(f"⚠️ Geplante Posts hängen: {len(haengt)} ({'; '.join(haengt[:3])})")
        warn += 1
    text, schlecht = update
    if schlecht:
        z.append(f"⚠️ Update: {text}")
        warn += 1
    else:
        z.append(f"✅ Update: {text.split(' Update auf ')[-1] if ' Update auf ' in text else text}")
    if alter is None:
        z.append("⚠️ Bot-Daten: nicht lesbar")
        warn += 1
    elif alter > 60:
        z.append(f"⚠️ Bot-Daten: {alter:.0f} Min. alt (läuft der Bot?)")
        warn += 1
    else:
        z.append(f"✅ Bot-Daten: {alter:.0f} Min. alt")
    if frei_prozent < 15:
        z.append(f"⚠️ Speicher: nur {frei_prozent:.0f} % frei")
        warn += 1
    else:
        z.append(f"✅ Speicher: {frei_prozent:.0f} % frei")
    z.append("✅ Stimme: eingerichtet" if stimme_ok else "🎙 Stimme: noch nicht eingerichtet (Videos ohne Stimme)")
    z += ["", "Alles in Ordnung. 👍" if not warn else f"{warn} Punkt(e) prüfen. Schick mir diese Nachricht im Redaktions-Chat."]
    return "\n".join(z), warn


def main() -> int:
    args = sys.argv[1:]
    jetzt = time.time()
    tag = args[args.index("--datum") + 1] if "--datum" in args else (dt.date.today() - dt.timedelta(days=1)).isoformat()
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    gp = BASIS / "secrets.yaml"
    g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    lies = lambda p: p.read_text(errors="replace") if p.exists() else ""
    abschnitte = plan_abschnitte(lies(PLAN_LOG), tag)
    arten, quellen, laeufe = fehler_zaehlen(abschnitte)
    du = shutil.disk_usage(str(AUSGABE if AUSGABE.exists() else BASIS))
    text, warn = bericht_text(tag, abschnitte, vorschlaege(AUSGABE, tag), arten, quellen, laeufe,
                              haengend(AUSGABE, jetzt), update_stand(lies(UPDATE_LOG)), daten_alter_min(cfg, jetzt),
                              du.free / du.total * 100, bool(g.get("google_tts_key")),
                              (BASIS / "pause").exists() or (AUSGABE / ".pause").exists())
    print(text)
    if "--senden" in args:
        from social import telegram
        print("Gesendet:", telegram.an_tobias(g, text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
