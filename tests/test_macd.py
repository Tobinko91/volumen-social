"""MACD im Reel-Chart (Wunsch Tobias 27.11.2026: echter Monats-MACD statt Schema)."""
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from social import reel


def kerzen(preise):
    return [{"t": (1_500_000_000 + i * 2_600_000) * 1000, "o": p, "h": p * 1.02, "l": p * 0.98, "c": p, "v": 1}
            for i, p in enumerate(preise)]


class MacdTest(unittest.TestCase):
    def test_rechnung(self):
        m, s, h = reel.macd(kerzen([100.0] * 60))
        self.assertAlmostEqual(m[-1], 0.0)
        self.assertAlmostEqual(h[-1], 0.0)
        self.assertIsNone(m[10])                      # vor 26 Kerzen kein Wert
        m, s, h = reel.macd(kerzen([100 + i for i in range(60)]))
        self.assertGreater(m[-1], 0)                  # steigender Kurs -> MACD ueber 0
        m, s, h = reel.macd(kerzen([100 + i for i in range(40)] + [140 - 3 * i for i in range(20)]))
        self.assertLess(h[-1], 0)                     # Drehung nach unten -> Histogramm rot
        self.assertEqual(reel.macd(kerzen([1.0] * 10)), ([None] * 10, [None] * 10, [None] * 10))

    def test_chart_mit_macd(self):
        o = Path(tempfile.mkdtemp())
        try:
            Image.new("RGB", (1080, 1920), "black").save(o / "s.png")
            k = kerzen([100 + i for i in range(60)] + [160 - 2 * i for i in range(40)])
            s = {"bild": "s.png", "chart": {"base": "BTC", "intervall": "1M", "anzahl": 72, "macd": True, "rsi": 14,
                                            "box": [40, 470, 1040, 1560], "titel": "BTC · monthly"}}
            p, w = reel.chart_szene(o, s, "t", lambda b, i, n: k[-n:])
            self.assertTrue(Path(p).exists())
            self.assertEqual(w["macd_lage"], "below")
            self.assertIn(w["macd_trend"], ("rising", "falling"))
        finally:
            shutil.rmtree(o, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
