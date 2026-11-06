"""Taegliche Folge-Liste an Tobias (Redaktions-Bot). Aufruf aus plan.sh:
    python3 tools/folgen.py --senden
X: ein Knopf "allen folgen" (freigabe.py fuehrt es aus). Instagram/TikTok/YouTube: Links zum Selbst-Antippen.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from social import folgen  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))
STAND = AUSGABE / "folgen_stand.json"
NAMEN_PL = folgen.NAMEN


def main(senden=None, schreiber=None, yt_holen=None, yt_schreiber=None, yt_suche=None) -> int:
    cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
    f = cfg.get("folgen") or {}
    stand = folgen.stand_laden(STAND)
    datum = folgen.heute()
    a = folgen.auswahl(folgen.liste(), stand, int(f.get("x_pro_tag", 10)), int(f.get("andere_pro_tag", 5)),
                       f.get("je_plattform"), datum, int(f.get("sperr_tage", 7)))
    begriffe = folgen.begriffe_heute(f.get("suchbegriffe") or [], datum)
    a["suche"] = folgen.suchlinks(begriffe)
    gp = BASIS / "secrets.yaml"
    g = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    kommentare = []
    # 06.11.2026 Tobias: jeden Tag NEUE Links. YouTube: frische Videos aus der Suche statt immer derselben Kanaele
    if g.get("youtube_api_key") and int(f.get("youtube_videos", 10)):
        try:
            a["videos"] = (yt_suche or folgen.youtube_suche)(g["youtube_api_key"], begriffe or ["bitcoin"], 24,
                                                             int(f.get("youtube_videos", 10)),
                                                             set(stand.get("videos", [])))
        except Exception as e:
            print("YouTube-Suche fehlgeschlagen:", e)
    if f.get("kommentare", True) and (a["andere"] or a.get("videos")):   # Wunsch Tobias 02.11.: Kommentare zum Einkopieren
        try:
            from social import daten
            from social import kommentare as km
            try:
                markt = daten.marktlage(daten.laden(cfg["daten"]["dir"], cfg["daten"]["max_alter_min"]))
            except Exception:
                markt = None   # ohne Marktdaten trotzdem Kommentare zum aktuellen Anlass
            fakten = dict(km.fakten_aus_markt(markt), current_events=km.anlaesse())
            # YouTube: neuestes Video lesen und den Kommentar genau dazu schreiben (wie bei X)
            videos = list(a.get("videos") or [])
            if g.get("youtube_api_key"):
                for k in a["andere"]:
                    if k["plattform"] == "youtube":
                        try:
                            v = (yt_holen or folgen.youtube_neuestes)(k["name"], g["youtube_api_key"])
                        except Exception as e:
                            print("YouTube-Video nicht gelesen:", k["name"], e)
                            v = None
                        if v:
                            k["video"] = v
                            videos.append(v)
            if videos:
                try:
                    vs = (yt_schreiber or (lambda ps: km.schreiben(ps, fakten, cfg, g["anthropic_api_key"])))(videos)
                    nach_id = {v["id"]: v for v in videos}
                    for vor in vs:
                        v = nach_id.get(str(vor.get("id")))
                        if v and not km.pruefen(vor["text"], v["text"], fakten, cfg, set()):
                            ziel = next((k for k in a["andere"] if k.get("video") is v), v)
                            ziel["kommentar"] = vor["text"]
                except Exception as e:
                    print("YouTube-Kommentare nicht geschrieben:", e)
            rest = sum(1 for k in a["andere"] if not k.get("kommentar"))
            kommentare = (schreiber or folgen.kommentare_schreiben)(rest, fakten, cfg, g.get("anthropic_api_key"))
        except Exception as e:
            print("Kommentare für die Folge-Liste nicht geschrieben:", e)
    stand.setdefault("heute", {})[datum] = {"x": [k["name"] for k in a["x"]],
                                           "andere": [f"{k['plattform']}:{k['name'].lower()}" for k in a["andere"]]}
    stand["heute"] = dict(list(stand["heute"].items())[-14:])
    stand["videos"] = (stand.get("videos", []) + [v["id"] for v in a.get("videos") or []])[-2000:]
    for k in a["x"] + a["andere"]:   # gezeigt merken: Reihenfolge und 7-Tage-Sperre (keine Wiederholungen)
        stand.setdefault("gezeigt", {})[f"{k['plattform']}:{k['name'].lower()}"] = datum
    text, knoepfe = folgen.nachricht(a, datum, kommentare)
    nummern = sorted((k for k in a["andere"] + list(a.get("videos") or []) if k.get("nr")), key=lambda k: k["nr"])
    if nummern:   # Knoepfe „✅ 1..n“ (Wunsch Tobias 06.11.2026), darunter die bisherigen Knoepfe
        from social import kommentiert
        lauf = "f" + datum.replace("-", "")[2:]
        kommentiert.lauf_merken(AUSGABE / "kommentiert.json", lauf, [
            {"plattform": NAMEN_PL.get(k.get("plattform"), "YouTube"), "konto": k.get("name") or k.get("konto", ""),
             "link": k.get("link") or folgen.LINKS[k["plattform"]].format(n=k["name"])} for k in nummern])
        knoepfe = kommentiert.knoepfe(lauf, len(nummern), (knoepfe or {}).get("inline_keyboard"))
    print(text)
    if "--senden" in sys.argv or senden:
        from social import telegram
        ergebnis = telegram.an_tobias(g, text, knoepfe, post=senden or requests.post)
        print("Gesendet:", ergebnis)
    AUSGABE.mkdir(parents=True, exist_ok=True)
    folgen.stand_speichern(STAND, stand)
    return 0


if __name__ == "__main__":
    sys.exit(main())
