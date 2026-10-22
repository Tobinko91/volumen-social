"""WhaleSqueeze Redaktion – erzeugt ein Kurzvideo aus den Bot-Daten.

Beispiele:
  python main.py markt                         # Daten aus config.yaml (Server)
  python main.py markt --daten beispieldaten   # Probe mit Beispieldaten
"""
from __future__ import annotations

import argparse
import os
import json
import sys
import time
from pathlib import Path

import yaml

from social import (bilder, daten, formate, kurse, news, news_post, news_text, post, pruefung, stimme, telegram,
                    texte, video, wissen)

HIER = Path(__file__).resolve().parent
# Auf dem Server liegen Schluessel und Sperrliste ausserhalb des Codes (/opt/volumen-social),
# damit ein Update sie nie ueberschreibt. Lokal: neben main.py.
GEHEIM_ORDNER = Path(os.environ.get("SOCIAL_GEHEIM", HIER))


def lade_cfg() -> tuple[dict, dict]:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    geheim_p = GEHEIM_ORDNER / "secrets.yaml"
    geheim = yaml.safe_load(geheim_p.read_text(encoding="utf-8")) if geheim_p.exists() else {}
    return cfg, geheim or {}


def lade_sperrliste() -> set[str]:
    p = GEHEIM_ORDNER / "sperrliste.txt"
    if not p.exists():
        return set()
    return {z.split("#")[0].strip().upper() for z in p.read_text(encoding="utf-8").splitlines()
            if z.split("#")[0].strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("format", choices=sorted(formate.FORMATE) + ["wissen", "news"])
    ap.add_argument("--thema", help="nur bei wissen: bestimmtes Thema (id aus inhalte/wissen.yaml)")
    ap.add_argument("--eil", action="store_true", help="nur bei news: nur senden, wenn es eine Eilmeldung gibt")
    ap.add_argument("--daten", help="Datenordner (Standard: config.yaml daten.dir)")
    ap.add_argument("--out", default=os.environ.get("SOCIAL_AUSGABE", str(HIER / "ausgabe")))
    ap.add_argument("--senden", action="store_true", help="Video per Telegram an Tobias schicken")
    ap.add_argument("--art", choices=["video", "post", "beides"], default="beides",
                    help="post = Bild + Text fuer Telegram und X (Hauptformat dort)")
    args = ap.parse_args()

    cfg, geheim = lade_cfg()
    sperr = lade_sperrliste()
    if args.format == "wissen":
        return wissen_beitrag(args, cfg, geheim, sperr)
    if args.format == "news":
        return news_beitrag(args, cfg, geheim, sperr)
    probe = bool(args.daten)
    d = daten.laden(args.daten or cfg["daten"]["dir"],
                    None if probe else cfg["daten"]["max_alter_min"])

    beitrag = formate.FORMATE[args.format](d, sperr, cfg.get("sprache", "de"))
    zeilen, textquelle = texte.schreiben(beitrag, cfg, geheim.get("anthropic_api_key"))
    fehler = pruefung.pruefen(zeilen, beitrag, cfg, sperr)
    if fehler and textquelle == "claude":
        print("Claude-Text fiel durch die Pruefung, nehme Vorlage:", fehler)
        zeilen, textquelle = texte.vorlage(beitrag), "vorlage"
        fehler = pruefung.pruefen(zeilen, beitrag, cfg, sperr)

    stempel = time.strftime("%Y%m%d-%H%M")
    ordner = Path(args.out) / f"{stempel}_{beitrag['format']}"
    ordner.mkdir(parents=True, exist_ok=True)

    if args.art in ("post", "beides"):
        txt = post.markt_texte(beitrag, cfg)
        pfehler = pruefung.pruefen([txt["x"], txt["telegram"]], dict(beitrag, szenen=[0, 0]), cfg, sperr,
                                   erlaubt_fusszeile=True)
        holen = None if probe else (lambda coins: {c: kurse.verlauf(c) for c in coins})
        bild = post.markt_bild(beitrag, cfg, ordner / "post.png", verlauf_holen=holen)
        (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
        (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
        print(f"Post: X {len(txt['x'])} Zeichen, Pruefung:", pfehler or "bestanden")
        if args.senden:
            telegram.vorschlag_senden(geheim, ordner, "⚠️ " + "; ".join(pfehler) if pfehler else "")
        if args.art == "post":
            return 1 if pfehler else 0

    bild_dateien = bilder.zeichnen(beitrag, zeilen, ordner / "bilder", cfg)
    toene, dauern, tonquelle = stimme.sprechen(zeilen, ordner / "ton", cfg, geheim.get("elevenlabs_api_key"))
    ziel = video.bauen(bild_dateien, toene, dauern, ordner / f"{beitrag['format']}.mp4", cfg)

    meta = {
        "titel": beitrag["titel"],
        "beschreibung": " ".join(zeilen) + "\n\n" + cfg["hinweise"]["fusszeile"] + "\n"
                        + cfg["hinweise"]["konflikt"] + "\n" + " ".join(beitrag["hashtags"]),
        "zeilen": zeilen, "text": textquelle, "stimme": tonquelle,
        "dauer_s": round(sum(dauern), 1), "pruefung": fehler or "bestanden",
        "fakten": beitrag["fakten"], "video": str(ziel),
    }
    (ordner / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.senden:
        status = "✅ Prüfung bestanden" if not fehler else "⚠️ Prüfung: " + "; ".join(fehler)
        ok = telegram.video_senden(geheim, ziel, f"{beitrag['titel']}\n{status}\nText: {textquelle}, Stimme: {tonquelle}")
        print("Telegram:", "gesendet" if ok else "nicht gesendet (Token/Chat-ID fehlen?)")
    print(json.dumps({k: meta[k] for k in ("titel", "dauer_s", "text", "stimme", "pruefung", "video")},
                     ensure_ascii=False, indent=2))
    return 1 if fehler else 0


def wissen_beitrag(args, cfg, geheim, sperr) -> int:
    """Lern-Beitrag als Bild + Text (Telegram und X)."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stand = out / "wissen_stand.json"   # im Ausgabe-Ordner, dort darf der Benutzer "redaktion" schreiben
    t = wissen.naechstes(stand, args.thema)
    txt = wissen.texte(t, cfg)
    pseudo = {"fakten": t["fakten"], "szenen": [0, 0]}
    fehler = pruefung.pruefen([txt["x"], txt["telegram"]], pseudo, cfg, sperr, erlaubt_fusszeile=True)
    ordner = out / f"{time.strftime('%Y%m%d-%H%M')}_wissen_{t['id']}"
    b = wissen.bild(t, cfg, ordner / "post.png")
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    print(f"Wissen: {t['id']}, X {len(txt['x'])} Zeichen, Pruefung:", fehler or "bestanden")
    if args.senden and not fehler:
        telegram.vorschlag_senden(geheim, ordner)
    if not args.thema:
        wissen.merken(stand, t["id"], time.time())
    return 1 if fehler else 0


def news_beitrag(args, cfg, geheim, sperr, laden=None, schreiber=None) -> int:
    """Wichtigste noch nicht gezeigte Krypto-Nachricht als Bild + Text (Telegram und X)."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stand_p = out / "news_stand.json"
    stand = news.stand_laden(stand_p)
    meldungen, status = news.einsammeln(laden=laden)
    print("Quellen:", ", ".join(f"{k}: {v}" for k, v in status.items()))
    gruppen = [g for g in news.buendeln(meldungen) if not news.schon_gezeigt(g, stand)]
    if args.eil:
        heute = [t for t in stand.get("eil", []) if time.time() - t < 86400]
        gruppen = [g for g in gruppen if g["eil"]] if len(heute) < 2 else []
    if not gruppen:
        print("Keine neue Nachricht." if not args.eil else "Keine Eilmeldung.")
        return 0
    api = geheim.get("anthropic_api_key")
    if not api and not schreiber:
        print("Kein Claude-Schluessel – News brauchen eigene Texte, Abbruch.")
        return 1
    schreiber = schreiber or (lambda g: news_text.schreiben(g, cfg, api))
    for g in gruppen[:4]:   # ungeeignete Meldungen ueberspringen
        try:
            d = schreiber(g)
        except Exception as e:
            print("Claude-Fehler:", e)
            continue
        if not d:
            news.stand_merken(stand_p, g)
            continue
        txt = news_post.texte(d, g, cfg, eil=args.eil)
        quelltext = " ".join(m["titel"] + " " + m["kurz"] for m in g["meldungen"])
        fehler = pruefung.pruefen([txt["x"], d["kernsatz"], " ".join(d["punkte"]), d["schlagzeile"]],
                                  {"fakten": quelltext, "szenen": [0] * 4}, cfg, sperr, erlaubt_fusszeile=True)
        fehler += [f"Coin auf der Sperrliste: {c}" for c in d.get("coins", []) if str(c).upper() in sperr]
        fehler = list(dict.fromkeys(fehler))
        ordner = out / f"{time.strftime('%Y%m%d-%H%M')}_news"
        b = news_post.bild(d, g, cfg, ordner / "post.png", eil=args.eil)
        (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
        (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
        (ordner / "quellen.json").write_text(json.dumps(g["meldungen"], ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"News: {d['schlagzeile']} | Quellen {g['quellen']} | Punkte {g['punkte']} | Pruefung:",
              fehler or "bestanden")
        if args.senden:
            hinweis = "" if not fehler else "⚠️ Automatische Prüfung: " + "; ".join(fehler)
            telegram.vorschlag_senden(geheim, ordner, hinweis)
        news.stand_merken(stand_p, g, eil=args.eil)
        return 1 if fehler else 0
    print("Keine geeignete Nachricht gefunden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
