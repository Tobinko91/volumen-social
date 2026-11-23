"""Aktien-/Index-Chart im Reel (Wunsch Tobias 23.11.2026: Nvidia-Chart seit der Meldung)."""
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from social import kurse, reel


class AktienChartTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp())
        Image.new("RGB", (1080, 1920), (20, 15, 46)).save(self.o / "s.png")

    def tearDown(self):
        shutil.rmtree(self.o, ignore_errors=True)

    def test_yahoo_lesen(self):
        ts = [1_800_000_000 + i * 900 for i in range(5)]
        j = {"chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{
            "open": [1, 2, None, 4, 5], "high": [2, 3, 3, 5, 6], "low": [0.5, 1, 2, 3, 4],
            "close": [2, 3, 3, 5, 6], "volume": [10, 20, 30, 40, 50]}]}}]}}
        gesehen = {}

        def get(url, p):
            gesehen.update(url=url, p=p)
            return j
        k = kurse.aktien_kerzen("nvda", "15m", 3, get=get)
        self.assertIn("/NVDA", gesehen["url"])
        self.assertEqual(gesehen["p"]["includePrePost"], "true")
        self.assertEqual([x["c"] for x in k], [3.0, 5.0, 6.0])   # Luecke (None) uebersprungen, letzte 3
        self.assertEqual(k[0]["t"], ts[1] * 1000)

    def test_chart_szene_mit_aktie(self):
        k = [{"t": (1_800_000_000 + i * 900) * 1000, "o": 100 + i, "h": 101 + i, "l": 99 + i, "c": 101 + i, "v": 1}
             for i in range(30)]
        s = {"bild": "s.png", "chart": {"base": "NVDA", "quelle": "aktie", "intervall": "15m", "anzahl": 30,
                                        "titel": "NVDA · 15m", "box": [60, 560, 1020, 1500]}}
        fremd = lambda *a: self.fail("Krypto-Kurse duerfen fuer eine Aktie nicht geholt werden")
        p, w = reel.chart_szene(self.o, s, "t", fremd, aktien_holen=lambda b, i, n: k)
        self.assertTrue(Path(p).exists())
        self.assertEqual(w["chg"], f"{(130 / 100 - 1) * 100:+.1f}%")


if __name__ == "__main__":
    unittest.main()
