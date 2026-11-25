"""Kurs-Alarm (Wunsch Tobias 05.11.2026): BTC/ETH +-4 % in 60 Minuten -> Eilmeldung."""
import json
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import kursalarm

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


def _k(ende_chg=-5.0, n=100):
    k = [{"t": (1_793_890_800 + i * 900) * 1000, "o": 80000, "h": 80100, "l": 79900, "c": 80000, "v": 1}
         for i in range(n)]
    k[-1]["c"] = 80000 * (1 + ende_chg / 100)
    return k


class KursAlarmTest(unittest.TestCase):
    def test_schwelle_und_sperre(self):
        stand = {}
        a = kursalarm.pruefen(lambda b, i, n: _k(-5.0), stand, jetzt=1000)
        self.assertEqual([x["base"] for x in a], ["BTC", "ETH"])
        self.assertAlmostEqual(a[0]["chg1h"], -5.0)
        self.assertEqual(kursalarm.pruefen(lambda b, i, n: _k(-5.0), stand, jetzt=2000), [])   # 3 Std. Sperre
        self.assertEqual(kursalarm.pruefen(lambda b, i, n: _k(-3.0), {}, jetzt=1000), [])     # unter 4 %
        self.assertEqual(kursalarm.pruefen(lambda b, i, n: [], {}, jetzt=1000), [])

    def test_bauen(self):
        a = kursalarm.pruefen(lambda b, i, n: _k(-5.0), {}, jetzt=1000)
        with tempfile.TemporaryDirectory() as d:
            bo, ro = kursalarm.bauen(a, Path(d), CFG, jetzt=1_793_895_000)
            self.assertEqual(Image.open(bo / "post.png").size, (1080, 1350))
            self.assertLessEqual(len((bo / "post_x.txt").read_text()), 280)
            self.assertIn("BTC drops 5.0% in one hour", (bo / "post_telegram.txt").read_text())
            r = json.loads((ro / "reel.json").read_text())
            self.assertIn("{chg}", r["szenen"][1]["text"])
            self.assertTrue(r["szenen"][1]["chart"]["ab_ts"])
            self.assertTrue(ro.name.endswith("_video"))


if __name__ == "__main__":
    unittest.main()


class MarkenTest(unittest.TestCase):
    """25.11.2026 Tobias: „Bitcoin falls below $57,500“ als Eilmeldung, auch ohne 4 % in einer Stunde."""

    def test_marke_gekreuzt(self):
        self.assertEqual(kursalarm.marke_gekreuzt("BTC", 58_100, 57_400), 57_500)
        self.assertEqual(kursalarm.marke_gekreuzt("BTC", 57_400, 60_100), 60_000)   # mehrere Marken: die letzte
        self.assertIsNone(kursalarm.marke_gekreuzt("BTC", 58_100, 57_600))
        self.assertIsNone(kursalarm.marke_gekreuzt("BTC", None, 57_400))
        self.assertEqual(kursalarm.marke_gekreuzt("ETH", 1_650, 1_590), 1_600)
        self.assertIsNone(kursalarm.marke_gekreuzt("SOL", 150, 140))

    def test_alarm_und_reel(self):
        def kerzen(preis):
            return lambda b, i, n: [dict(x, c=preis if b == "BTC" else 2000, o=preis if b == "BTC" else 2000)
                                    for x in _k(0.0)]
        stand = {}
        self.assertEqual(kursalarm.pruefen(kerzen(58_100), stand, jetzt=1000), [])   # erster Lauf merkt den Preis
        a = kursalarm.pruefen(kerzen(57_400), stand, jetzt=1600)
        self.assertEqual([(x["base"], x["marke"], x["runter"]) for x in a], [("BTC", 57_500, True)])
        self.assertEqual(kursalarm.pruefen(kerzen(57_600), stand, jetzt=2200), [])
        self.assertEqual(kursalarm.pruefen(kerzen(57_400), stand, jetzt=2800), [])   # gleiche Marke: 3 Std. Sperre
        with tempfile.TemporaryDirectory() as d:
            bo, ro = kursalarm.bauen(a, Path(d), CFG, jetzt=1_793_895_000)
            self.assertIn("BTC falls below $57,500", (bo / "post_telegram.txt").read_text())
            r = json.loads((ro / "reel.json").read_text())
            self.assertTrue(r["szenen"][0]["text"].startswith("Breaking: BTC falls below $57,500."))
