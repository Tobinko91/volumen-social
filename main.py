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

from social import links
from social import (bilder, coincheck, daten, formate, kurse, news, news_post, news_text, post, pruefung, stimme, telegram,
                    texte, video, wissen)
from social import wal  # noqa: E402  (Wal des Tages)
from social import sprache  # noqa: E402

HIER = Path(__file__).resolve().parent
# Auf dem Server liegen Schluessel und Sperrliste ausserhalb des Codes (/opt/volumen-social),
# damit ein Update sie nie ueberschreibt. Lokal: neben main.py.
GEHEIM_ORDNER = Path(os.environ.get("SOCIAL_GEHEIM", HIER))


def vorschlag(args, geheim: dict, cfg: dict, ordner: Path, hinweis: str = "", fehler: list | None = None) -> bool:
    """Routine-Formate: automatisch posten, wenn das Freigabe-Tor offen ist (social/autopost.py), sonst wie bisher
    als Vorschlag an Tobias. News/Eilmeldungen rufen das nie auf."""
    from social import autopost, bericht
    ausgabe = Path(args.out)
    fmt = bericht.format_aus_ordner(ordner.name)
    ok, grund = autopost.erlaubt(fmt, bericht.protokoll_laden(ausgabe / "protokoll.jsonl"), cfg,
                                 autopost.aus_datei(ausgabe).exists())
    if ok and not fehler and not getattr(args, "coin", None):   # /check COIN bleibt immer Vorschlag
        sys.path.insert(0, str(HIER / "tools"))
        import freigabe
        ergebnis = freigabe.posten(geheim, ordner.name, "alle")
        telegram.text_senden(geheim, f"🤖 Automatisch gepostet ({bericht.NAMEN.get(fmt, fmt)}, {grund}):\n{ergebnis}\n"
                                     "Stoppen: /auto aus")
        print("Automatisch gepostet:", ordner.name)
        return True
    return telegram.vorschlag_senden(geheim, ordner, hinweis)


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
    ap.add_argument("format", choices=sorted(formate.FORMATE) + ["wissen", "news", "coincheck", "wal", "karussell", "termine", "willkommen", "warum", "formation", "lehrbuch", "liquiditaet", "liqmap", "signallab"])
    ap.add_argument("--thema", help="nur bei wissen: bestimmtes Thema (id aus inhalte/wissen.yaml)")
    ap.add_argument("--eil", action="store_true", help="nur bei news: nur senden, wenn es eine Eilmeldung gibt")
    ap.add_argument("--nur-mit-stimme", action="store_true", help="nur bei willkommen: ohne Stimme nicht senden")
    ap.add_argument("--datum", help="nur bei termine: ab diesem Datum die kommende Woche (JJJJ-MM-TT), Standard heute")
    ap.add_argument("--coin", help="nur bei coincheck: bestimmter Coin, z. B. AKE")
    ap.add_argument("--richtung", choices=["hoch", "runter"], help="nur bei warum: Gewinner (Standard) oder Verlierer")
    ap.add_argument("--sprache", choices=["de", "en"], default=None,
                    help="Sprache (Standard: config.yaml). Englisch nur Probe/Schattenlauf: wird nie gesendet.")
    ap.add_argument("--skript", action="store_true", help="nur bei formation: Sprechtext an Tobias (eigene Stimme)")
    ap.add_argument("--daten", help="Datenordner (Standard: config.yaml daten.dir)")
    ap.add_argument("--out", default=os.environ.get("SOCIAL_AUSGABE", str(HIER / "ausgabe")))
    ap.add_argument("--senden", action="store_true", help="Video per Telegram an Tobias schicken")
    ap.add_argument("--art", choices=["video", "post", "beides"], default="beides",
                    help="post = Bild + Text fuer Telegram und X (Hauptformat dort)")
    args = ap.parse_args()

    cfg, geheim = lade_cfg()
    sperr = lade_sperrliste()
    lang = args.sprache or cfg.get("sprache", "de")
    if lang != cfg.get("sprache", "de") and args.senden:
        # S1: Englisch erst nach Freigabe durch Tobias. Bis dahin nie an den Freigabe-Bot (dessen Knoepfe
        # posten in die deutschen Kanaele).
        print("Diese Sprache ist nicht die Kanal-Sprache – nur Dateien erzeugt, nichts gesendet.")
        args.senden = False
    if args.format == "wissen":
        return wissen_beitrag(args, cfg, geheim, sperr)
    if args.format == "news":
        return news_beitrag(args, cfg, geheim, sperr)
    if args.format == "coincheck":
        return coincheck_beitrag(args, cfg, geheim, sperr)
    if args.format == "wal":
        return wal_beitrag(args, cfg, geheim, sperr)
    if args.format == "karussell":
        return karussell_beitrag(args, cfg, geheim, sperr)
    if args.format == "termine":
        return termine_beitrag(args, cfg, geheim, sperr)
    if args.format == "warum":
        return warum_beitrag(args, cfg, geheim, sperr)
    if args.format == "willkommen":
        return willkommen_video(args, cfg, geheim, sperr)
    if args.format == "formation":
        return formation_video(args, cfg, geheim, sperr)
    if args.format == "lehrbuch":
        return lehrbuch_video(args, cfg, geheim, sperr)
    if args.format == "liquiditaet":
        return liquiditaet_beitrag(args, cfg, geheim, sperr)
    if args.format == "liqmap":
        return liqmap_beitrag(args, cfg, geheim, sperr)
    if args.format == "signallab":
        return signallab_beitrag(args, cfg, geheim, sperr)
    probe = bool(args.daten)
    d = daten.laden(args.daten or cfg["daten"]["dir"],
                    None if probe else cfg["daten"]["max_alter_min"])

    beitrag = formate.FORMATE[args.format](d, sperr, lang)
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
        txt["telegram"] = links.mit_telegram_link(txt["telegram"], beitrag["format"], ordner.name,
                                                  lang=beitrag.get("sprache", "de"))
        pfehler = pruefung.pruefen([txt["x"], txt["telegram"]], dict(beitrag, szenen=[0, 0]), cfg, sperr,
                                   erlaubt_fusszeile=True)
        holen = None if probe else (lambda coins: {c: kurse.verlauf(c) for c in coins})
        bild = post.markt_bild(beitrag, cfg, ordner / "post.png", verlauf_holen=holen)
        (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
        (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
        print(f"Post: X {len(txt['x'])} Zeichen, Pruefung:", pfehler or "bestanden")
        if args.senden:
            vorschlag(args, geheim, cfg, ordner, "⚠️ " + "; ".join(pfehler) if pfehler else "", pfehler)
        if args.art == "post":
            return 1 if pfehler else 0

    if args.art == "beides":   # eigener Ordner: ein Vorschlag = ein Medium (Bild ODER Video)
        ordner = Path(args.out) / f"{stempel}_{beitrag['format']}_video"
        ordner.mkdir(parents=True, exist_ok=True)
    bild_dateien = bilder.zeichnen(beitrag, zeilen, ordner / "bilder", cfg)
    toene, dauern, tonquelle = stimme.sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    ziel = video.bauen(bild_dateien, toene, dauern, ordner / "video.mp4", cfg, **video.ut_formate(cfg, zeilen, beitrag))
    # Texte fuer die Kanaele wie beim Bild-Beitrag (Telegram-Text mit Link, X-Text)
    vtxt = post.markt_texte(beitrag, cfg)
    vtxt["telegram"] = links.mit_telegram_link(vtxt["telegram"], beitrag["format"], ordner.name,
                                               lang=beitrag.get("sprache", "de"))
    vtxt["x"] = post.frage_vorne(vtxt["x"], beitrag)   # gleiche Frage in Bild, Ton und X-Text
    (ordner / "post_x.txt").write_text(vtxt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(vtxt["telegram"], encoding="utf-8")
    fehler += [f for f in pruefung.pruefen([vtxt["x"], vtxt["telegram"]], dict(beitrag, szenen=[0, 0]), cfg, sperr,
                                           erlaubt_fusszeile=True) if f not in fehler]

    beschreibung = (" ".join(zeilen) + "\n\n" + sprache.hinweis(cfg, lang) + "\n"
                    + " ".join(beitrag["hashtags"]))
    meta = {
        "titel": beitrag["titel"],
        "beschreibung": beschreibung,
        # S7: je Kanal eigene Beschreibung mit Link-Kennung (utm_source = Kanal, utm_content = Beitrag)
        "beschreibungen": links.beschreibungen(beschreibung, beitrag["format"], ordner.name,
                                               lang=beitrag.get("sprache", "de")),
        "zeilen": zeilen, "text": textquelle, "stimme": tonquelle,
        "dauer_s": round(sum(dauern), 1), "pruefung": fehler or "bestanden",
        "fakten": beitrag["fakten"], "video": str(ziel),
    }
    (ordner / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.senden:
        status = "🎬 Video-Vorschlag (Reels, TikTok, X, Telegram)" + (
            "" if not fehler else "\n⚠️ Prüfung: " + "; ".join(fehler)) + f"\nStimme: {tonquelle}"
        ok = vorschlag(args, geheim, cfg, ordner, status, fehler)
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
    ordner = out / f"{time.strftime('%Y%m%d-%H%M')}_wissen_{t['id']}"
    txt = wissen.texte(t, cfg)
    txt["telegram"] = links.mit_telegram_link(txt["telegram"], "wissen", ordner.name)
    pseudo = {"fakten": t["fakten"], "szenen": [0, 0]}
    fehler = pruefung.pruefen([txt["x"], txt["telegram"]], pseudo, cfg, sperr, erlaubt_fusszeile=True)
    # Echter BTC-Chart einmal holen, fuer Bild UND Video (Wunsch Tobias 03.11.2026: überall)
    echt = wissen.echter_chart(t) if (cfg.get("video") or {}).get("echter_chart", True) else None
    b = wissen.bild(t, cfg, ordner / "post.png", echt=echt)
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    print(f"Wissen: {t['id']}, X {len(txt['x'])} Zeichen, Pruefung:", fehler or "bestanden")
    if args.senden and not fehler:
        vorschlag(args, geheim, cfg, ordner, f"Chart: echter {echt['titel']}-Chart" if echt else "")
    if getattr(args, "art", "beides") in ("video", "beides"):   # S28: Lernen auch als Reel/TikTok/Short
        fehler += wissen_video(t, txt, cfg, geheim, sperr, Path(f"{ordner}_video"), args, echt)
    if not args.thema:
        wissen.merken(stand, t["id"], time.time())
    return 1 if fehler else 0


def formation_video(args, cfg, geheim, sperr) -> int:
    """S27 „Formation des Tages: BUY or SELL?“ (Wunsch Tobias 09.11.2026), Daten muster_des_tages.json vom Bot."""
    import html as _h
    from social import formation
    d = formation.laden(args.daten or cfg["daten"]["dir"])
    if not d:
        print("Formation: keine (vollstaendigen) Daten in muster_des_tages.json")
        return 0
    if d["coin"].upper() in {c.upper() for c in sperr}:
        print("Formation: Coin auf der Sperrliste, kein Video")
        return 0
    stand = Path(args.out) / "formation_stand.json"
    try:
        schon = json.loads(stand.read_text())
    except Exception:
        schon = {}
    tag = d.get("datum") or time.strftime("%Y-%m-%d")
    if not args.daten and schon.get("tag") == tag:
        print("Formation: heute schon gebaut")
        return 0
    modus = (cfg.get("formation") or {}).get("aufloesung", "morgen")
    from social import eigenstimme
    es = cfg.get("eigene_stimme") or {}
    es_aktiv = bool(es.get("aktiv")) and time.strftime("%Y-%m-%d") <= str(es.get("bis", "2000-01-01"))
    if getattr(args, "skript", False):   # 18:00: Sprechtext an Tobias, Community-Zahl wird dabei festgelegt
        if not es_aktiv:
            return 0
        g, erg, _ = (_formation_gestern(args, cfg, geheim, schon, markieren=False) if modus == "morgen"
                     else (None, None, ""))
        zeilen = formation.zeilen_gesamt(d, modus, g, erg)
        eigenstimme.skript_speichern(Path(args.out), zeilen, erg, schon.get("ordner") if g else None)
        if args.senden:
            from social import telegram
            telegram.an_tobias(geheim, eigenstimme.skript_text(zeilen, es.get("bis_uhr", "21:15")))
        print("Skript fuer die eigene Stimme:", len(zeilen), "Saetze")
        return 0
    skript = eigenstimme.skript_laden(Path(args.out)) if es_aktiv else None
    rec = eigenstimme.aufnahme(Path(args.out)) if skript else None
    gestern, community, c_hinweis = _formation_gestern(args, cfg, geheim, schon) if modus == "morgen" else (None, None, "")
    if rec and gestern is not None and skript.get("gestern_ordner"):
        community = skript.get("community")   # dieselbe Zahl wie im Skript, das Tobias gesprochen hat
    name = "formationich" if rec else "formation"   # eigenes Format im Wochenbericht (Haltequote gegen Brian)
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_{name}_{d['coin']}_video"
    pfad = None
    if rec:
        try:
            key = geheim.get("elevenlabs_api_key") or ""
            pfad, quelle, tx = formation.video(d, ordner, cfg, geheim, modus=modus, gestern=gestern,
                                               community=community,
                                               sprechen=eigenstimme.sprecher(rec, key, skript.get("zeilen")))
        except Exception as e:
            print("Eigene Stimme nicht genutzt:", e)
            c_hinweis = (c_hinweis + f"\n⚠️ Deine Aufnahme ging nicht ({str(e)[:80]}), Brian spricht.").strip()
            import shutil as _sh
            _sh.rmtree(ordner, ignore_errors=True)
            ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_formation_{d['coin']}_video"
    if pfad is None:
        pfad, quelle, tx = formation.video(d, ordner, cfg, geheim, modus=modus, gestern=gestern, community=community)
    (ordner / "daten.json").write_text(json.dumps(d), encoding="utf-8")   # fuer die Aufloesung morgen
    (ordner / "post_x.txt").write_text(tx["x"], encoding="utf-8")
    e = lambda x: _h.escape(x, quote=False)
    (ordner / "post_telegram.txt").write_text(
        "📊 <b>BUY or SELL?</b>\n\n" + "\n".join(e(z) for z in tx["zeilen"]) + "\n\n<i>Not financial advice.</i>",
        encoding="utf-8")
    if not args.daten:
        stand.write_text(json.dumps({"tag": tag, "ordner": str(ordner), "aufgeloest": modus != "morgen"}))
    print(f"Formation {d['muster']} auf {d['coin']}: Stimme {quelle}", c_hinweis)
    if args.senden:
        vorschlag(args, geheim, cfg, ordner, f"📊 Formation des Tages: {d['name_en']} auf {d['coin']}\nStimme: {quelle}"
                  + (f"\nAuflösung von gestern ({gestern['coin']}) vorne dran. {c_hinweis}" if gestern else "")
                  + ("" if d.get("statistik") else "\n⚠️ Ohne Trefferquote: einmal tools/muster_statistik.py im "
                     "Bot ausfuehren (Szene „But here's the catch“ fehlt sonst)."))
    return 0


def _formation_gestern(args, cfg, geheim, schon: dict, markieren: bool = True) -> tuple[dict | None, dict | None, str]:
    """Offene Aufloesung der letzten Formation (hoechstens 3 Tage alt) + Community-Ergebnis. Markiert sie als
    aufgeloest (ausser bei Probelaeufen mit --daten)."""
    from social import community
    if schon.get("aufgeloest", True) or not schon.get("ordner"):
        return None, None, ""
    alt = Path(schon["ordner"])
    try:
        g = json.loads((alt / "daten.json").read_text())
    except Exception:
        return None, None, ""
    if time.time() - alt.stat().st_mtime > 3 * 86400 or len(g.get("kerzen_nachher") or []) < 6:
        return None, None, ""
    try:
        erg, hinweis = community.holen(alt, geheim, cfg)
    except Exception as e:
        erg, hinweis = None, f"Community nicht gezählt: {str(e)[:60]}"
    if markieren and not args.daten:
        p = Path(args.out) / "formation_stand.json"
        p.write_text(json.dumps(dict(schon, aufgeloest=True)))
    return g, erg, hinweis


def lehrbuch_video(args, cfg, geheim, sperr) -> int:
    """S29 „The textbook is WRONG“ (Wunsch Tobias 10.11.2026): 1 Folge pro Woche statt S27 an diesem Tag.
    Rueckgabe 3 = keine Folge gebaut (plan.sh baut dann die Formation des Tages)."""
    import html as _h
    from social import lehrbuch
    lc = cfg.get("lehrbuch") or {}
    if not lc.get("aktiv", True):
        return 3
    daten = lehrbuch.laden(args.daten or cfg["daten"]["dir"])
    stand_p = Path(args.out) / "lehrbuch_stand.json"
    try:
        stand = json.loads(stand_p.read_text())
    except Exception:
        stand = {}
    woche = time.strftime("%G-W%V")
    if not args.daten and stand.get("woche") == woche:
        print("Lehrbuch: diese Woche schon gebaut")
        return 3
    m = lehrbuch.naechste(daten, stand.get("erledigt", []), lc.get("reihe"))
    if not m:
        print("Lehrbuch: keine Folge (Reihe fertig oder Beispiel fehlt noch, lehrbuch_falsch vom Bot 9.38)")
        return 3
    if m == lehrbuch.ABSCHLUSS:
        coin, titel = "", "Abschluss: der Hammer"
    else:
        e = daten[m]
        if e["coin"].upper() in {c.upper() for c in sperr}:
            print("Lehrbuch: Coin auf der Sperrliste")
            return 3
        coin, titel = e["coin"], f"{e['name_en']} auf {e['coin']}"
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_lehrbuch_{m}_video"
    if m == lehrbuch.ABSCHLUSS:
        folgen, tx = lehrbuch.abschluss_szenen(daten["_statistik"][m], ordner / "bilder")
    else:
        folgen, tx = lehrbuch.szenen(daten[m], ordner / "bilder")
    v_hinweis = ""
    if (cfg.get("formation") or {}).get("aufloesung", "morgen") == "morgen":   # Aufloesung von gestern nicht verlieren
        from social import formation
        try:
            f_stand = json.loads((Path(args.out) / "formation_stand.json").read_text())
        except Exception:
            f_stand = {}
        g, erg, v_hinweis = _formation_gestern(args, cfg, geheim, f_stand)
        if g:
            vf, vz = formation.vorspann(g, ordner / "bilder", erg)
            folgen, tx = vf + folgen, dict(tx, zeilen=vz + ["Now, this week's myth. " + tx["zeilen"][0]]
                                           + tx["zeilen"][1:])
    pfad, quelle = lehrbuch.video(folgen, tx, ordner, cfg, geheim)
    (ordner / "post_x.txt").write_text(tx["x"], encoding="utf-8")
    e_ = lambda x: _h.escape(x, quote=False)
    (ordner / "post_telegram.txt").write_text(
        "📚 <b>The textbook is WRONG</b>\n\n" + "\n".join(e_(z) for z in tx["zeilen"])
        + "\n\n<i>Not financial advice.</i>", encoding="utf-8")
    if not args.daten:
        stand_p.write_text(json.dumps({"woche": woche, "erledigt": stand.get("erledigt", []) + [m]}))
    print(f"Lehrbuch {m} {coin}: Stimme {quelle}")
    if args.senden:
        vorschlag(args, geheim, cfg, ordner, f"📚 The textbook is WRONG: {titel}\nStimme: {quelle}"
                  + (f"\nAuflösung der Formation von gestern vorne dran. {v_hinweis}" if v_hinweis else ""))
    return 0


def liquiditaet_beitrag(args, cfg, geheim, sperr) -> int:
    """S24 (Wunsch Tobias 06.11.2026): Top- und Flop-Coin des Tages mit geschaetzten Liquiditaetszonen + Heatmap,
    je Bild (4:5) und Reel (9:16). Daten: liquiditaet.json vom Bot."""
    from social import liquiditaet
    if not (cfg.get("liquiditaet") or {}).get("aktiv", True):
        return 0
    d = liquiditaet.laden(Path(args.daten or cfg["daten"]["dir"]))
    gesperrt = {c.upper() for c in sperr}
    for rolle in ("top", "flop"):
        e = next((c for c in d.get("coins") or [] if c.get("rolle") == rolle and c["base"].upper() not in gesperrt
                  and c.get("kerzen")), None)
        if not e:
            continue
        ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_liquiditaet_{e['base']}"
        b = liquiditaet.beitrag(e, ordner, cfg, d.get("pruefung"))
        print(f"Liquiditaet {rolle} {e['base']}: X {len(b['x'])} Zeichen, Heatmap {'ja' if e.get('heatmap') else 'nein'}")
        if args.senden:
            vorschlag(args, geheim, cfg, ordner, f"💧 {'Top' if rolle == 'top' else 'Flop'}-Coin mit geschaetzten Zonen")
        if getattr(args, "art", "beides") in ("video", "beides") and not args.daten:
            vo = Path(f"{ordner}_video")
            vo.mkdir(parents=True, exist_ok=True)
            for f in ("post_x.txt", "post_telegram.txt"):
                (vo / f).write_text((ordner / f).read_text(encoding="utf-8"), encoding="utf-8")
            _, quelle = liquiditaet.reel(b, vo, cfg, geheim)
            if args.senden:
                vorschlag(args, geheim, cfg, vo, f"💧 {e['base']} Liquiditaet als Reel · Stimme: {quelle}")
    return 0


def liqmap_beitrag(args, cfg, geheim, sperr) -> int:
    """S28 Liquidity Map of the Day (Wunsch Tobias 09.11.2026): Heatmap-Karussell BTC + Coin des Tages (+ Flop)
    und Reel. Daten: liquidity_map_des_tages.json vom Bot (ab 06:30)."""
    from social import liqmap, stimme
    web = Path(args.daten or cfg["daten"]["dir"])
    d = liqmap.laden(web)
    if not d:
        print("Liquidity Map: keine Daten")
        return 0
    for feld in ("top", "flop"):   # Sperrliste: Coin weglassen (fehlt top, nur BTC)
        if d.get(feld) and d[feld].get("base", "").upper() in {c.upper() for c in sperr}:
            d[feld] = None
    if not d.get("top"):
        d["flop"] = None
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_liqmap"
    folien, szenen = liqmap.bauen(d, ordner, cfg, web)
    if not folien:
        print("Liquidity Map: keine Heatmap zeichenbar")
        return 0
    tx = liqmap.texte(d, cfg)
    (ordner / "post_x.txt").write_text(tx["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(tx["telegram"], encoding="utf-8")
    print(f"Liquidity Map: {len(folien)} Folien, X {len(tx['x'])} Zeichen")
    if args.senden:
        vorschlag(args, geheim, cfg, ordner, "🗺 Liquidity Map of the Day (Karussell, Zonen geschaetzt)")
    if getattr(args, "art", "beides") in ("video", "beides") and szenen and not args.daten:
        vo = Path(f"{ordner}_video")
        vo.mkdir(parents=True, exist_ok=True)
        for f in ("post_x.txt", "post_telegram.txt"):
            (vo / f).write_text((ordner / f).read_text(encoding="utf-8"), encoding="utf-8")
        z = tx["sprech"]   # Szenen: BTC (Einstieg + Kurs + Cluster), Coin des Tages, Schluss auf dem letzten Bild
        zeilen = [" ".join(z[:3]), *(z[3:-1] if len(szenen) > 1 else []), z[-1]]
        bilder_ = [szenen[0], *(szenen[1:len(zeilen) - 1]), szenen[-1]][:len(zeilen)]
        toene, dauern, quelle = stimme.sprechen(zeilen, vo / "ton", cfg, stimme.schluessel(cfg, geheim))
        video.bauen(bilder_, toene, dauern, vo / "video.mp4", cfg, **video.ut_formate(cfg, zeilen))
        if args.senden:
            vorschlag(args, geheim, cfg, vo, f"🗺 Liquidity Map als Reel · Stimme: {quelle}")
    return 0


def signallab_beitrag(args, cfg, geheim, sperr) -> int:
    """S23 Signal Lab · Week N (Wunsch Tobias 04.11.2026), montags. Verlierer werden genauso gezeigt."""
    from social import signallab
    d = signallab.laden(Path(args.daten or cfg["daten"]["dir"]))
    if not d:
        print("Signal Lab: keine strategien.json")
        return 0
    jetzt = time.time()
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_signallab"
    signallab.bild(d, cfg, ordner / "post.png", jetzt)
    tx = signallab.texte(d, cfg, jetzt)
    (ordner / "post_x.txt").write_text(tx["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(tx["telegram"], encoding="utf-8")
    print(f"Signal Lab Woche {signallab.woche_nr(d, jetzt)}: X {len(tx['x'])} Zeichen")
    if args.senden:
        vorschlag(args, geheim, cfg, ordner, "🧪 Signal Lab · Wochen-Post (auch Verlierer, wie gewünscht 04.11.)")
    return 0


def wissen_video(t, txt, cfg, geheim, sperr, ordner: Path, args, echt=None) -> list[str]:
    """S28 Lern-Video (9:16): grosse Zahl als Haken, je Punkt eine Szene, Folgen. Mit Stimme, wenn eingerichtet."""
    lang = cfg.get("sprache", "en")
    b = wissen.video_szenen(t, lang, echt)
    zeilen = [sz["vorlage"] for sz in b["szenen"]]
    fehler = pruefung.pruefen(zeilen, {"fakten": b["fakten"], "szenen": b["szenen"]}, cfg, sperr)
    ordner.mkdir(parents=True, exist_ok=True)
    bild_dateien = bilder.zeichnen(dict(b, ts=time.time()), zeilen, ordner / "bilder", cfg)
    toene, dauern, tonquelle = stimme.sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    video.bauen(bild_dateien, toene, dauern, ordner / "video.mp4", cfg, **video.ut_formate(cfg, zeilen, b))
    (ordner / "post_x.txt").write_text(post.frage_vorne(txt["x"], b), encoding="utf-8")   # gleiche Frage wie im Video
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    print(f"Lern-Video {t['id']}: {round(sum(dauern), 1)} s, Stimme {tonquelle}, Chart "
          f"{'echt ' + echt['titel'] if echt else 'Illustration'}, Pruefung", fehler or "bestanden")
    if args.senden and not fehler:
        vorschlag(args, geheim, cfg, ordner, f"🎬 Video-Vorschlag Lernen ({t['titel']})\nStimme: {tonquelle}"
                  + (f"\nChart: echter {echt['titel']}-Chart" if echt else ""))
    return fehler


def _markt_fuer_news(args, cfg) -> dict | None:
    """S19: aktuelle Marktbreite vom Bot fuer die Krypto-Zeile unter Makro-News (fehlt sie, ohne Zeile)."""
    try:
        return daten.marktlage(daten.laden(args.daten or cfg["daten"]["dir"], cfg["daten"]["max_alter_min"]))
    except Exception:
        return None


def news_beitrag(args, cfg, geheim, sperr, laden=None, schreiber=None, kurs_holen="auto", markt="auto",
                 x_leser="auto") -> int:
    """Wichtigste noch nicht gezeigte Krypto-Nachricht als Bild + Text (Telegram und X).
    S18: Radar-Konten (inhalte/quellen.yaml) zaehlen nur mit zweiter Quelle. S19: Makro-News bekommen eine
    Zeile mit eigenen Bot-Daten."""
    if kurs_holen == "auto":   # echte Laeufe holen den Kurs; Tests mit eigenem 'laden' nicht
        kurs_holen = kurse.verlauf if laden is None else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stand_p = out / "news_stand.json"
    stand = news.stand_laden(stand_p)
    if x_leser == "auto":   # X kostet je Abruf: nur wenn eingeschaltet, Schluessel da und nicht im Stunden-Eil-Lauf
        r = cfg.get("radar") or {}
        x_an = r.get("x_lesen") and not args.eil and laden is None and all(
            geheim.get(k) for k in ("x_api_key", "x_api_secret", "x_access_token", "x_access_secret"))
        x_leser = (lambda konten: news.x_radar(konten, geheim, max_posts=int(r.get("x_max_posts", 30)))) if x_an \
            else None
    meldungen, status = news.einsammeln(laden=laden, x_leser=x_leser)
    print("Quellen:", ", ".join(f"{k}: {v}" for k, v in status.items()))
    gruppen = [g for g in news.buendeln(meldungen) if not news.schon_gezeigt(g, stand)]
    ohne = [g for g in gruppen if not g.get("bestaetigt", True)]
    if ohne:
        print("Radar ohne zweite Quelle (nicht gepostet):", "; ".join(g["meldungen"][0]["titel"][:60] for g in ohne[:5]))
    gruppen = [g for g in gruppen if g.get("bestaetigt", True)]
    if args.eil:
        heute = [t for t in stand.get("eil", []) if time.time() - t < 86400]
        gruppen = [g for g in gruppen if g["eil"]] if len(heute) < int((cfg.get("eil") or {}).get("max_pro_tag", 5)) else []
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
        sp = cfg.get("sprache", "de")
        if news_post.ist_makro(d, g):
            if markt == "auto":
                markt = _markt_fuer_news(args, cfg)
            d["krypto"] = news_post.krypto_zeile(markt, sp)
        txt = news_post.texte(d, g, cfg, eil=args.eil)
        quelltext = " ".join(m["titel"] + " " + m["kurz"] for m in g["meldungen"])
        quelltext += " " + " ".join(news_text.zeiten(quelltext, sp)) + " " + news_text.heute_text(lang=sp)
        if d.get("krypto"):   # Zahlen der Krypto-Zeile stammen aus den Bot-Daten
            quelltext += " " + " ".join(str(z) for z in d["krypto"]["fakten"] if z is not None)
        fehler = pruefung.pruefen([txt["x"], d["kernsatz"], " ".join(d["punkte"]), d["schlagzeile"],
                                   (d.get("krypto") or {}).get("lang", "")],
                                  {"fakten": quelltext, "szenen": [0] * 5}, cfg, sperr, erlaubt_fusszeile=True)
        fehler += [f"Coin auf der Sperrliste: {c}" for c in d.get("coins", []) if str(c).upper() in sperr]
        fehler = list(dict.fromkeys(fehler))
        if any(f.startswith(pruefung.SPRACHFEHLER) for f in fehler):   # nie einen deutschen Text vorschlagen
            print("Uebersprungen, nicht Englisch:", d.get("schlagzeile"), fehler)
            news.stand_merken(stand_p, g)
            continue
        ordner = out / f"{time.strftime('%Y%m%d-%H%M')}_news"
        kurs = None
        coins = [str(c).upper() for c in d.get("coins", []) if str(c).upper() not in sperr]
        if coins and kurs_holen:
            try:
                kurs = kurs_holen(coins[0], "4h", 42)
            except Exception:
                kurs = None
        b = news_post.bild(d, g, cfg, ordner / "post.png", eil=args.eil, kurs=kurs)
        txt["telegram"] = links.mit_telegram_link(txt["telegram"], "news", ordner.name)
        (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
        (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
        (ordner / "quellen.json").write_text(json.dumps(g["meldungen"], ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"News: {d['schlagzeile']} | Quellen {g['quellen']} | Punkte {g['punkte']} | Pruefung:",
              fehler or "bestanden")
        if args.senden:
            hinweis = news_post.quellen_hinweis(g)
            if args.eil:   # Live-Modus: Tobias soll sofort sehen, dass es eilt
                hinweis = "🚨 EILMELDUNG – bitte schnell freigeben, News veralten in Minuten.\n" + hinweis
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
    lang = getattr(args, "sprache", None) or cfg.get("sprache", "de")
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_wal_{w['base']}"
    txt = wal.texte(w, cfg, lang)
    txt["telegram"] = links.mit_telegram_link(txt["telegram"], "wal", ordner.name, pfad=f"/coin/{w['base'].lower()}/",
                                              lang=lang)
    f = wal.fakten(w)
    w.setdefault("mcap", (d.coins.get(w["base"]) or {}).get("mcap"))   # fuer das passende Logo (06.11.2026)
    fehler = pruefung.pruefen([txt["x"], txt["telegram"]], {"fakten": f, "szenen": [0, 0]}, cfg, sperr,
                              erlaubt_fusszeile=True)
    wal.bild(w, cfg, ordner / "post.png", lang)
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    (ordner / "fakten.json").write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wal des Tages {w['base']} ({w['quelle']}): Pruefung", fehler or "bestanden")
    # Seit 05.11.2026 (Tobias: weniger Vorschlaege) geht bei „beides“ nur das Video an Tobias; Bild nur mit --art post
    if args.senden and getattr(args, "art", "beides") == "post":
        vorschlag(args, geheim, cfg, ordner, "⚠️ " + "; ".join(fehler) if fehler else "", fehler)
    if getattr(args, "art", "beides") in ("video", "beides"):   # Wunsch Tobias 01.11.2026: auch als Video
        fehler += wal_video(w, txt, f, cfg, geheim, sperr, Path(f"{ordner}_video"), lang, args.senden, args)
    return 1 if fehler else 0


def karussell_beitrag(args, cfg, geheim, sperr) -> int:
    """S11 Wal-Karussell (sonntags): die Wale der Woche als Bilderserie (Instagram, TikTok, X, Telegram)."""
    from social import karussell
    probe = bool(args.daten)
    d = daten.laden(args.daten or cfg["daten"]["dir"], None if probe else cfg["daten"]["max_alter_min"])
    wale = daten.wale_der_woche(d, sperr)
    if len(wale) < 3:   # weniger als 3 Folien lohnt kein Karussell
        print("Zu wenige Wal-Daten fuer das Karussell:", len(wale))
        return 0
    lang = getattr(args, "sprache", None) or cfg.get("sprache", "de")
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_karussell"
    txt = karussell.texte(wale, cfg, lang)
    f = karussell.fakten(wale)
    fehler = pruefung.pruefen([txt["x"], txt["telegram"]], {"fakten": f, "szenen": [0, 0]}, cfg, sperr,
                              erlaubt_fusszeile=True)
    karussell.bauen(wale, cfg, ordner, lang)
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    (ordner / "fakten.json").write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wal-Karussell ({', '.join(w['base'] for w in wale)}): Pruefung", fehler or "bestanden")
    if args.senden:
        vorschlag(args, geheim, cfg, ordner, "🎠 Karussell-Vorschlag Whales of the week (YouTube: nicht möglich)"
                  + ("\n⚠️ " + "; ".join(fehler) if fehler else ""), fehler)
    return 1 if fehler else 0


def willkommen_video(args, cfg, geheim, sperr) -> int:
    """S30 Willkommensvideo mit Stimme zum Anpinnen (Wunsch Tobias 03.11.2026)."""
    from social import willkommen
    b = willkommen.szenen()
    zeilen = [sz["vorlage"] for sz in b["szenen"]]
    fehler = pruefung.pruefen(zeilen, {"fakten": b["fakten"], "szenen": b["szenen"]}, cfg, sperr)
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_willkommen_video"
    ordner.mkdir(parents=True, exist_ok=True)
    bild_dateien = bilder.zeichnen(dict(b, ts=time.time()), zeilen, ordner / "bilder", cfg)
    toene, dauern, tonquelle = stimme.sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    video.bauen(bild_dateien, toene, dauern, ordner / "video.mp4", cfg, **video.ut_formate(cfg, zeilen, b))
    (ordner / "post_x.txt").write_text(willkommen.X, encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(willkommen.TELEGRAM, encoding="utf-8")
    print(f"Willkommensvideo: {round(sum(dauern), 1)} s, Stimme {tonquelle}, Pruefung", fehler or "bestanden")
    if getattr(args, "nur_mit_stimme", False) and tonquelle.startswith("stille"):
        print("Ohne Stimme nicht gesendet, naechster Versuch spaeter.")
        return 2
    if args.senden and not fehler:
        telegram.vorschlag_senden(geheim, ordner, "🎬 Willkommensvideo zum Anpinnen (S30). Nach dem Posten auf TikTok, "
                                  f"Instagram und X oben anpinnen.\nStimme: {tonquelle}")
    return 1 if fehler else 0


def termine_beitrag(args, cfg, geheim, sperr) -> int:
    """S13 Termine der Woche (montags): CPI, Arbeitsmarkt, PCE, Fed, Optionsverfall – Bild + Text."""
    import datetime as _dt
    from social import termine
    lang = getattr(args, "sprache", None) or cfg.get("sprache", "de")
    heute = _dt.date.fromisoformat(args.datum) if getattr(args, "datum", None) else _dt.date.today()
    montag = termine.kommende_woche(heute)   # immer die kommende Woche, nie die vergangene
    t = termine.laden(HIER / "inhalte" / "termine.yaml")
    luecken = termine.pflege_luecken(t, montag)
    if luecken and args.senden:   # Redaktion muss die Liste nachpflegen (Hinweis nur an Tobias)
        telegram.text_senden(geheim, "📅 Termine-Liste bald leer: " + ", ".join(luecken)
                             + ". Bitte im Redaktions-Chat sagen: „Termine nachpflegen“.")
    ereignisse = termine.woche(t, montag, lang)
    if not ereignisse:
        print("Keine Termine diese Woche – kein Beitrag.")
        return 0
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_termine"
    txt = termine.texte(ereignisse, cfg, lang)
    f = termine.fakten(ereignisse)
    fehler = pruefung.pruefen([txt["x"], txt["telegram"]], {"fakten": f, "szenen": [0, 0]}, cfg, sperr,
                              erlaubt_fusszeile=True)
    termine.bild(ereignisse, cfg, ordner / "post.png", montag, lang)
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    (ordner / "fakten.json").write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Termine der Woche ab {montag}: {len(ereignisse)} Termine, Pruefung", fehler or "bestanden")
    if args.senden:
        vorschlag(args, geheim, cfg, ordner, "⚠️ " + "; ".join(fehler) if fehler else "", fehler)
    return 1 if fehler else 0


def titelbild(b: dict, base: str, mcap, ordner: Path, ausgabe: Path) -> str:
    """Hingucker im Titelbild (Wunsch Tobias 06.11.2026): Coin-Logo in der ersten Szene, A/B-Test „titelbild“
    (abwechselnd mit/ohne). Rueckgabe: Zeile fuer den Hinweis an Tobias."""
    from social import bildpaket, logos
    ordner.mkdir(parents=True, exist_ok=True)
    art = bildpaket.test_zuteilen(ordner, ausgabe / "bildtest_titelbild_stand.json", "titelbild")
    if art != "mit":
        return "\n🖼 Bild-Test: Titelbild OHNE Logo (Vergleichsgruppe)"
    pfad = logos.logo(base, mcap, Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social")) / "logos")
    if not pfad:
        (ordner / "bildtest.json").unlink(missing_ok=True)   # ohne Logo zaehlt der Beitrag nicht im Test
        return "\n🖼 Kein eindeutiges Logo gefunden, Titelbild ohne Logo (nicht im Test)"
    b["szenen"][0]["daten"]["_logo"] = str(pfad)
    return "\n🖼 Bild-Test: Titelbild MIT Coin-Logo"


def wal_video(w, txt, f, cfg, geheim, sperr, ordner: Path, lang: str, senden: bool, args=None) -> list[str]:
    """'Whale of the day' als 9:16-Video (Haken mit der Wal-Zahl, Verlauf, Boersen/Holder, Folgen)."""
    b = wal.video_szenen(w, lang)
    zeilen = [sz["vorlage"] for sz in b["szenen"]]
    fehler = pruefung.pruefen(zeilen, {"fakten": f, "szenen": b["szenen"]}, cfg, sperr)
    ordner.mkdir(parents=True, exist_ok=True)
    bild_hw = "" if getattr(args, "daten", None) else titelbild(b, w["base"], w.get("mcap"), ordner, ordner.parent)
    bild_dateien = bilder.zeichnen(dict(b, ts=time.time()), zeilen, ordner / "bilder", cfg)
    toene, dauern, tonquelle = stimme.sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    video.bauen(bild_dateien, toene, dauern, ordner / "video.mp4", cfg, **video.ut_formate(cfg, zeilen, b))
    (ordner / "post_x.txt").write_text(post.frage_vorne(txt["x"], b), encoding="utf-8")   # gleiche Frage wie im Video
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    print(f"Wal-Video {w['base']}: {round(sum(dauern), 1)} s, Pruefung", fehler or "bestanden")
    if senden:
        vorschlag(args, geheim, cfg, ordner, "🎬 Video-Vorschlag Whale of the day" + bild_hw + (
            "\n⚠️ " + "; ".join(fehler) if fehler else ""))
    return fehler


def warum_beitrag(args, cfg, geheim, sperr, kerzen_holen=None) -> int:
    """„Why did it move?“ (Wunsch Tobias 04.11.2026, ersetzt das Markt-Video): ein Coin, Erklaerung aus Daten."""
    from social import warum
    if not (cfg.get("warum") or {}).get("aktiv", True) and not args.daten and not args.coin:   # Pause (CARV 04.11.)
        print("Warum-Video pausiert (config warum.aktiv: false).")
        return 0
    probe = bool(args.daten)
    d = daten.laden(args.daten or cfg["daten"]["dir"], None if probe else cfg["daten"]["max_alter_min"])
    from social import verlauf as _verlauf
    richtung = getattr(args, "richtung", None) or "hoch"
    if args.coin:   # /warum COIN im Redaktions-Bot
        base = args.coin.upper().strip("$")
        if base in sperr:
            telegram.text_senden(geheim, f"{base} steht auf deiner Sperrliste – kein Warum-Video.") if args.senden else None
            return 0
        w = warum.coin_wahl(d, base)
        if not w:
            msg = f"{base} ist nicht in den Bot-Daten (Bitunix-Scan) – kein Warum-Video."
            telegram.text_senden(geheim, msg) if args.senden else print(msg)
            return 0
    else:
        w = warum.auswahl(d, sperr, richtung)
    if not w:
        print("Keine passende Bewegung – kein Warum-Video.")
        return 0
    holen = kerzen_holen or ((lambda b: _test_kerzen(168)) if probe else (lambda b: kurse.kerzen(b, "1h", 168)))
    try:
        kerzen = holen(w["base"])
    except Exception as e:
        print("Kerzen nicht geholt:", e)
        kerzen = []
    lsr = None if probe else kurse.long_short(w["base"])
    b = warum.beitrag(d, sperr, kerzen, "en", richtung=richtung, wahl=w, lsr=lsr,
                      verlauf=_verlauf.laden(Path(args.out) / "verlauf", w["base"]))
    zeilen = [s["vorlage"] for s in b["szenen"]]   # feste Regel-Saetze, kein Claude (nichts erfinden)
    fehler = pruefung.pruefen(zeilen, b, warum.pruef_cfg(cfg), sperr)
    txt = warum.texte(b, cfg)
    fehler += [f for f in pruefung.pruefen([txt["x"], txt["telegram"]], dict(b, szenen=[0, 0]), cfg, sperr,
                                           erlaubt_fusszeile=True) if f not in fehler]
    ordner = Path(args.out) / f"{time.strftime('%Y%m%d-%H%M')}_warum_{b['base']}_video"
    ordner.mkdir(parents=True, exist_ok=True)
    bild_hw = "" if probe else titelbild(b, b["base"], (w.get("coin") or {}).get("mcap"), ordner, Path(args.out))
    bild_dateien = bilder.zeichnen(dict(b, ts=time.time()), zeilen, ordner / "bilder", cfg)
    toene, dauern, tonquelle = stimme.sprechen(zeilen, ordner / "ton", cfg, stimme.schluessel(cfg, geheim))
    video.bauen(bild_dateien, toene, dauern, ordner / "video.mp4", cfg, **video.ut_formate(cfg, zeilen, b))
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    (ordner / "meta.json").write_text(json.dumps({"titel": b["titel"], "zeilen": zeilen, "fakten": b["fakten"],
                                                  "stimme": tonquelle, "dauer_s": round(sum(dauern), 1),
                                                  "pruefung": fehler or "bestanden"}, ensure_ascii=False, indent=2))
    print(f"Warum-Video {b['base']}: {round(sum(dauern), 1)} s, {len(zeilen)} Szenen, Stimme {tonquelle}, "
          f"Kerzen {len(kerzen)}, Pruefung", fehler or "bestanden")
    if args.senden:
        vorschlag(args, geheim, cfg, ordner, f"🔍 Why did it move? ({b['base']})\nStimme: {tonquelle}" + bild_hw + (
            "\n⚠️ " + "; ".join(fehler) if fehler else ""), fehler)
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
    txt["telegram"] = links.mit_telegram_link(txt["telegram"], "coincheck", ordner.name, pfad=f"/coin/{base.lower()}/")
    (ordner / "post_x.txt").write_text(txt["x"], encoding="utf-8")
    (ordner / "post_telegram.txt").write_text(txt["telegram"], encoding="utf-8")
    (ordner / "fakten.json").write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Coin-Check {base}: Pruefung", fehler or "bestanden")
    if args.senden:
        vorschlag(args, geheim, cfg, ordner, "⚠️ " + "; ".join(fehler) if fehler else "", fehler)
    stand[base] = time.time()
    stand_p.write_text(json.dumps(stand))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
