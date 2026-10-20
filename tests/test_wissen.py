import unittest
from pathlib import Path

import yaml

from social import pruefung, wissen

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())


def monate_bis(ziel, rate=200.0, rendite=0.07):
    k, m = 0.0, 0
    while k < ziel:
        m += 1
        k = k * (1 + rendite / 12) + rate
    return m


class WissenTest(unittest.TestCase):
    def test_alle_themen_bestehen_pruefung(self):
        for t in wissen.themen():
            txt = wissen.texte(t, CFG)
            f = pruefung.pruefen([txt["x"], txt["telegram"]], {"fakten": t["fakten"], "szenen": [0, 0]},
                                 CFG, set(), erlaubt_fusszeile=True)
            self.assertEqual(f, [], t["id"])

    def test_x_texte_hoechstens_280(self):
        for t in wissen.themen():
            self.assertLessEqual(len(t["x"]), 280, t["id"])

    def test_rechnungen_stimmen(self):
        self.assertAlmostEqual(0.99 ** 10 * 100, 90.4, places=1)
        self.assertAlmostEqual(0.95 ** 10 * 100, 59.9, places=1)
        self.assertAlmostEqual(monate_bis(100000, rendite=0.0) / 12, 41.7, places=1)
        self.assertAlmostEqual(monate_bis(100000, rendite=0.05) / 12, 22.6, places=1)
        self.assertAlmostEqual(monate_bis(100000, rendite=0.07) / 12, 19.6, places=1)
        self.assertEqual(monate_bis(10000), 45)
        self.assertEqual(monate_bis(20000) - monate_bis(10000), 35)
        self.assertEqual(round(100 * 1.08 ** 30), 1006)
        self.assertEqual(round(100 / (1 - 0.5) - 100), 100)
        self.assertEqual(round(100 / (1 - 0.9) - 100), 900)

    def test_rotation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            s = Path(d) / "stand.json"
            a = wissen.naechstes(s)
            wissen.merken(s, a["id"], 1)
            self.assertNotEqual(wissen.naechstes(s)["id"], a["id"])


if __name__ == "__main__":
    unittest.main()
