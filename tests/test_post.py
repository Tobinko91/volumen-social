import unittest
from pathlib import Path

import yaml

from social import daten, formate, post, pruefung

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
D = daten.laden(HIER / "beispieldaten")


class PostTest(unittest.TestCase):
    def setUp(self):
        self.b = formate.markt_30s(D, set())
        self.t = post.markt_texte(self.b, CFG)

    def test_x_hoechstens_280_zeichen(self):
        self.assertLessEqual(len(self.t["x"]), 280)

    def test_post_besteht_pruefung(self):
        f = pruefung.pruefen([self.t["x"], self.t["telegram"]], dict(self.b, szenen=[0, 0]), CFG, set(),
                             erlaubt_fusszeile=True)
        self.assertEqual(f, [])

    def test_risiko_hinweis_steht_drin(self):
        self.assertIn("Keine Anlageberatung", self.t["x"])
        self.assertIn("Keine Anlageberatung", self.t["telegram"])


if __name__ == "__main__":
    unittest.main()
