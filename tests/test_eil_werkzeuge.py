"""Eil-Werkzeuge 13.11.2026: EMA im Chart, echter Kursverlauf im Beitragsbild, Foto-Szene im Reel."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER / "tools"))
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))

from social import reel  # noqa: E402


def kerzen(n, start=80000.0, schritt=-40.0):
    out, p = [], start
    for i in range(n):
        o, c = p, p + schritt
        out.append({"t": (1_760_000_000 + i * 86400) * 1000, "o": o, "h": max(o, c) * 1.01, "l": min(o, c) * 0.99,
                    "c": c, "v": 1})
        p = c
    return out


class EilTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp())
        Image.new("RGB", (1080, 1350), "navy").save(self.o / "post.png")

    def tearDown(self):
        shutil.rmtree(self.o, ignore_errors=True)

    def test_ema(self):
        k = [{"c": float(c)} for c in [1, 2, 3, 4, 5]]
        e = reel.ema(k, 3)
        self.assertEqual(e[:2], [None, None])
        self.assertAlmostEqual(e[2], 2.0)
        self.assertAlmostEqual(e[3], 3.0)
        self.assertEqual(reel.ema(k, 10), [None] * 5)

    def test_chart_mit_ema(self):
        geholt = {}

        def holen(b, i, n):
            geholt.update(b=b, i=i, n=n)
            return kerzen(n)

        p, w = reel.chart_szene(self.o, {"bild": "post.png", "chart": {
            "base": "BTC", "intervall": "1d", "anzahl": 60, "ema": 200, "box": [60, 300, 1020, 1100],
            "titel": "BTC · daily"}}, "t", holen)
        self.assertEqual(geholt, {"b": "BTC", "i": "1d", "n": 860})   # 4 x 200 Kerzen Vorlauf fuer die EMA
        self.assertTrue(p.exists())
        for key in ("chg", "ema", "ema_abstand", "ema_lage", "hoch", "vom_hoch"):
            self.assertIn(key, w)
        self.assertEqual(w["ema_lage"], "below")    # fallender Verlauf liegt unter der EMA

    def test_ema_ohne_altlast(self):
        """Fehler 13.11.2026: Startwert aus alten, hoeheren Kursen zog die EMA 200 nach oben (75k statt 68k)."""
        hoch = [{"t": i, "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "v": 1} for i in range(1500)]
        tief = [{"t": 1500 + i, "o": 60.0, "h": 61.0, "l": 59.0, "c": 60.0, "v": 1} for i in range(150)]
        k = hoch + tief
        ref = reel.ema(k, 200)[-1]   # EMA ueber die ganze Geschichte (wie TradingView)
        p, w = reel.chart_szene(self.o, {"bild": "post.png", "chart": {
            "base": "BTC", "intervall": "1d", "anzahl": 60, "ema": 200, "box": [60, 300, 1020, 1100]}}, "t",
            lambda b, i, n: k[-n:])
        self.assertAlmostEqual(float(w["ema"].strip("$").replace(",", "")), ref, delta=ref * 0.002)
        with self.assertRaises(ValueError):    # zu wenig Vorlauf -> lieber kein Wert als ein falscher
            reel.chart_szene(self.o, {"bild": "post.png", "chart": {
                "base": "BTC", "intervall": "1d", "anzahl": 60, "ema": 200, "box": [60, 300, 1020, 1100]}}, "t",
                lambda b, i, n: k[-300:])

    def test_rsi_wie_wilder(self):
        k = [{"c": float(c)} for c in [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89,
                                         46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64]]
        r = reel.rsi(k, 14)
        self.assertIsNone(r[13])
        self.assertAlmostEqual(r[14], 70.46, delta=0.1)   # Lehrbuch-Beispiel (Wilder/StockCharts)
        self.assertAlmostEqual(r[15], 66.25, delta=0.1)

    def test_200_wochen_linie_und_rsi_im_chart(self):
        """13.11.2026 Tobias: die ~68.000 sind die 200-Wochen-Linie; RSI unten ins Bild."""
        tag = kerzen(1000, 90000, -20)
        woche = [{"t": i, "o": 68000.0, "h": 69000.0, "l": 67000.0, "c": 68000.0, "v": 1} for i in range(200)]
        geholt = []

        def holen(b, i, n):
            geholt.append((i, n))
            return (woche if i == "1w" else tag)[-n:]

        p, w = reel.chart_szene(self.o, {"bild": "post.png", "chart": {
            "base": "BTC", "intervall": "1d", "anzahl": 90, "ema": 200, "wochen_ma": 200, "rsi": 14,
            "box": [40, 300, 1040, 1250]}}, "t", holen)
        self.assertIn(("1w", 200), geholt)
        self.assertEqual(w["wma"], "$68,000")
        self.assertIn(w["wma_lage"], ("above", "below"))
        self.assertTrue(0 <= float(w["rsi"]) <= 100)
        # zu wenige Wochen -> keine Linie, kein Platzhalter (lieber nichts als falsch)
        p, w = reel.chart_szene(self.o, {"bild": "post.png", "chart": {
            "base": "BTC", "intervall": "1d", "anzahl": 90, "wochen_ma": 200, "box": [40, 300, 1040, 1250]}}, "t",
            lambda b, i, n: (woche[:150] if i == "1w" else tag)[-n:])
        self.assertNotIn("wma", w)

    def test_lange_reihen_von_binance(self):
        from social import kurse
        bitunix = [{"time": (1000 + i) * 1000, "open": 1, "high": 1, "low": 1, "close": 1, "quoteVol": 1}
                   for i in range(150)]
        binance = [[(i) * 1000, "2", "2", "2", "2", "0", 0, "1"] for i in range(200)]

        def get(url, p):
            return {"data": bitunix if not p.get("endTime") else []} if url == kurse.BITUNIX else binance

        self.assertEqual(len(kurse.kerzen("BTC", "1w", 200, get=get, voll=True)), 200)   # Binance reicht weiter
        self.assertEqual(len(kurse.kerzen("BTC", "1w", 200, get=get)), 150)              # sonst wie bisher Bitunix

    def test_post_chart_setzt_zahlen_ein_oder_faellt_zurueck(self):
        import eingang
        (self.o / "post_chart.json").write_text(json.dumps({"chart": {
            "base": "BTC", "intervall": "1d", "anzahl": 60, "ema": 200, "box": [60, 300, 1020, 1100]}}))
        (self.o / "post_x.txt").write_text("BTC {chg} in 60 days. 200-day EMA at {ema}.\\nNot financial advice.")
        (self.o / "post_x_ohne.txt").write_text("BTC under pressure.\\nNot financial advice.")
        h = eingang.post_chart(self.o, lambda b, i, n: kerzen(n))
        self.assertIn("Echter Kursverlauf", h)
        x = (self.o / "post_x.txt").read_text()
        self.assertNotIn("{", x)
        self.assertIn("200-day EMA at $", x)
        # ohne Kurse: Text ohne Zahlen
        (self.o / "post_x.txt").write_text("BTC {chg}")
        h = eingang.post_chart(self.o, lambda b, i, n: [])
        self.assertIn("nicht gezeichnet", h)
        self.assertEqual((self.o / "post_x.txt").read_text(), "BTC under pressure.\\nNot financial advice.")

    def test_foto_szene_laedt_nach(self):
        from social import fotos
        fd = self.o / "fotos"

        def holen(ziel, personen):
            (ziel / "huang").mkdir(parents=True)
            Image.new("RGB", (1600, 2000), "gray").save(ziel / "huang" / "1.jpg")
            (ziel / "fotos.json").write_text(json.dumps({"huang": [{
                "datei": "huang/1.jpg", "lizenz": "CC BY 2.0", "credit": "Test, CC BY 2.0", "seite": "", "titel": "",
                "name": "Jensen Huang"}]}))

        orig = fotos.holen
        fotos.holen = holen
        try:
            p = reel.foto_szene(self.o, {"bild": "szene_0.png", "foto": {
                "person": "huang", "kopf": "Nvidia employees want Huang back", "unter": "1,600+ comments"}}, CFG, fd)
        finally:
            fotos.holen = orig
        self.assertEqual(Image.open(p).size, (1080, 1920))
        with self.assertRaises(ValueError):   # unbekannte Person -> kein Foto, Reel nimmt das Chat-Bild
            reel.foto_szene(self.o, {"bild": "x.png", "foto": {"person": "niemand"}}, CFG, fd)

    def test_personen_und_youtube_in_alle(self):
        p = yaml.safe_load((HIER / "inhalte" / "personen.yaml").read_text())
        self.assertIn("huang", {x["slug"] for x in p})
        self.assertTrue(CFG["youtube"]["in_alle"])


if __name__ == "__main__":
    unittest.main()
