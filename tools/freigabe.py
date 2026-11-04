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
MUSIK = Path(os.environ.get("SOCIAL_MUSIK", BASIS / "musik"))   # eigene Musikstuecke (Tobias schickt sie dem Bot)
PROTOKOLL = AUSGABE / "protokoll.jsonl"   # dauerhaft (Wochenbericht, Freigabe-Tor); Ordner werden nach 3 Tagen geloescht


def geheim() -> dict:
    p = BASIS / "secrets.yaml"
    return (yaml.safe_load(p.read_text()) if p.exists() else {}) or {}


def tg(g: dict, methode: str, **daten):
    r = requests.post(API.format(token=g["telegram_token"], methode=methode), json=daten, timeout=70)
    return r.json()


def tiktok_entwuerfe_24h(jetzt: float | None = None) -> int:
    """Wie viele TikTok-Entwuerfe in den letzten 24 Std. geschickt wurden (TikTok-Regel: hoechstens 5 offene)."""
    from social import bericht
    seit = (jetzt or time.time()) - 86400
    return sum(1 for e in bericht.protokoll_laden(PROTOKOLL, seit)
               if e.get("kanal") == "tiktok" and e.get("ereignis") == "gepostet" and "Entwurf" in str(e.get("link", "")))


def reel_bauen(g: dict, ordner: Path) -> str:
    if ordner.name.endswith("_video") or (ordner / "video.mp4").exists() or (ordner / "karussell.json").exists():
        return "🎬 Das ist schon ein Video bzw. eine Bilderserie."
    from social import reel, telegram as _telegram
    try:
        neu, quelle = reel.aus_bild(ordner, kanaele._cfg(), g)
    except Exception as e:
        return f"❌ Reel nicht gebaut: {str(e)[:200]}"
    if quelle == "schon gebaut":
        return "🎬 Reel gibt es schon (Vorschlag weiter oben im Chat)."
    hinweis = f"🎬 Reel aus Bild-Vorschlag · 🎙 Ton: {quelle}"
    if not _telegram.vorschlag_senden(g, neu, hinweis):
        return "⚠️ Reel gebaut, aber Telegram hat die Vorschau abgelehnt."
    return "🎬 Reel gebaut, Vorschau kommt als eigener Vorschlag mit Knöpfen."


def posten(g: dict, beitrag_id: str, ziel: str) -> str:
    ordner = AUSGABE / Path(beitrag_id).name          # nur Ordnername, kein Pfad von aussen
    video = ordner / "video.mp4"
    medium = video if video.exists() else ordner / "post.png"   # Video-Vorschlag oder Bild-Beitrag
    if not medium.exists():
        return "Beitrag nicht mehr vorhanden (Videos/Bilder werden nach 3 Tagen gelöscht)."
    if ziel == "reel":   # Bild-Vorschlag als 9:16-Reel mit Stimme, kommt als neuer Video-Vorschlag (04.11.2026)
        return reel_bauen(g, ordner)
    from social import karussell_posten, video_posten
    ist_karussell = medium != video and (ordner / "karussell.json").exists()   # S11: Bilderserie
    poster = (video_posten.POSTER if medium == video
              else karussell_posten.POSTER if ist_karussell else kanaele.POSTER)
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
        # YouTube nur per eigenem Knopf, solange Uploads privat sind (Wunsch Tobias 02.11.2026, config youtube.in_alle)
        if medium == video and k.get("youtube") and (kanaele._cfg().get("youtube") or {}).get("in_alle", False):
            ziele.append("youtube")
        # S31: Instagram/TikTok/YouTube zur US-Hauptzeit, Telegram/X sofort; News/Redaktion ueberall sofort
        from social import zeitplan
        ziele, spaeter = zeitplan.aufteilen(ziele, bericht.format_aus_ordner(ordner.name),
                                            medium != video and not ist_karussell, kanaele._cfg(), time.time())
        if spaeter:
            status.setdefault("geplant", {}).update({k: v for k, v in spaeter.items() if k not in status})
            status_p.write_text(json.dumps(status))
    else:
        ziele = [{"tg": "telegram", "x": "x", "ig": "instagram", "tt": "tiktok", "yt": "youtube"}[ziel]]
        if ziele == ["youtube"] and medium != video:
            return ("▶️ YouTube nimmt nur Videos (Shorts). Dieser Vorschlag ist "
                    + ("eine Bilderserie." if ist_karussell else "ein Bild."))
    tg_text = (ordner / "post_telegram.txt").read_text(encoding="utf-8")
    texte = {"telegram": tg_text, "instagram": tg_text, "tiktok": tg_text, "youtube": tg_text,   # wandeln selbst um
             "x": (ordner / "post_x.txt").read_text(encoding="utf-8")}
    zeilen = []
    for z in ziele:
        if z in status:
            if "Entwurf" in str(status[z]):   # TikTok bis zur App-Pruefung: nur Entwurf, Tobias postet in der App
                zeilen.append(f"🎵 {z}: schon als ENTWURF an TikTok geschickt, noch nicht öffentlich. In der TikTok-App: "
                              "Posteingang → „Systembenachrichtigungen“ → „Dein Inhalt … ist bereit“ → antippen → Posten.")
            else:
                zeilen.append(f"{z}: schon gepostet ({status[z]})")
            continue
        if z == "tiktok" and tiktok_entwuerfe_24h() >= 5:   # TikTok: max. 5 OFFENE Entwuerfe in 24 Std.
            zeilen.append("⚠️ tiktok: schon 5 Entwürfe in 24 Std. geschickt. TikTok nimmt nur 5 OFFENE an – sind die "
                          "alten noch nicht gepostet, kommt dieser nicht an. Erst alte Entwürfe in der App posten.")
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
    for k, v in (status.get("geplant") or {}).items():
        if ziel == "alle" and k not in status:
            from social import zeitplan as _zp
            zeilen.append(f"⏰ {k}: geplant um {_zp.uhr(v)} (US-Hauptzeit)")
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
    if cmd == "/musik":
        if len(teile) > 2 and teile[1].lower() == "weg" and teile[2].isdigit():
            from social import musik
            stuecke = sorted(f for f in MUSIK.glob("*") if f.suffix.lower() in musik.ENDUNGEN)
            i = int(teile[2]) - 1
            if 0 <= i < len(stuecke):
                stuecke[i].unlink()
                return f"🗑 {stuecke[i].name} gelöscht.\n" + musik_liste()
        return musik_liste()
    if cmd == "/pause":
        PAUSE.touch()
        return "⏸ Pause: keine neuen Vorschläge, bis du /weiter schreibst."
    if cmd == "/weiter":
        PAUSE.unlink(missing_ok=True)
        return "▶️ Geht weiter."
    return "Befehle: /check AKE, /status, /auto (an/aus), /musik, /sperre BTC, /entsperre BTC, /pause, /weiter"


def musik_speichern(g: dict, m: dict, holen=requests.get) -> str:
    """Tobias schickt dem Redaktions-Bot eine Audiodatei (z. B. von Pixabay) -> landet im Musik-Ordner der Videos."""
    import re as _re
    datei = m.get("audio") or m.get("document") or {}
    name = datei.get("file_name") or (datei.get("title") or "stueck") + ".mp3"
    if not (m.get("audio") or (datei.get("mime_type") or "").startswith("audio/")
            or name.lower().endswith((".mp3", ".m4a", ".wav", ".aac"))):
        return "Das ist keine Audiodatei. Bitte eine mp3 schicken."
    info = tg(g, "getFile", file_id=datei["file_id"])
    if not info.get("ok"):
        return "Datei zu groß oder nicht abrufbar (Telegram-Grenze für Bots: 20 MB)."
    url = f"https://api.telegram.org/file/bot{g['telegram_token']}/{info['result']['file_path']}"
    r = holen(url, timeout=120)
    r.raise_for_status()
    MUSIK.mkdir(parents=True, exist_ok=True)
    sauber = _re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name)[:80] or "stueck.mp3"
    (MUSIK / sauber).write_bytes(r.content)
    return f"🎵 Gespeichert: {sauber}\n" + musik_liste()


def musik_liste() -> str:
    from social import musik
    stuecke = sorted(f.name for f in MUSIK.glob("*") if f.suffix.lower() in musik.ENDUNGEN) if MUSIK.exists() else []
    if not stuecke:
        return "Noch keine Musik. Schick mir mp3-Dateien, dann laufen sie unter den Videos (jeden Tag ein anderes Stück)."
    return f"Musik ({len(stuecke)} Stücke, täglich wechselnd):\n" + "\n".join(
        f"{i}. {n}" for i, n in enumerate(stuecke, 1)) + "\nLöschen: /musik weg 2"


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
                elif str(m["chat"]["id"]) == chef and (m.get("audio") or m.get("document")):
                    try:
                        antwort = musik_speichern(g, m)
                    except Exception as e:
                        antwort = f"❌ Musik nicht gespeichert: {e}"
                    tg(g, "sendMessage", chat_id=chef, text=antwort)


if __name__ == "__main__":
    schleife()
