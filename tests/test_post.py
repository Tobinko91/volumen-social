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
        self.assertIn("Not financial advice", self.t["x"])
        self.assertIn("Not financial advice", self.t["telegram"])

    def test_ohne_ausloeser_kein_hinweis(self):
        b = formate.markt_30s(D, set())
        for m in b["fakten"]["mover"]:
            m["ausloeser"] = None
        t = post.markt_texte(b, CFG)
        for wort in ("keine klare", "spekulativ", "Futures", "Auslöser", "no clear", "speculative", "Trigger"):
            self.assertNotIn(wort, t["telegram"])
            self.assertNotIn(wort, t["x"])

    def test_kein_mittlerer_coin(self):
        alles = self.t["x"] + self.t["telegram"] + " ".join(s["vorlage"] for s in self.b["szenen"])
        self.assertNotIn("mittlere", alles)
        self.assertNotIn("median coin", alles)
        self.assertIn("Half of", alles)


    def test_telegram_nur_kurzer_hinweis(self):
        from social import wissen
        texte = [self.t["telegram"], wissen.texte(wissen.themen()[0], CFG)["telegram"]]
        for t in texte:
            self.assertIn(CFG["hinweise"]["post_text"], t)
            for weg in ("KI-erstellt", "Totalverlust", "Betreiber"):
                self.assertNotIn(weg, t)


if __name__ == "__main__":
    unittest.main()
