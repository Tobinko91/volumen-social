"""S23 Signal Lab (Wunsch Tobias 04.11.2026): ehrlich, auch Verlierer."""
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import signallab as S

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


class SignalLabTest(unittest.TestCase):
    def setUp(self):
        self.d = S.laden(HIER / "beispieldaten")

    def test_texte(self):
        tx = S.texte(self.d, CFG, 1794300000)
        self.assertLessEqual(len(tx["x"]), 280)
        self.assertTrue(tx["x"].endswith("Not financial advice."))
        self.assertIn("❌ Pump Fade −0.31R", tx["x"])                  # Verlierer bleiben drin
        self.assertIn("No winner yet", " ".join(tx["satz"]))            # vor dem 17.11. kein Gewinner
        self.assertIn("Event Short lost to random this week", tx["telegram"])
        self.assertNotIn("winner:", tx["x"].lower())
        self.assertIn("Virtual trades, fees included.", tx["x"])
        nach = S.texte(self.d, CFG, self.d["urteil_ab"] + 1)
        self.assertNotIn("No winner yet", " ".join(nach["satz"]))

    def test_bild_und_woche(self):
        self.assertEqual(S.woche_nr(self.d, self.d["start"] + 8 * 86400), 2)
        with tempfile.TemporaryDirectory() as t:
            p = S.bild(self.d, CFG, Path(t) / "p.png", 1794300000)
            self.assertEqual(Image.open(p).size, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
