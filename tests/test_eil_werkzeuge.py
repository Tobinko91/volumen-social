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
