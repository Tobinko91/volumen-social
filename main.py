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

from social import (bilder, coincheck, daten, formate, kurse, news, news_post, news_text, post, pruefung, stimme, telegram,
                    texte, video, wissen)
from social import wal  # noqa: E402  (Wal des Tages)

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
    ap.add_argument("format", choices=sorted(formate.FORMATE) + ["wissen", "news", "coincheck", "wal"])
    ap.add_argument("--thema", help="nur bei wissen: bestimmtes Thema (id aus inhalte/wissen.yaml)")
    ap.add_argument("--eil", action="store_true", help="nur bei news: nur senden, wenn es eine Eilmeldung gibt")
    ap.add_argument("--coin", help="nur bei coincheck: bestimmter Coin, z. B. AKE")
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
    if args.format == "coincheck":
        return coincheck_beitrag(args, cfg, geheim, sperr)
    if args.format == "wal":
        return wal_beitrag(args, cfg, geheim, sperr)
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
        "beschreibung": " ".join(zeilen) + "\n\n" + cfg["hinweise"]["post_text"] + "\n"
                        + " ".join(beitrag["hashtags"]),
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


def news_beitrag(args, cfg, geheim, sperr, laden=None, schreiber=None, kurs_holen="auto") -> int:
    """Wichtigste noch nicht gezeigte Krypto-Nachricht als Bild + Text (Telegram und X)."""
    if kurs_holen == "auto":   # echte Laeufe holen den Kurs; Tests mit eigenem 'laden' nicht
        kurs_holen = kurse.verlauf if laden is None else None
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
        kurs = None
        coins = [str(c).upper() for c in d.get("coins", []) if str(c).upper() not in sperr]
        if coins and kurs_holen:
            try:
                kurs = kurs_holen(coins[0], "4h", 42)
            except Exception:
                kurs = None
        b = news_post.bild(d, g, cfg, ordner / "post.png", eil=args.eil, kurs=kurs)
        (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
        (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
        (ordner / "quellen.json").write_text(json.dumps(g["meldungen"], ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"News: {d['schlagzeile']} | Quellen {g['quellen']} | Punkte {g['punkte']} | Pruefung:",
              fehler or "bestanden")
        if args.senden:
            hinweis = news_post.quellen_hinweis(g)
            if fehler:
                hinweis = "⚠️ Automatische Prüfung: " + "; ".join(fehler) + "\n" + hinweis
            telegram.vorschlag_senden(geheim, ordner, hinweis)
        news.stand_merken(stand_p, g, eil=args.eil)
        return 1 if fehler else 0
    print("Keine geeignete Nachricht gefunden.")
    return 0


def wal_beitrag(args, cfg, geheim, sperr) -> int:
    """'Wal des Tages' als Bild + Text (Telegram und X) aus wale_7d / wale_verlauf des Bots."""
    probe = bool(args.daten)
    d = daten.laden(args.daten or cfg["daten"]["dir"], None if probe else cfg["daten"]["max_alter_min"])
    w = daten.wal_des_tages(d, sperr)
    if not w:
        print("Keine Wal-Daten.")
        return 0
    lang = cfg.get("sprache", "de")
    txt = wal.texte(w, cfg, lang)
    f = wal.fakten(w)
    fehler = pruefung.pruefen([txt["x"], txt["telegram"]], {"fakten": f, "szenen": [0, 0]}, cfg, sperr,
                              erlaubt_fusszeile=True)
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_wal_{w['base']}"
    wal.bild(w, cfg, ordner / "post.png", lang)
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    (ordner / "fakten.json").write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wal des Tages {w['base']} ({w['quelle']}): Pruefung", fehler or "bestanden")
    if args.senden:
        telegram.vorschlag_senden(geheim, ordner, "⚠️ " + "; ".join(fehler) if fehler else "")
    return 1 if fehler else 0


def _test_kerzen(n: int = 168) -> list[dict]:
    """Kuenstliche Kerzen nur fuer Proben ohne Netz (--daten)."""
    import math
    out, p = [], 1.0
    for i in range(n):
        q = 1 + 0.25 * math.sin(i / 20) + 0.08 * math.sin(i / 3) + (0.3 if i > 140 else 0)
        out.append({"t": i * 3600000, "o": p, "h": max(p, q) * 1.01, "l": min(p, q) * 0.99, "c": q,
                    "v": 1e5 * (1 + 2 * (abs(math.sin(i / 7)) > 0.9))})
        p = q
    return out


def coincheck_beitrag(args, cfg, geheim, sperr, kerzen_holen=None) -> int:
    """Coin-Check: ein Coin mit Kurs, Volumenprofil, Open Interest, Funding und Walen (Bild + Text)."""
    probe = bool(args.daten)
    d = daten.laden(args.daten or cfg["daten"]["dir"], None if probe else cfg["daten"]["max_alter_min"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stand_p = out / "coincheck_stand.json"
    stand = json.loads(stand_p.read_text()) if stand_p.exists() else {}
    base = (args.coin or "").upper().strip("$") or coincheck.auswahl(d.coins, sperr, stand)
    if not base:
        print("Kein passender Coin.")
        return 0
    if base in sperr:
        telegram.text_senden(geheim, f"{base} steht auf deiner Sperrliste – kein Coin-Check.") if args.senden else None
        print("Sperrliste:", base)
        return 1
    kerzen_holen = kerzen_holen or (_test_kerzen if probe else (lambda b: kurse.kerzen(b)))
    k = kerzen_holen(base) if not probe else _test_kerzen()
    c = dict(d.coins.get(base) or {"base": base})
    if k and c.get("price") is None:
        c["price"] = k[-1]["c"]
        c["chg24"] = round((k[-1]["c"] / k[-25]["c"] - 1) * 100, 1) if len(k) > 25 else None
    if not k and c.get("price") is None:
        if args.senden:
            telegram.text_senden(geheim, f"Für {base} habe ich weder Bot-Daten noch Kurse gefunden.")
        return 1
    z = kurse.zonen(k) if k else {"oben": [], "unten": [], "grenzen": [0, 1], "vol": [0]}
    f = coincheck.fakten(c, k, z)
    text = coincheck.schreiben(f, cfg, geheim.get("anthropic_api_key"))
    txt = coincheck.texte(text, cfg)
    fehler = pruefung.pruefen([txt["x"], " ".join(text["punkte"]), text["schlagzeile"]],
                              {"fakten": f, "szenen": [0] * 3}, cfg, sperr, erlaubt_fusszeile=True)
    if fehler and text is not None:   # Claude-Text faellt durch -> sichere Vorlage
        text = coincheck.vorlage(f)
        txt = coincheck.texte(text, cfg)
        fehler = pruefung.pruefen([txt["x"], " ".join(text["punkte"]), text["schlagzeile"]],
                                  {"fakten": f, "szenen": [0] * 3}, cfg, sperr, erlaubt_fusszeile=True)
    ordner = out / f"{time.strftime('%Y%m%d-%H%M')}_coincheck_{base}"
    coincheck.bild(c, k, z, text, cfg, ordner / "post.png")
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    (ordner / "fakten.json").write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Coin-Check {base}: Pruefung", fehler or "bestanden")
    if args.senden:
        telegram.vorschlag_senden(geheim, ordner, "⚠️ " + "; ".join(fehler) if fehler else "")
    stand[base] = time.time()
    stand_p.write_text(json.dumps(stand))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
