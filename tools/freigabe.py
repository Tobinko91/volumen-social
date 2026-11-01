"""Freigabe-Dienst: wartet auf Knopfdruecke von Tobias im Redaktions-Bot und postet dann.

Laeuft dauerhaft als systemd-Dienst (deploy/volumen-social-freigabe.service), Benutzer "redaktion".
Knoepfe: Telegram-Kanal, X, Instagram, alle eingerichteten Kanaele, verwerfen; Folge-Liste (X allen folgen). Befehle: /check AKE, /status, /sperre BTC, /entsperre BTC, /pause, /weiter.
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
PROTOKOLL = AUSGABE / "protokoll.jsonl"   # dauerhaft (Wochenbericht, Freigabe-Tor); Ordner werden nach 3 Tagen geloescht


def geheim() -> dict:
    p = BASIS / "secrets.yaml"
    return (yaml.safe_load(p.read_text()) if p.exists() else {}) or {}


def tg(g: dict, methode: str, **daten):
    r = requests.post(API.format(token=g["telegram_token"], methode=methode), json=daten, timeout=70)
    return r.json()


def posten(g: dict, beitrag_id: str, ziel: str) -> str:
    ordner = AUSGABE / Path(beitrag_id).name          # nur Ordnername, kein Pfad von aussen
    video = ordner / "video.mp4"
    medium = video if video.exists() else ordner / "post.png"   # Video-Vorschlag oder Bild-Beitrag
    if not medium.exists():
        return "Beitrag nicht mehr vorhanden (Videos/Bilder werden nach 3 Tagen gelöscht)."
    from social import video_posten
    poster = video_posten.POSTER if medium == video else kanaele.POSTER
    status_p = ordner / "gepostet.json"
    status = json.loads(status_p.read_text()) if status_p.exists() else {}
    from social import bericht
    if ziel == "nein":
        status["verworfen"] = time.time()
        status_p.write_text(json.dumps(status))
        bericht.protokollieren(PROTOKOLL, ordner.name, "verworfen")
        return "🗑 Verworfen."
    if ziel == "alle":   # Telegram und X immer (Fehlermeldung, falls nicht eingerichtet), Instagram nur wenn eingerichtet
        k = kanaele.verfuegbar(g)
        ziele = ["telegram", "x"] + [z for z in ("instagram", "tiktok") if k[z]]
        if medium == video and k.get("youtube"):
            ziele.append("youtube")
    else:
        ziele = [{"tg": "telegram", "x": "x", "ig": "instagram", "tt": "tiktok", "yt": "youtube"}[ziel]]
        if ziele == ["youtube"] and medium != video:
            return "▶️ YouTube nimmt nur Videos (Shorts). Dieser Vorschlag ist ein Bild."
    tg_text = (ordner / "post_telegram.txt").read_text(encoding="utf-8")
    texte = {"telegram": tg_text, "instagram": tg_text, "tiktok": tg_text, "youtube": tg_text,   # wandeln selbst um
             "x": (ordner / "post_x.txt").read_text(encoding="utf-8")}
    zeilen = []
    for z in ziele:
        if z in status:
            zeilen.append(f"{z}: schon gepostet ({status[z]})")
            continue
        try:
            from social import design
            text = kanaele.telegram_hinweis(texte[z], z, g, design.SPRACHE)   # „First on Telegram“
            link = poster[z](g, medium, text)
            status[z] = link
            zeilen.append(f"✅ {z}: {link}")
            bericht.protokollieren(PROTOKOLL, ordner.name, "gepostet", z, link)
            if z == "tiktok" and medium == video and "Entwurf" in str(link):
                # TikTok nimmt fuer Video-Entwuerfe keinen Text an -> fertigen Text zum Antippen/Kopieren schicken
                import html as _html
                from social import tiktok as _tt
                _, beschreibung = _tt.titel_und_text(text, design.SPRACHE)
                tg(g, "sendMessage", chat_id=g.get("telegram_chat_id"), parse_mode="HTML",
                   text="🎵 TikTok-Text (antippen = kopiert):\n<code>" + _html.escape(beschreibung[:3800]) + "</code>")
            if z == "instagram" and (kanaele._cfg().get("instagram") or {}).get("story", True):
                try:   # Punkt C: jeden Instagram-Beitrag auch als Story (Fehler hier stoppen nichts)
                    from social import story
                    status["instagram_story"] = story.posten(g, medium)
                    zeilen.append("✅ instagram: auch als Story geteilt")
                except Exception as e:
                    zeilen.append(f"⚠️ Instagram-Story nicht geteilt: {e}")
        except kanaele.NichtEingerichtet as e:
            zeilen.append(f"⚙️ {z}: {e}")
        except Exception as e:
            zeilen.append(f"❌ {z}: {e}")
    status_p.write_text(json.dumps(status))
    return "\n".join(zeilen)


def folge_knopf(g: dict, art: str, datum: str) -> str:
    """Knopf aus der taeglichen Folge-Liste (tools/folgen.py)."""
    from social import folgen
    p = AUSGABE / "folgen_stand.json"
    stand = folgen.stand_laden(p)
    tag = (stand.get("heute") or {}).get(datum)
    if not tag:
        return "Diese Folge-Liste ist zu alt. Die nächste kommt morgen."
    if art == "ok":
        for k in tag.get("andere", []):
            stand.setdefault("erledigt", {})[k] = int(time.time())
        tag["andere"] = []
        folgen.stand_speichern(p, stand)
        return "☑️ Danke, als erledigt gemerkt."
    namen = [n for n in tag.get("x", []) if f"x:{n.lower()}" not in stand.get("erledigt", {})]
    if not namen:
        return "X: schon erledigt."
    try:
        zeilen = folgen.x_folgen(g, namen, stand)
    except folgen.FolgenFehler as e:
        zeilen = [f"❌ X: {e}"]
    folgen.stand_speichern(p, stand)
    return "👥 X-Folgen:\n" + "\n".join(zeilen)


def befehl(g: dict, text: str) -> str:
    teile = text.strip().split()
    cmd = teile[0].lower().split("@")[0]
    sperr = BASIS / "sperrliste.txt"
    if cmd == "/status":
        k = kanaele.verfuegbar(g)
        offen = sum(1 for o in AUSGABE.glob("*/post.png") if not (o.parent / "gepostet.json").exists())
        return (f"Kanäle: Telegram {'✅' if k['telegram'] else '–'}, X {'✅' if k['x'] else '–'}, "
                f"Instagram {'✅' if k['instagram'] else '–'}, TikTok {'✅' if k['tiktok'] else '–'}, "
                f"YouTube {'✅' if k.get('youtube') else '–'}\n"
                f"Offene Vorschläge: {offen}\nPause: {'ja' if PAUSE.exists() else 'nein'}")
    if cmd in ("/sperre", "/entsperre") and len(teile) > 1:
        coin = teile[1].upper().strip("$#")
        alt = [z for z in (sperr.read_text().splitlines() if sperr.exists() else []) if z.split("#")[0].strip()]
        neu = [z for z in alt if z.split("#")[0].strip().upper() != coin]
        if cmd == "/sperre":
            neu.append(coin)
        sperr.write_text("\n".join(neu) + "\n")
        return f"Sperrliste: {', '.join(z.strip() for z in neu) or 'leer'}"
    if cmd == "/check" and len(teile) > 1:
        import subprocess
        coin = teile[1].upper().strip("$#")
        if not coin.isalnum() or len(coin) > 15:
            return "Bitte nur den Ticker, z. B. /check AKE"
        app = Path(__file__).resolve().parent.parent
        subprocess.Popen([sys.executable, str(app / "main.py"), "coincheck", "--coin", coin, "--senden"],
                         cwd=str(app), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"🔎 Coin-Check für {coin} wird erstellt, kommt in etwa einer Minute."
    if cmd == "/auto":   # Freigabe-Tor: Status, /auto aus, /auto an
        from social import autopost, bericht
        aus = autopost.aus_datei(AUSGABE)
        if len(teile) > 1 and teile[1].lower() == "aus":
            aus.touch()
        elif len(teile) > 1 and teile[1].lower() == "an":
            aus.unlink(missing_ok=True)
        return autopost.status(bericht.protokoll_laden(PROTOKOLL), kanaele._cfg(), aus.exists())
    if cmd == "/pause":
        PAUSE.touch()
        return "⏸ Pause: keine neuen Vorschläge, bis du /weiter schreibst."
    if cmd == "/weiter":
        PAUSE.unlink(missing_ok=True)
        return "▶️ Geht weiter."
    return "Befehle: /check AKE, /status, /auto (an/aus), /sperre BTC, /entsperre BTC, /pause, /weiter"


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
                if len(teile) == 3 and teile[0] == "f":
                    tg(g, "answerCallbackQuery", callback_query_id=c["id"], text="Wird erledigt …")
                    tg(g, "sendMessage", chat_id=chef, text=folge_knopf(g, teile[1], teile[2]),
                       disable_web_page_preview=True, reply_to_message_id=c["message"]["message_id"])
                elif len(teile) == 3 and teile[0] == "p":
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
