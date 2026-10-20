"""Krypto-News aus US- und deutschen Quellen: einsammeln, buendeln, auswaehlen.

Es werden nur Titel und Kurztext der Feeds gelesen. Claude schreibt daraus einen EIGENEN Text
(nie kopieren), jede Zahl muss in den Quelltexten stehen, die Quelle wird immer genannt.
"""
from __future__ import annotations

import email.utils
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
import yaml

HIER = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "WhaleSqueeze-Redaktion/0.1 (+https://whalesqueeze.com; kontakt@whalesqueeze.com)"}

KRYPTO = re.compile(r"\b(krypto\w*|crypto\w*|bitcoin|btc|ether(eum)?|eth|stablecoin\w*|token\w*|blockchain|"
                    r"digital asset\w*|mica|defi|solana|xrp|ripple|binance|coinbase)\b", re.I)
# Woerter, die eine Meldung wichtiger machen (Gewicht)
WICHTIG = {
    r"\betf\b": 2.0, r"\bsec\b": 1.5, r"\bhack\w*|exploit\w*|gestohlen|stolen": 2.0, r"\bverbot\w*|\bban\w*": 1.5,
    r"\bfed\b|zins\w*|interest rate": 1.2, r"\bbitcoin\b|\bbtc\b": 1.0, r"\blisting\b|listet": 0.8,
    r"\bmica\b|bafin|regulier\w*|regulat\w*": 1.2, r"\binsolven\w*|bankrupt\w*|pleite": 1.5,
}
EIL = re.compile(r"\betf\b.*\b(approv|genehmig|zugelassen)|\bhack\w*|exploit|insolven|bankrupt|verbot|\bban\b", re.I)
STOPP = set("the a an of to in on for and or with is are was be by at from as that this it its new says after "
            "der die das ein eine und oder mit von im in am auf für ist sind wird werden nach zu den dem des "
            "crypto krypto news price preis kurs".split())


def quellen() -> list[dict]:
    return yaml.safe_load((HIER / "inhalte" / "quellen.yaml").read_text(encoding="utf-8"))


def _text(el, *namen) -> str:
    for n in namen:
        x = el.find(n)
        if x is not None and (x.text or "").strip():
            return x.text.strip()
    return ""


def _sauber(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    return re.sub(r"\s+", " ", s).strip()


def _zeit(s: str) -> float | None:
    if not s:
        return None
    try:
        return email.utils.parsedate_to_datetime(s).timestamp()
    except (TypeError, ValueError):
        pass
    try:
        import datetime as dt
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse_feed(xml_text: str, quelle: dict) -> list[dict]:
    """RSS 2.0 und Atom, nur Standardbibliothek."""
    xml_text = re.sub(r' xmlns(:\w+)?="[^"]+"', "", xml_text, count=20)   # Namensraeume weg = einfacher
    xml_text = re.sub(r"<(/?)\w+:(\w+)", r"<\1\2", xml_text)
    root = ET.fromstring(xml_text)
    items = root.findall(".//item") or root.findall(".//entry")
    out = []
    for it in items:
        titel = _sauber(_text(it, "title"))
        link = _text(it, "link")
        if not link:
            le = it.find("link")
            link = le.get("href", "") if le is not None else ""
        kurz = _sauber(_text(it, "description", "summary", "encoded", "content"))[:900]
        ts = _zeit(_text(it, "pubDate", "published", "updated", "date"))
        if not titel or not link:
            continue
        if quelle.get("filter") == "krypto" and not KRYPTO.search(titel + " " + kurz):
            continue
        out.append({"quelle": quelle["name"], "land": quelle.get("land"), "gewicht": quelle.get("gewicht", 1.0),
                    "offiziell": bool(quelle.get("offiziell")), "titel": titel, "link": link, "kurz": kurz, "ts": ts})
    return out


def einsammeln(stunden: float = 12, jetzt: float | None = None, laden=None) -> tuple[list[dict], dict]:
    """Alle Feeds lesen. Gibt (Meldungen, Status je Quelle) zurueck."""
    jetzt = jetzt or time.time()
    laden = laden or (lambda url: requests.get(url, headers=UA, timeout=20).text)
    alle, status = [], {}
    for q in quellen():
        try:
            items = parse_feed(laden(q["url"]), q)
            frisch = [i for i in items if i["ts"] is None or jetzt - i["ts"] <= stunden * 3600]
            alle += frisch
            status[q["name"]] = f"ok ({len(frisch)} neu)"
        except Exception as e:  # ein kaputter Feed darf den Rest nicht stoppen
            status[q["name"]] = f"Fehler: {type(e).__name__}"
    return alle, status


def _woerter(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-zäöüß0-9$]{3,}", s.lower()) if w not in STOPP}


def buendeln(meldungen: list[dict], schwelle: float = 0.28) -> list[dict]:
    """Meldungen zum selben Ereignis zusammenfassen (aehnliche Woerter im Titel)."""
    gruppen: list[dict] = []
    for m in sorted(meldungen, key=lambda m: -(m["ts"] or 0)):
        w = _woerter(m["titel"])
        beste, wert = None, 0.0
        for g in gruppen:
            j = len(w & g["woerter"]) / max(1, len(w | g["woerter"]))
            if j > wert:
                beste, wert = g, j
        if beste and wert >= schwelle:
            beste["meldungen"].append(m)
            beste["woerter"] |= w
        else:
            gruppen.append({"meldungen": [m], "woerter": set(w)})
    for g in gruppen:
        g["quellen"] = sorted({m["quelle"] for m in g["meldungen"]})
        text = " ".join(m["titel"] + " " + m["kurz"] for m in g["meldungen"])
        bonus = sum(v for k, v in WICHTIG.items() if re.search(k, text, re.I))
        g["punkte"] = round(sum(max(m["gewicht"] for m in g["meldungen"] if m["quelle"] == q) for q in g["quellen"])
                            + bonus, 2)
        g["eil"] = bool(EIL.search(text)) and len(g["quellen"]) >= 3
        g["schluessel"] = " ".join(sorted(list(g["woerter"]))[:12])
    return sorted(gruppen, key=lambda g: -g["punkte"])


def schon_gezeigt(gruppe: dict, stand: dict) -> bool:
    links = {m["link"] for m in gruppe["meldungen"]}
    if links & set(stand.get("links", [])):
        return True
    for alt in stand.get("woerter", []):   # gleiches Ereignis, andere Links
        a = set(alt)
        if len(a & gruppe["woerter"]) / max(1, len(a | gruppe["woerter"])) >= 0.35:
            return True
    return False


def stand_laden(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {"links": [], "woerter": [], "eil": []}


def stand_merken(p: Path, gruppe: dict, eil: bool = False) -> None:
    s = stand_laden(p)
    s["links"] = (s["links"] + [m["link"] for m in gruppe["meldungen"]])[-500:]
    s["woerter"] = (s["woerter"] + [sorted(gruppe["woerter"])])[-100:]
    if eil:
        s["eil"] = (s.get("eil", []) + [time.time()])[-20:]
    p.write_text(json.dumps(s, ensure_ascii=False))
