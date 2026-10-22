"""Freigabe-Dienst: wartet auf Knopfdruecke von Tobias im Redaktions-Bot und postet dann.

Laeuft dauerhaft als systemd-Dienst (deploy/volumen-social-freigabe.service), Benutzer "redaktion".
Knoepfe: Telegram-Kanal, X, beide, verwerfen. Befehle: /status, /sperre BTC, /entsperre BTC, /pause, /weiter.
Nur Nachrichten aus Tobias' Chat werden beachtet.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import kanaele  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))
API = "https://api.telegram.org/bot{token}/{methode}"
PAUSE = AUSGABE / ".pause"   # hier darf der Benutzer "redaktion" schreiben


def geheim() -> dict:
    p = BASIS / "secrets.yaml"
    return (yaml.safe_load(p.read_text()) if p.exists() else {}) or {}


def tg(g: dict, methode: str, **daten):
    r = requests.post(API.format(token=g["telegram_token"], methode=methode), json=daten, timeout=70)
    return r.json()


def posten(g: dict, beitrag_id: str, ziel: str) -> str:
    ordner = AUSGABE / Path(beitrag_id).name          # nur Ordnername, kein Pfad von aussen
    if not (ordner / "post.png").exists():
        return "Beitrag nicht mehr vorhanden (Videos/Bilder werden nach 3 Tagen gelöscht)."
    status_p = ordner / "gepostet.json"
    status = json.loads(status_p.read_text()) if status_p.exists() else {}
    if ziel == "nein":
        status["verworfen"] = time.time()
        status_p.write_text(json.dumps(status))
        return "🗑 Verworfen."
    ziele = ["telegram", "x"] if ziel == "alle" else [{"tg": "telegram", "x": "x"}[ziel]]
    texte = {"telegram": (ordner / "post_telegram.txt").read_text(encoding="utf-8"),
             "x": (ordner / "post_x.txt").read_text(encoding="utf-8")}
    zeilen = []
    for z in ziele:
        if z in status:
            zeilen.append(f"{z}: schon gepostet ({status[z]})")
            continue
        try:
            link = kanaele.POSTER[z](g, ordner / "post.png", texte[z])
            status[z] = link
            zeilen.append(f"✅ {z}: {link}")
        except kanaele.NichtEingerichtet as e:
            zeilen.append(f"⚙️ {z}: {e}")
        except Exception as e:
            zeilen.append(f"❌ {z}: {e}")
    status_p.write_text(json.dumps(status))
    return "\n".join(zeilen)


def befehl(g: dict, text: str) -> str:
    teile = text.strip().split()
    cmd = teile[0].lower().split("@")[0]
    sperr = BASIS / "sperrliste.txt"
    if cmd == "/status":
        k = kanaele.verfuegbar(g)
        offen = sum(1 for o in AUSGABE.glob("*/post.png") if not (o.parent / "gepostet.json").exists())
        return (f"Kanäle: Telegram {'✅' if k['telegram'] else '–'}, X {'✅' if k['x'] else '–'}\n"
                f"Offene Vorschläge: {offen}\nPause: {'ja' if PAUSE.exists() else 'nein'}")
    if cmd in ("/sperre", "/entsperre") and len(teile) > 1:
        coin = teile[1].upper().strip("$#")
        alt = [z for z in (sperr.read_text().splitlines() if sperr.exists() else []) if z.split("#")[0].strip()]
        neu = [z for z in alt if z.split("#")[0].strip().upper() != coin]
        if cmd == "/sperre":
            neu.append(coin)
        sperr.write_text("\n".join(neu) + "\n")
        return f"Sperrliste: {', '.join(z.strip() for z in neu) or 'leer'}"
    if cmd == "/pause":
        PAUSE.touch()
        return "⏸ Pause: keine neuen Vorschläge, bis du /weiter schreibst."
    if cmd == "/weiter":
        PAUSE.unlink(missing_ok=True)
        return "▶️ Geht weiter."
    return "Befehle: /status, /sperre BTC, /entsperre BTC, /pause, /weiter"


def schleife():
    offset = None
    while True:
        g = geheim()
        if not g.get("telegram_token"):
            time.sleep(60)
            continue
        chef = str(g.get("telegram_chat_id"))
        try:
            antw = tg(g, "getUpdates", offset=offset, timeout=50, allowed_updates=["message", "callback_query"])
        except Exception as e:
            print("Telegram nicht erreichbar:", e, flush=True)
            time.sleep(15)
            continue
        for u in antw.get("result", []):
            offset = u["update_id"] + 1
            if "callback_query" in u:
                c = u["callback_query"]
                if str(c["from"]["id"]) != chef:
                    continue
                teile = (c.get("data") or "").split("|", 2)
                if len(teile) == 3 and teile[0] == "p":
                    tg(g, "answerCallbackQuery", callback_query_id=c["id"], text="Wird erledigt …")
                    ergebnis = posten(g, teile[2], teile[1])
                    tg(g, "sendMessage", chat_id=chef, text=ergebnis, disable_web_page_preview=True,
                       reply_to_message_id=c["message"]["message_id"])
            elif "message" in u:
                m = u["message"]
                if str(m["chat"]["id"]) == chef and (m.get("text") or "").startswith("/"):
                    tg(g, "sendMessage", chat_id=chef, text=befehl(g, m["text"]))


if __name__ == "__main__":
    schleife()
