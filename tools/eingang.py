"""Beitraege aus dem Redaktions-Chat (Branch 'warteschlange' im Repository) als Vorschlag an Tobias.

Ablauf: Claude legt im Chat einen Ordner warteschlange/<name>/ mit post.png, post_x.txt, post_telegram.txt
an und schiebt ihn auf den Branch 'warteschlange'. plan.sh holt den Branch nach /opt/volumen-social/eingang,
dieses Skript prueft jeden neuen Ordner und schickt ihn mit Freigabe-Knoepfen an Tobias.
Gepostet wird erst, wenn Tobias einen Knopf drueckt.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
from social import telegram  # noqa: E402

BASIS = Path(os.environ.get("SOCIAL_GEHEIM", "/opt/volumen-social"))
AUSGABE = Path(os.environ.get("SOCIAL_AUSGABE", BASIS / "ausgabe"))
EINGANG = Path(os.environ.get("SOCIAL_EINGANG", BASIS / "eingang"))
FOTOS = Path(os.environ.get("SOCIAL_FOTOS", BASIS / "fotos"))


def pruefen(ordner: Path, cfg: dict, sperr: set[str]) -> list[str]:
    fehler = []
    for f in ("post.png", "post_x.txt", "post_telegram.txt"):
        if not (ordner / f).exists():
            fehler.append(f"{f} fehlt")
    if fehler:
        return fehler
    x = (ordner / "post_x.txt").read_text(encoding="utf-8")
    tg = (ordner / "post_telegram.txt").read_text(encoding="utf-8")
    if len(x) > 280:
        fehler.append(f"X-Text zu lang ({len(x)} Zeichen)")
    hw = (cfg["hinweise"].get("post_text") or "Keine Anlageberatung").rstrip(".")
    if hw not in x + tg and "Keine Anlageberatung" not in x + tg:
        fehler.append("Risiko-Hinweis fehlt")
    text = (x + " " + tg)
    for h in (h for h in cfg["hinweise"].values() if h):   # leere Hinweise ueberspringen
        text = text.replace(h, " ")
    klein = text.replace("Keine Anlageberatung", " ").lower()
    fehler += [f"verbotene Wendung: '{w}'" for w in cfg["pruefung"]["verboten"] if w in klein]
    import re
    fehler += [f"Coin auf der Sperrliste: {c}" for c in sperr if re.search(rf"\b{re.escape(c)}\b", text, re.I)]
    return fehler


def post_chart(ziel: Path, kerzen_holen=None) -> str:
    """13.11.2026 (Wunsch Tobias: „Bilder vom Kursverlauf“): post_chart.json = {"chart": {...wie im Reel}} zeichnet
    den ECHTEN Kursverlauf (Kurse nur vom Server) in post.png und setzt {chg}, {ema}, {hoch} ... in post_x.txt und
    post_telegram.txt ein. Klappt es nicht: *_ohne.txt (Pflicht, falls Platzhalter) und ein Hinweis an Tobias."""
    from social import kurse, reel
    spec = json.loads((ziel / "post_chart.json").read_text(encoding="utf-8"))
    try:
        p, werte = reel.chart_szene(ziel, {"bild": "post.png", "chart": spec["chart"]}, ziel.name,
                                    kerzen_holen or (lambda b, i, n: kurse.kerzen(b, i, n)))
        shutil.move(p, ziel / "post.png")
        for f in ("post_x.txt", "post_telegram.txt"):
            if (ziel / f).exists():
                t = (ziel / f).read_text(encoding="utf-8")
                (ziel / f).write_text(t.format(**werte) if "{" in t else t, encoding="utf-8")
        return "\n📈 Echter Kursverlauf im Bild: " + ", ".join(f"{k} {v}" for k, v in werte.items())
    except Exception as e:
        for f in ("post_x.txt", "post_telegram.txt"):
            ohne = ziel / f.replace(".txt", "_ohne.txt")
            if ohne.exists():
                shutil.copy(ohne, ziel / f)
        return f"\n⚠️ Kursverlauf nicht gezeichnet ({str(e)[:80]}), Text ohne Kurszahlen"


def foto_nachladen(spec: dict, holen=None) -> bool:
    """12.11.2026 (MSTR-Eilmeldung ohne Saylor-Foto): fehlt die Person in der Bibliothek, sofort bei Wikimedia
    Commons nachladen (nur freie Lizenzen, wie fotos_holen.py), statt ohne Foto zu posten."""
    from social import fotos
    slug = str(spec.get("person", "")).lower()
    if not slug or fotos.waehlen(FOTOS, slug):
        return False
    personen = yaml.safe_load((HIER / "inhalte" / "personen.yaml").read_text(encoding="utf-8")) or []
    p = [x for x in personen if x.get("slug") == slug]
    if not p:
        return False
    try:
        (holen or fotos.holen)(FOTOS, p)
    except Exception as e:
        print("Foto nicht nachgeladen:", slug, e)
        return False
    return bool(fotos.waehlen(FOTOS, slug))


def hingucker(ziel: Path, geheim: dict, holen=None) -> str:
    """hingucker.png zeichnen, Test-Gruppe zuteilen, Vorschau an Tobias. Rueckgabe: Zeile fuer den Hinweis.
    Mit "titelbild": true (Wunsch Tobias 12.11.2026) wird das Foto auf ALLEN Kanaelen das erste Bild
    (Karussell: Foto, dann Beitragsbild), ohne Bild-Test."""
    from social import bildpaket
    try:
        spec = json.loads((ziel / "hingucker.json").read_text(encoding="utf-8"))
    except Exception:
        spec = {}
    nachgeladen = spec.get("art") != "vergleich" and foto_nachladen(spec, holen)
    try:
        bild = bildpaket.aus_spec(ziel, FOTOS)
    except Exception as e:
        return f"\n🖼 Hingucker nicht gezeichnet ({str(e)[:100]})"
    if not bild:
        return "\n🖼 Kein freies Foto dieser Person in der Bibliothek, X bekommt nur das Beitragsbild."
    zusatz = " (Foto eben nachgeladen)" if nachgeladen else ""
    if spec.get("titelbild"):   # Hochformat-Titelbild statt 16:9-Hingucker (Instagram schneidet sonst zu)
        from social import fotos
        foto = fotos.waehlen(FOTOS, str(spec.get("person", "")), ziel.name)
        titel = ziel / "titelbild.png"
        bildpaket.foto_titel(foto, spec.get("kopf", ""), spec.get("unter", ""), spec.get("etikett", "BREAKING")
                             ).convert("RGB").save(titel)
        (ziel / "karussell.json").write_text(json.dumps({"folien": [titel.name, "post.png"]}), encoding="utf-8")
        (ziel / "bildtest.json").unlink(missing_ok=True)
        bild.unlink(missing_ok=True)   # X bekommt das Karussell, nicht zusaetzlich den 16:9-Hingucker
        return f"\n🖼 Foto als erstes Bild auf allen Kanälen, danach das Beitragsbild{zusatz}"
    art = bildpaket.test_zuteilen(ziel, AUSGABE / "bildtest_stand.json")
    if art == "mit":
        telegram.foto_an_tobias(geheim, bild, "🖼 Hingucker (X bekommt 2 Bilder nebeneinander)")
        return "\n🖼 Bild-Test: MIT Hingucker auf X (Vorschau oben)" + zusatz
    return "\n🖼 Bild-Test: OHNE Hingucker (Vergleichsgruppe, X bekommt nur das Beitragsbild)"


def main() -> int:
    cfg = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
    gp = BASIS / "secrets.yaml"
    geheim = (yaml.safe_load(gp.read_text()) if gp.exists() else {}) or {}
    sp = BASIS / "sperrliste.txt"
    sperr = {z.split("#")[0].strip().upper() for z in (sp.read_text().splitlines() if sp.exists() else [])
             if z.split("#")[0].strip()}
    stand_p = AUSGABE / "eingang_stand.json"
    stand = json.loads(stand_p.read_text()) if stand_p.exists() else []
    if not EINGANG.is_dir():
        return 0
    for o in sorted(p for p in EINGANG.iterdir() if p.is_dir()):
        if o.name in stand:
            continue
        ziel = AUSGABE / f"chat_{o.name}"
        shutil.copytree(o, ziel, dirs_exist_ok=True)
        chart_hw = post_chart(ziel) if (ziel / "post_chart.json").exists() else ""
        fehler = pruefen(ziel, cfg, sperr)
        ton = ""
        if (ziel / "reel.json").exists() and not (ziel / "video.mp4").exists():   # Reel: Server spricht + schneidet
            from social import reel
            try:
                ton = "\n🎙 Ton: " + reel.bauen(ziel, cfg, geheim)
            except Exception as e:
                fehler.append(f"Reel nicht gebaut ({str(e)[:120]}), nur Bild")
        bild_hw = ""
        if (ziel / "hingucker.json").exists():   # 06.11.2026: Hingucker-Bild fuer X (Foto/Zitat/Vergleich)
            bild_hw = hingucker(ziel, geheim)
        hinweis = ("💬 Aus dem Redaktions-Chat" + ton + chart_hw + bild_hw
                   + ("\n⚠️ " + "; ".join(fehler) if fehler else ""))
        if not (ziel / "post.png").exists():
            gesendet = telegram.text_senden(geheim, hinweis)
        else:
            gesendet = telegram.vorschlag_senden(geheim, ziel, hinweis)
        if not gesendet:   # beim naechsten Lauf noch einmal versuchen, statt still zu verschwinden
            print("Eingang:", o.name, "NICHT zugestellt, neuer Versuch beim naechsten Lauf")
            continue
        stand.append(o.name)
        print("Eingang:", o.name, fehler or "ok")
    stand_p.write_text(json.dumps(stand[-500:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
