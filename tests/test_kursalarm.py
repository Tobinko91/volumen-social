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
