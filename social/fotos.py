"""Foto-Bibliothek echter Personen mit freier Lizenz (Wunsch Tobias 06.11.2026).

Quelle: Wikimedia Commons (offizielle US-Regierungsfotos sind gemeinfrei, dazu CC0/CC BY/CC BY-SA).
Nie: Pressefotos (Reuters/AP/Getty), Lizenzen mit NC (nicht kommerziell) oder ND (keine Bearbeitung), KI-Bilder
echter Personen, veraenderte Gesichter. Bei CC BY/CC BY-SA steht der Fotograf klein im Bild (Lizenzpflicht, kein
Quellenhinweis zur Nachricht).

Ablage: <BASIS>/fotos/<slug>/<n>.jpg + <BASIS>/fotos/fotos.json {slug: [{datei, lizenz, credit, seite, titel}]}.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import requests
import yaml

HIER = Path(__file__).resolve().parent.parent
COMMONS = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "WhaleSqueezeEditorial/1.0 (photo library; free licenses only)"}
AUSSCHLUSS = ("caricature", "cartoon", "meme", "signature", "logo", "collage", "mural", "statue", "wax", "drawing",
              "painting", "protest", "sign ", "poster", "graffiti", "puppet", "mask", "effigy", "flag", "map", "coin",
              "stamp", "banner", "illustration", "ai-generated", "ai generated", "screenshot")


def _klar(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def lizenz(meta: dict) -> tuple[bool, str, str]:
    """-> (erlaubt, Kurzname, Credit-Zeile oder ''). meta = extmetadata von Commons."""
    kurz = _klar((meta.get("LicenseShortName") or {}).get("value", ""))
    k = kurz.lower().replace("-", " ")
    if not kurz or "nc" in k.split() or "nd" in k.split() or "non free" in k or "fair use" in k:
        return False, kurz, ""
    if k.startswith(("public domain", "pd", "cc0")) or k == "no restrictions":
        return True, kurz, ""
    if re.match(r"cc by( sa)? \d", k):
        autor = _klar((meta.get("Artist") or {}).get("value", ""))[:40] or "Wikimedia Commons"
        return True, kurz, f"Photo: {autor} · {kurz}"
    return False, kurz, ""


def suchen(person: dict, n: int = 5, get=requests.get) -> list[dict]:
    """Kandidaten auf Commons: frei lizenziert, gross genug, Nachname im Titel, keine Karikaturen/Plakate/Logos.
    Offizielle Portraets zuerst."""
    j = get(COMMONS, params={"action": "query", "format": "json", "generator": "search",
                             "gsrsearch": f"filetype:bitmap {person['suche']}", "gsrnamespace": 6, "gsrlimit": 40,
                             "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1600},
            headers=UA, timeout=30).json()
    seiten = sorted(((j.get("query") or {}).get("pages") or {}).values(), key=lambda p: p.get("index", 99))
    out = []
    for s in seiten:
        titel = s.get("title", "")
        klein = titel.lower()
        info = (s.get("imageinfo") or [{}])[0]
        if (person.get("muss", "").lower() not in klein or any(w in klein for w in AUSSCHLUSS)
                or titel in (person.get("ohne") or [])):   # „ohne“: von Tobias aussortierte Fotos
            continue
        if info.get("mime") not in ("image/jpeg", "image/png") or min(info.get("width", 0), info.get("height", 0)) < 800:
            continue
        ok, kurz, credit = lizenz(info.get("extmetadata") or {})
        if not ok:
            continue
        out.append({"titel": titel, "url": info.get("thumburl") or info.get("url"), "seite": info.get("descriptionurl"),
                    "lizenz": kurz, "credit": credit, "offiziell": "official" in klein or "portrait" in klein})
    out.sort(key=lambda c: (not c["offiziell"], bool(c["credit"])))   # offiziell + gemeinfrei zuerst
    return out[:n]


def holen(ziel: Path, personen: list[dict] | None = None, n: int = 5, get=requests.get) -> dict:
    """Laedt die Bibliothek (vorhandene Personen bleiben, wenn die Suche nichts liefert). Rueckgabe: fotos.json."""
    personen = personen or yaml.safe_load((HIER / "inhalte" / "personen.yaml").read_text(encoding="utf-8"))
    index_p = ziel / "fotos.json"
    index = json.loads(index_p.read_text()) if index_p.exists() else {}
    for p in personen:
        try:
            kandidaten = suchen(p, n, get)
        except Exception as e:
            print("Commons-Suche fehlgeschlagen:", p["slug"], e)
            continue
        if not kandidaten:
            print("Keine freien Fotos:", p["slug"])
            continue
        ordner = ziel / p["slug"]
        ordner.mkdir(parents=True, exist_ok=True)
        liste = []
        for i, k in enumerate(kandidaten, 1):
            datei = ordner / f"{i}.jpg"
            try:
                r = get(k["url"], headers=UA, timeout=60)
                datei.write_bytes(r.content)
            except Exception as e:
                print("Download fehlgeschlagen:", k["titel"], e)
                continue
            liste.append({"datei": f"{p['slug']}/{datei.name}", "lizenz": k["lizenz"], "credit": k["credit"],
                          "seite": k["seite"], "titel": k["titel"], "name": p["name"]})
        if liste:
            index[p["slug"]] = liste
    ziel.mkdir(parents=True, exist_ok=True)
    index_p.write_text(json.dumps(index, ensure_ascii=False, indent=1))
    return index


def waehlen(ziel: Path, slug: str, schluessel: str = "") -> dict | None:
    """Ein Foto der Person (gleicher Beitrag = gleiches Foto, verschiedene Beitraege wechseln ab)."""
    try:
        index = json.loads((ziel / "fotos.json").read_text())
    except Exception:
        return None
    liste = [f for f in index.get(slug.lower(), []) if (ziel / f["datei"]).exists()]
    if not liste:
        return None
    f = liste[int(hashlib.md5(schluessel.encode()).hexdigest(), 16) % len(liste)]
    return dict(f, pfad=str(ziel / f["datei"]))


def sicher(ziel: Path, slug: str, schluessel: str = "", holen_=None) -> dict | None:
    """Foto der Person; fehlt sie in der Bibliothek, sofort bei Wikimedia Commons nachladen (nur Personen aus
    inhalte/personen.yaml, nur freie Lizenzen). Wunsch Tobias 12./13.11.2026: Eilmeldungen immer mit Bild."""
    import yaml
    f = waehlen(ziel, slug, schluessel)
    if f:
        return f
    liste = yaml.safe_load((Path(__file__).resolve().parent.parent / "inhalte" / "personen.yaml")
                           .read_text(encoding="utf-8")) or []
    p = [x for x in liste if x.get("slug") == slug]
    if not p:
        return None
    try:
        (holen_ or holen)(ziel, p)
    except Exception as e:
        print("Foto nicht nachgeladen:", slug, e)
        return None
    return waehlen(ziel, slug, schluessel)
