"""Bilder 1080x1920 je Szene (gesichtslos: Zahlen, Balken, Untertitel).

Sichere Zonen fuer TikTok/Reels/Shorts: oben ~200 px und unten ~380 px sowie rechts ~140 px
werden von den App-Knoepfen verdeckt. Wichtige Inhalte liegen dazwischen.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .sprache import T, zahl

from . import design

_GEWICHT = {"Black": "Bold", "ExtraBold": "Bold", "Bold": "Bold", "SemiBold": "SemiBold", "Medium": "Medium",
            "Regular": "Regular"}


def _font(gewicht: str, groesse: int) -> ImageFont.FreeTypeFont:
    """Space Grotesk aus dem Corporate Design (assets/schrift)."""
    return design.font(_GEWICHT.get(gewicht, "Regular"), groesse)


def _hex(c: str) -> tuple[int, int, int]:
    return design.rgb(c)


class Leinwand:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.W, self.H = cfg["video"]["breite"], cfg["video"]["hoehe"]
        self.th = cfg.get("_thema") or design.THEMEN["nacht"]
        th = self.th
        self.f = {k: _hex(v) for k, v in {
            "grund": th.grund, "flaeche": th.karte, "text": th.text, "neben": th.neben, "linie": th.linie,
            "amber": th.akzent2, "plus": th.plus, "minus": th.minus}.items()}
        self.lang = cfg.get("sprache", "de")
        self.t = T[self.lang]
        self.pz = "%" if self.lang == "en" else " %"
        self._grund = None

    def neu(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        if self._grund is None:
            self._grund = design.hintergrund(self.th, self.W, self.H).convert("RGB")
        self.img = self._grund.copy()
        return self.img, ImageDraw.Draw(self.img)

    # ---------- Bausteine ----------
    def mitte(self, d, y, text, font, farbe):
        w = d.textlength(text, font=font)
        d.text(((self.W - w) / 2, y), text, font=font, fill=farbe)

    def logo(self, d, x, y, s=2.2):
        """Logo-Plakette aus dem Corporate Design (s = Groesse / 32 wie frueher)."""
        g = int(32 * s)
        self.img.paste(design.logo(g), (int(x), int(y)), design.logo(g))

    def kopf(self, d):
        """Marke + feste Fusszeile („Keine Anlageberatung“) oben in der sicheren Zone."""
        rgba = self.img.convert("RGBA")
        design.marke(rgba, self.th, 90, 205, 70)
        self.img.paste(rgba.convert("RGB"))
        d = ImageDraw.Draw(self.img)
        d.text((90, 300), self.cfg["hinweise"]["fusszeile"], font=_font("Medium", 31), fill=self.f["neben"])
        d.line([(90, 348), (self.W - 90, 348)], fill=self.f["linie"], width=2)

    def untertitel(self, d, text, y=1230):
        """Untertitel (viele schauen ohne Ton). Zahlen fett und in Leuchtminze (Wunsch Tobias 01.11.2026),
        damit sie beim Durchscrollen sofort auffallen."""
        if self.cfg.get("video", {}).get("untertitel_animiert"):   # seit 04.11.: animiert im Video (video.py)
            return
        text = text.replace(self.t["adresse_gesprochen"], ".com")   # Stimme sagt "Punkt com", Bild zeigt die Adresse
        breite_max = self.W - 140 - 80
        groesse = 50
        while True:
            normal, fett = _font("SemiBold", groesse), _font("Black", groesse + 4)
            zeilen = self._umbrechen(d, text.split(), normal, fett, breite_max)
            if len(zeilen) <= 4 or groesse <= 38:   # lange Saetze: kleiner statt abgeschnitten
                break
            groesse -= 4
        abstand = int(groesse * 1.32)
        hoehe = len(zeilen) * abstand + 50
        d.rounded_rectangle([70, y, self.W - 70, y + hoehe], radius=28, fill=self.f["flaeche"])
        leer = d.textlength(" ", font=normal)
        for i, worte in enumerate(zeilen):
            gesamt = sum(d.textlength(w, font=fett if self._ist_zahl(w) else normal) for w in worte) + leer * (len(worte) - 1)
            x = (self.W - gesamt) / 2
            for w in worte:
                zahl_wort = self._ist_zahl(w)
                f = fett if zahl_wort else normal
                d.text((x, y + 25 + i * abstand - (2 if zahl_wort else 0)), w, font=f,
                       fill=(self.f["minus"] if w.lstrip("($").startswith(("-", "−")) else self.f["plus"])
                       if zahl_wort else self.f["text"])
                x += d.textlength(w, font=f) + leer

    @staticmethod
    def _ist_zahl(wort: str) -> bool:
        return any(c.isdigit() for c in wort)

    def _umbrechen(self, d, worte, normal, fett, breite):
        zeilen, akt, w_akt = [], [], 0.0
        leer = d.textlength(" ", font=normal)
        for w in worte:
            lw = d.textlength(w, font=fett if self._ist_zahl(w) else normal)
            if akt and w_akt + leer + lw > breite:
                zeilen.append(akt)
                akt, w_akt = [], 0.0
            w_akt = lw if not akt else w_akt + leer + lw
            akt.append(w)
        if akt:
            zeilen.append(akt)
        return zeilen

    def farbe_wert(self, x):
        return self.f["plus"] if x >= 0 else self.f["minus"]

    # ---------- Szenen ----------
    def titel(self, daten, text):
        img, d = self.neu()
        self.kopf(d)
        self.mitte(d, 560, self.t["b_markt"], _font("Black", 104), self.f["text"])
        self.mitte(d, 690, self.t["b_30s"], _font("Black", 104), self.f["amber"])
        self.mitte(d, 860, daten["datum"].upper(), _font("SemiBold", 54), self.f["neben"])
        self.untertitel(d, text)
        return img

    def haken(self, daten, text):
        """Erste Szene: groesste Bewegung als riesige Zahl + „Warum?“ (Haken fuer die ersten 1-2 Sekunden)."""
        img, d = self.neu()
        self.kopf(d)
        c = daten["chg24"]
        self.mitte(d, 430, self.t["b_haken"], _font("Bold", 46), self.f["neben"])
        wert = f"{zahl(c, self.lang, True)}{self.pz}"
        gr = 260
        while d.textlength(wert, font=_font("Black", gr)) > self.W - 120 and gr > 140:
            gr -= 10
        self.mitte(d, 500, wert, _font("Black", gr), self.farbe_wert(c))
        self.mitte(d, 500 + gr + 30, f"{daten['base']} · {self.t['b_24h']}", _font("Black", 96), self.f["text"])
        frage = daten.get("_frage")   # A/B-Test: Frage gross im Bild statt „WHY? ↓“
        ff = 70
        while frage and d.textlength(frage, font=_font("Black", ff)) > self.W - 140 and ff > 40:
            ff -= 4
        self.mitte(d, 500 + gr + 170, frage or self.t["b_warum"], _font("Black", ff), self.f["amber"])
        self.mitte(d, 500 + gr + 270, str(daten.get("datum", "")).upper(), _font("SemiBold", 40), self.f["neben"])
        self.untertitel(d, text)
        return img

    # ---------- Whale of the day (Video) ----------
    def _wt(self):
        from .wal import W
        return W[self.lang]

    def wal_haken(self, w, text):
        img, d = self.neu()
        self.kopf(d)
        wt = self._wt()
        self.mitte(d, 420, wt["etikett"], _font("Bold", 46), self.f["neben"])
        self.mitte(d, 490, f"${w['base']}", _font("Black", 150), self.f["text"])
        if w.get("wal_7d") is not None:
            v = w["wal_7d"]
            gross, farbe = f"{zahl(v, self.lang, True)} {'pp' if self.lang == 'en' else 'PP'}", self.farbe_wert(v)
        else:
            gross, farbe = f"{zahl(w.get('wal') or 0, self.lang)}{self.pz}", self.f["plus"]
        self.mitte(d, 680, gross, _font("Black", 190), farbe)
        self.mitte(d, 920, w.get("_frage") or wt["v_frage"], _font("Black", 64), self.f["amber"])
        self.untertitel(d, text)
        return img

    def wal_verlauf(self, w, text):
        from . import grafik
        img, d = self.neu()
        self.kopf(d)
        wt = self._wt()
        v = w["verlauf"]
        tage = round((v[-1][0] - v[0][0]) / 86400)
        labels = [""] * len(v)
        labels[0], labels[-1] = wt["vor"].format(n=tage), wt["jetzt"]
        reihen = [{"name": wt["kurve_w"], "werte": [p[1] for p in v], "farbe": self.th.akzent}]
        if all(p[2] is not None for p in v):
            reihen.append({"name": wt["kurve_b"], "werte": [p[2] for p in v], "farbe": self.th.akzent2})
        rgba = img.convert("RGBA")
        self.mitte(d, 420, f"${w['base']}", _font("Black", 90), self.f["text"])
        grafik.linien(rgba, self.th, (60, 560, self.W - 60, 1150), reihen, labels, titel=wt["chart"],
                      einheit="%" if self.lang == "en" else " %", flaeche=False)
        self.img = rgba.convert("RGB")
        d = ImageDraw.Draw(self.img)
        self.mitte(d, 420, f"${w['base']}", _font("Black", 90), self.f["text"])
        self.untertitel(d, text)
        return self.img

    def wal_details(self, w, text):
        img, d = self.neu()
        self.kopf(d)
        wt = self._wt()
        self.mitte(d, 420, wt["v_details"], _font("Bold", 46), self.f["neben"])
        y = 520
        if w.get("boerse") is not None:
            self.mitte(d, y, f"{zahl(w['boerse'], self.lang)}{self.pz}", _font("Black", 160), self.f["amber"])
            self.mitte(d, y + 185, wt["kurve_b"].upper(), _font("Bold", 44), self.f["neben"])
            y += 300
        if w.get("holder") is not None:
            h = f"{int(w['holder']):,}"   # nur im Bild mit Tausendertrennung (Untertitel bleibt pruefbar)
            self.mitte(d, y, h if self.lang == "en" else h.replace(",", "."), _font("Black", 120), self.f["text"])
            self.mitte(d, y + 140, "HOLDERS" if self.lang == "en" else "HOLDER", _font("Bold", 44), self.f["neben"])
        self.untertitel(d, text)
        return img

    def breite(self, daten, text):
        img, d = self.neu()
        self.kopf(d)
        m = daten["median_24h"]
        self.mitte(d, 440, self.t["b_breite"], _font("Bold", 44), self.f["neben"])
        self.mitte(d, 520, f"{zahl(m, self.lang, True)}{self.pz}", _font("Black", 200), self.farbe_wert(m))
        self.mitte(d, 780, self.t["b_median"].format(anzahl=daten["anzahl"]), _font("Medium", 44), self.f["neben"])
        # Balken gruen/rot
        x0, x1, y0 = 120, self.W - 120, 900
        teil = x0 + (x1 - x0) * daten["anteil_plus"] / 100
        d.rounded_rectangle([x0, y0, x1, y0 + 56], radius=28, fill=self.f["minus"])
        if daten["anteil_plus"] > 0:
            d.rounded_rectangle([x0, y0, max(teil, x0 + 56), y0 + 56], radius=28, fill=self.f["plus"])
        f = _font("Bold", 40)
        d.text((x0, y0 + 80), self.t["b_plus"].format(p=daten["anteil_plus"]), font=f, fill=self.f["plus"])
        rot = self.t["b_minus"].format(p=100 - daten["anteil_plus"])
        d.text((x1 - d.textlength(rot, font=f), y0 + 80), rot, font=f, fill=self.f["minus"])
        self.untertitel(d, text)
        return img

    def mover(self, daten, text, nr=None, von=None):
        img, d = self.neu()
        self.kopf(d)
        if nr:
            self.mitte(d, 430, self.t["b_mover"].format(nr=nr, von=von), _font("Bold", 44), self.f["neben"])
        self.mitte(d, 500, daten["base"], _font("Black", 180), self.f["text"])
        c = daten["chg24"]
        self.mitte(d, 710, f"{zahl(c, self.lang, True)}{self.pz}  {self.t['b_24h']}", _font("Black", 100), self.farbe_wert(c))
        if not daten.get("ausloeser"):   # ohne bekannte Nachricht: gar keinen Hinweis zeigen
            self.untertitel(d, text)
            return img
        grund = self.t["b_ausloeser"].format(a=daten["ausloeser"]).upper()
        groesse = 38
        f = _font("Bold", groesse)
        while d.textlength(grund, font=f) + 70 > self.W - 160 and groesse > 24:
            groesse -= 2
            f = _font("Bold", groesse)
        w = d.textlength(grund, font=f) + 70
        x = (self.W - w) / 2
        farbe = self.f["amber"]
        d.rounded_rectangle([x, 900, x + w, 976], radius=38, outline=farbe, width=4)
        d.text((x + 35, 917), grund, font=f, fill=farbe)
        self.untertitel(d, text)
        return img

    # ---------- Lern-Video (S28, Wunsch Tobias 01.11.2026) ----------
    def lern_haken(self, t, text):
        """Erste Szene: grosse Zahl/Wort des Themas + kurze Erklaerung, Etikett „LEARN IN 20 SECONDS“."""
        img, d = self.neu()
        self.kopf(d)
        etikett = "LEARN IN 20 SECONDS" if self.lang == "en" else "IN 20 SEKUNDEN ERKLÄRT"
        from . import wissen
        wert = str(t["gross"])
        chart = t["id"] in wissen.CHART_ART   # Kerzen-Schema braucht mehr Hoehe
        gr, y0 = (130, 460) if chart else (180, 500)   # darunter kommt die Grafik (Wunsch Tobias 03.11.2026)
        while d.textlength(wert, font=_font("Black", gr)) > self.W - 140 and gr > 90:
            gr -= 10
        farbe = self.f["minus"] if wert.startswith(("-", "−")) else self.f["plus"]
        frage = t.get("_frage")
        if frage:   # A/B-Test: die Frage gross statt des Etiketts (wer stumm scrollt, sieht sie sofort)
            zeilen = textwrap.wrap(frage, width=26)[:2]
            for i, z in enumerate(zeilen):
                self.mitte(d, 372 + i * 58, z, _font("Black", 48), self.f["amber"])
            neu_y0 = 372 + 58 * len(zeilen) + 24
            if chart and neu_y0 > y0:   # Platz fuer die Grafik halten: Zahl etwas kleiner statt Grafik quetschen
                gr = max(90, gr - (neu_y0 - y0))
            y0 = max(y0, neu_y0)
        else:
            self.mitte(d, y0 - 62 if chart else 440, etikett, _font("Bold", 42 if chart else 46), self.f["amber"])
        self.mitte(d, y0, wert, _font("Black", gr), farbe)
        y = y0 + gr + 30
        for z in textwrap.wrap(t.get("gross_text", ""), width=30)[:2]:
            self.mitte(d, y, z, _font("Bold", 50), self.f["text"])
            y += 64
        rgba = self.img.convert("RGBA")   # Vorschau: das fertige Bild (letzter Schritt) als Haken
        if wissen.video_grafik(rgba, t, self.th, (60, y + 30 if chart else max(y + 30, 820), self.W - 60, 1200), 3,
                               self.lang, t.get("_echt")):
            self.img.paste(rgba.convert("RGB"))
        d = ImageDraw.Draw(self.img)
        self.untertitel(d, text)
        return self.img

    def lern_punkt(self, daten, text):
        """Ein Punkt des Themas: Schritt + Fortschritt oben, Ergebnis-Zahl, darunter die GRAFIK (Kerzen-Schema, das
        sich je Punkt aufbaut, oder das Diagramm des Themas; Wunsch Tobias 03.11.2026), der Satz als Untertitel."""
        import re as _re
        from . import wissen
        img, d = self.neu()
        self.kopf(d)
        nr, von = daten["nr"], daten["von"]
        f_nr = _font("Bold", 40)
        d.text((90, 378), f"{nr}/{von}", font=f_nr, fill=self.f["neben"])
        x0, x1, y = 200, self.W - 90, 398
        d.rounded_rectangle([x0, y, x1, y + 12], radius=6, fill=self.f["flaeche"])
        d.rounded_rectangle([x0, y, x0 + (x1 - x0) * nr / von, y + 12], radius=6, fill=self.f["plus"])
        # Ergebnis-Zahl = letzte Zahl im Satz („Risk 1% ... you still have 90.4%“ -> 90.4%)
        treffer = _re.findall(r"[-−+]?\$?\d[\d,.]*\d%?|[-−+]?\$?\d%?(?:x)?", daten["satz"])
        gross = treffer[-1].rstrip(".,") if treffer else ""
        if not gross and ":" in daten["satz"][:30]:
            gross = daten["satz"].split(":")[0]
        oben = 450
        if gross:
            gr = 130
            while d.textlength(gross, font=_font("Black", gr)) > self.W - 160 and gr > 70:
                gr -= 10
            farbe = self.f["minus"] if gross.startswith(("-", "−")) else (
                self.f["plus"] if any(c.isdigit() for c in gross) else self.f["amber"])
            self.mitte(d, oben, gross, _font("Black", gr), farbe)
            oben += gr + 40
        t = daten.get("thema")
        if t:
            rgba = self.img.convert("RGBA")
            if wissen.video_grafik(rgba, t, self.th, (60, oben, self.W - 60, 1200), daten.get("schritt", nr), self.lang,
                                   daten.get("echt")):
                self.img.paste(rgba.convert("RGB"))
            d = ImageDraw.Draw(self.img)
        self.untertitel(d, text)
        return self.img

    # ---------- Willkommensvideo (S30, Wunsch Tobias 03.11.2026) ----------
    WILLKOMMEN = [("W", "Whale of the day", "Who is buying, who is leaving"),
                  ("!", "Live crypto alerts", "In minutes, not hours"),
                  ("%", "Market in 30 seconds", "Biggest moves, every day"),
                  ("?", "Crypto explained", "Short and clear")]

    def willkommen(self, daten, text):
        """schritt 0: Logo + Leitsatz; 1-4: die vier Formate, das aktuelle leuchtet."""
        img, d = self.neu()
        self.kopf(d)
        s = daten.get("schritt", 0)
        if s == 0:
            self.logo(d, (self.W - 32 * 8) / 2, 430, 8)
            d = ImageDraw.Draw(self.img)
            self.mitte(d, 720, "WhaleSqueeze", _font("Black", 110), self.f["text"])
            self.mitte(d, 860, "Who watches while", _font("Bold", 62), self.f["plus"])   # Frage als Haken
            self.mitte(d, 940, "the market sleeps?", _font("Bold", 62), self.f["plus"])
        else:
            y = 420
            for i, (zeichen, titel, unter) in enumerate(self.WILLKOMMEN, 1):
                an = i == s
                fl = self.f["flaeche"]
                d.rounded_rectangle([70, y, self.W - 70, y + 170], radius=30, fill=fl,
                                    outline=self.f["plus"] if an else self.f["linie"], width=5 if an else 2)
                d.rounded_rectangle([100, y + 35, 200, y + 135], radius=22,
                                    fill=self.f["plus"] if an else self.f["linie"])
                fz = _font("Black", 64)
                d.text((150 - d.textlength(zeichen, font=fz) / 2, y + 42), zeichen, font=fz, fill=self.f["grund"])
                d.text((235, y + 32), titel, font=_font("Bold", 52), fill=self.f["text"] if an else self.f["neben"])
                d.text((235, y + 100), unter, font=_font("Medium", 36), fill=self.f["neben"])
                y += 195
        self.untertitel(d, text)
        return self.img

    def outro(self, daten, text):
        img, d = self.neu()
        self.kopf(d)
        self.logo(d, (self.W - 32 * 7) / 2, 420, 7)
        # Folgen statt Website (Website noch hinter Passwort; „Folgen“ am Ende bringt auf Reels/TikTok Follower)
        self.mitte(d, 690, "@whalesqueeze", _font("Black", 104), self.f["amber"])
        self.mitte(d, 830, self.t["b_folgen"], _font("Bold", 50), self.f["text"])
        cta = daten.get("_cta")
        if cta:   # Kommentar-Frage (04.11.2026) statt Leitsatz
            for i, z in enumerate(textwrap.wrap(cta, width=26)[:3]):
                self.mitte(d, 920 + i * 62, z, _font("Black", 52), self.f["plus"])
            self.mitte(d, 920 + 62 * len(textwrap.wrap(cta, width=26)[:3]) + 24, self.t["b_kommentar"],
                       _font("Bold", 40), self.f["neben"])
        else:
            self.mitte(d, 910, self.t["b_outro"], _font("SemiBold", 42), self.f["neben"])
        konflikt = textwrap.wrap(self.cfg["hinweise"].get("konflikt") or "", width=48)
        for i, z in enumerate(konflikt):
            self.mitte(d, 930 + i * 44, z, _font("Medium", 34), self.f["neben"])
        self.untertitel(d, text)
        return img


def zeichnen(beitrag: dict, zeilen: list[str], ordner: Path, cfg: dict) -> list[Path]:
    import datetime as _dt
    tag = _dt.date.fromtimestamp(beitrag.get("ts") or _dt.datetime.now().timestamp()).isoformat()
    lw = Leinwand(dict(cfg, _thema=design.thema_waehlen("video", f"{tag}:{beitrag.get('format')}")))
    ordner.mkdir(parents=True, exist_ok=True)
    movers = [s for s in beitrag["szenen"] if s["typ"] == "mover"]
    dateien = []
    for i, (s, z) in enumerate(zip(beitrag["szenen"], zeilen)):
        if s["typ"] == "mover":
            img = lw.mover(s["daten"], z, movers.index(s) + 1, len(movers))
        else:
            img = getattr(lw, s["typ"])(s["daten"], z)
        p = ordner / f"bild_{i:02d}.png"
        img.save(p)
        dateien.append(p)
    return dateien
