"""Lern-Beitraege (Trading lernen, Kaufzonen verstehen, Weg zu 100.000 €, Betrug) als Bild + Text.
Die Themen stehen in inhalte/wissen.yaml. Reihenfolge: das am laengsten nicht gezeigte Thema zuerst."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import yaml

from .design import de

HIER = Path(__file__).resolve().parent.parent


def themen() -> list[dict]:
    """Themen in der Kanal-Sprache: wissen.yaml (Englisch, seit 26.10.2026) bzw. wissen_de.yaml."""
    from . import design
    datei = "wissen_de.yaml" if design.SPRACHE == "de" else "wissen.yaml"
    return yaml.safe_load((HIER / "inhalte" / datei).read_text(encoding="utf-8"))


def naechstes(stand_datei: Path, thema_id: str | None = None) -> dict:
    alle = themen()
    if thema_id:
        return next(t for t in alle if t["id"] == thema_id)
    stand = json.loads(stand_datei.read_text()) if stand_datei.exists() else {}
    return min(alle, key=lambda t: stand.get(t["id"], 0))


def merken(stand_datei: Path, thema_id: str, ts: float) -> None:
    stand = json.loads(stand_datei.read_text()) if stand_datei.exists() else {}
    stand[thema_id] = ts
    stand_datei.write_text(json.dumps(stand, indent=1))


def texte(t: dict, cfg: dict) -> dict:
    tg = [f"📚 <b>{t['titel']}</b>", ""]
    tg += [f"• {p}" for p in t["punkte"]]
    tg += ["", f"<i>{cfg['hinweise']['post_text']}</i>"]
    return {"x": t["x"], "telegram": "\n".join(tg)}


def _grafik(img, t, th, box):
    """Passende Grafik je Thema (Werte nachgerechnet, siehe tests/test_wissen.py)."""
    from . import design, grafik as g
    from .design import MINUS
    if design.SPRACHE == "de":
        return _grafik_de(img, t, th, box)
    i = t["id"]
    if i == "risiko-1-prozent":
        g.linien(img, th, box, [
            {"name": "1% risk", "werte": [100 * 0.99 ** n for n in range(11)], "farbe": th.akzent, "endtext": "90.4%"},
            {"name": "5% risk", "werte": [100 * 0.95 ** n for n in range(11)], "farbe": th.minus, "endtext": "59.9%"},
        ], ["0", "", "2", "", "4", "", "6", "", "8", "", "10"], titel="Account balance after losses in a row",
            y_min=55, y_max=100)
    elif i == "verlust-falle":
        g.balken(img, th, box, [
            {"label": "−20%", "wert": 25, "text": "+25%", "farbe": th.akzent},
            {"label": "−50%", "wert": 100, "text": "+100%", "farbe": th.akzent2},
            {"label": "−90%", "wert": 900, "text": "+900%", "farbe": th.minus},
        ], titel="Loss → gain needed to get back to even")
    elif i == "hebel":
        g.balken(img, th, box, [
            {"label": f"{h}x", "wert": 100 / h, "text": f"{de(100 / h, 0)}%",
             "farbe": [th.akzent, th.akzent, th.akzent2, th.minus, th.minus][k]}
            for k, h in enumerate([2, 5, 10, 20, 50])
        ], titel="Move against you that wipes out the position (simplified)")
    elif i == "weg-100k-200":
        g.balken(img, th, box, [
            {"label": "0% return", "wert": 41.7, "text": "41.7 years", "farbe": th.minus},
            {"label": "5% return", "wert": 22.6, "text": "22.6 years", "farbe": th.akzent2},
            {"label": "7% return", "wert": 19.6, "text": "19.6 years", "farbe": th.akzent},
        ], titel="Years to $100,000 at $200 a month (return assumed)")
    elif i == "erste-10k":
        g.balken(img, th, box, [
            {"label": f"{['1st', '2nd', '3rd', '4th', '5th'][k - 1]} $10k", "wert": m, "text": f"{m} months",
             "farbe": th.minus if k == 1 else th.akzent}
            for k, m in enumerate([45, 35, 29, 24, 22], 1)
        ], titel="Months per $10,000 ($200 a month, 7% assumed)")
    elif i == "zinseszins":
        g.linien(img, th, box, [
            {"name": "8% a year", "werte": [100 * 1.08 ** j for j in range(31)], "farbe": th.akzent,
             "endtext": "$1,006"},
        ], ["0"] + [""] * 9 + ["10"] + [""] * 9 + ["20"] + [""] * 9 + ["30 years"], titel="$100 turns into …",
            y_min=0)
    elif i == "unterstuetzung":
        g.schema(img, th, box, "unterstuetzung")
    elif i == "liquiditaetszone":
        g.schema(img, th, box, "liquiditaet")
    elif i == "pump-and-dump":
        g.schema(img, th, box, "pump")
    elif i == "fake-guru":
        g.liste_x(img, th, box, ["never shows losses", "promises fixed returns", "rushes you",
                                 "sells expensive groups", "hides own positions"])
    else:
        return False
    _ = MINUS
    return True


def _grafik_de(img, t, th, box):
    """Deutsche Fassung (bis 26.10.2026)."""
    from . import grafik as g
    from .design import MINUS
    i = t["id"]
    if i == "risiko-1-prozent":
        g.linien(img, th, box, [
            {"name": "1 % Risiko", "werte": [100 * 0.99 ** n for n in range(11)], "farbe": th.akzent, "endtext": "90,4 %"},
            {"name": "5 % Risiko", "werte": [100 * 0.95 ** n for n in range(11)], "farbe": th.minus, "endtext": "59,9 %"},
        ], ["0", "", "2", "", "4", "", "6", "", "8", "", "10"], titel="Kontostand nach Verlusten in Folge",
            y_min=55, y_max=100)
    elif i == "verlust-falle":
        g.balken(img, th, box, [
            {"label": "−20 %", "wert": 25, "text": "+25 %", "farbe": th.akzent},
            {"label": "−50 %", "wert": 100, "text": "+100 %", "farbe": th.akzent2},
            {"label": "−90 %", "wert": 900, "text": "+900 %", "farbe": th.minus},
        ], titel="Verlust → nötiger Gewinn bis zurück auf null")
    elif i == "hebel":
        g.balken(img, th, box, [
            {"label": f"{h}-fach", "wert": 100 / h, "text": f"{de(100 / h, 0)} %",
             "farbe": [th.akzent, th.akzent, th.akzent2, th.minus, th.minus][k]}
            for k, h in enumerate([2, 5, 10, 20, 50])
        ], titel="Gegenbewegung bis zum Totalverlust (vereinfacht)")
    elif i == "weg-100k-200":
        g.balken(img, th, box, [
            {"label": "0 % Rendite", "wert": 41.7, "text": "41,7 Jahre", "farbe": th.minus},
            {"label": "5 % Rendite", "wert": 22.6, "text": "22,6 Jahre", "farbe": th.akzent2},
            {"label": "7 % Rendite", "wert": 19.6, "text": "19,6 Jahre", "farbe": th.akzent},
        ], titel="Jahre bis 100.000 € mit 200 € im Monat (Rendite angenommen)")
    elif i == "erste-10k":
        g.balken(img, th, box, [
            {"label": f"{k}. 10.000 €", "wert": m, "text": f"{m} Monate",
             "farbe": th.minus if k == 1 else th.akzent}
            for k, m in enumerate([45, 35, 29, 24, 22], 1)
        ], titel="Monate je 10.000 € (200 € im Monat, 7 % angenommen)")
    elif i == "zinseszins":
        g.linien(img, th, box, [
            {"name": "8 % im Jahr", "werte": [100 * 1.08 ** j for j in range(31)], "farbe": th.akzent,
             "endtext": "1.006 €"},
        ], ["0"] + [""] * 9 + ["10"] + [""] * 9 + ["20"] + [""] * 9 + ["30 Jahre"], titel="Aus 100 € werden …",
            y_min=0)
    elif i == "unterstuetzung":
        g.schema(img, th, box, "unterstuetzung")
    elif i == "liquiditaetszone":
        g.schema(img, th, box, "liquiditaet")
    elif i == "pump-and-dump":
        g.schema(img, th, box, "pump")
    elif i == "fake-guru":
        g.liste_x(img, th, box, ["zeigt nie Verluste", "verspricht feste Renditen", "drängt zur Eile",
                                 "verkauft teure Gruppen", "verschweigt eigene Positionen"])
    else:
        return False
    _ = MINUS
    return True


def bild(t: dict, cfg: dict, ziel: Path, tag: str | None = None) -> Path:
    import datetime as _dt
    from PIL import ImageDraw
    from .design import absatz, etikett, fuss, hintergrund, marke, punkte, thema_waehlen, ueberschrift
    tag = tag or _dt.date.today().isoformat()
    th = thema_waehlen("wissen", f"{tag}:{t['id']}")
    W, H = 1080, 1350
    img = hintergrund(th, W, H, saat=len(t["id"]))
    marke(img, th, 80, 64, 64)
    d = ImageDraw.Draw(img)
    etikett(d, th, 80, 170, t["saeule"].upper())
    y = ueberschrift(d, th, 80, 252, t["titel"], W - 160, groesse=66, max_zeilen=3) + 26
    box = (80, y, W - 80, y + 470)
    if _grafik(img, t, th, box):
        y = box[3] + 34
    else:
        y = absatz(d, th, 80, y, t["gross"], W - 160, groesse=110, farbe=th.akzent, gewicht="Bold")
        y = absatz(d, th, 80, y, t["gross_text"], W - 160, groesse=32, farbe=th.neben) + 20
    d = ImageDraw.Draw(img)
    punkte(d, th, 80, y, t["punkte"], W - 160, groesse=29, bis_y=H - 120)
    fuss(img, th, cfg["hinweise"]["fusszeile"])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(ziel)
    return ziel
