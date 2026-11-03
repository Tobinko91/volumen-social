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


class LernVideoTest(unittest.TestCase):
    """S28: jedes Lern-Thema als Video – gleiche Saetze, Zahlen-Pruefung bestanden, eine Szene je Punkt."""

    def test_alle_themen_als_video(self):
        import yaml as _y
        from social import pruefung as _p
        cfg = _y.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
        for t in wissen.themen():
            b = wissen.video_szenen(t, "en")
            self.assertEqual(len(b["szenen"]), len(t["punkte"]) + 2)
            self.assertEqual(b["szenen"][0]["typ"], "lern_haken")
            zeilen = [s["vorlage"] for s in b["szenen"]]
            self.assertEqual(_p.pruefen(zeilen, {"fakten": b["fakten"], "szenen": b["szenen"]}, cfg, set()), [], t["id"])


if __name__ == "__main__":
    unittest.main()


class LernGrafikTest(unittest.TestCase):
    """Wunsch Tobias 03.11.2026: Erklaervideos immer mit Grafik; Chart-Themen bauen ein Kerzen-Schema Schritt fuer Schritt."""

    def test_jedes_thema_hat_grafik_in_jeder_szene(self):
        from social import design
        img0 = design.hintergrund(design.THEMEN["nacht"], 1080, 700).convert("RGBA")
        for t in wissen.themen():
            for schritt in (1, 2, 3):
                img = img0.copy()
                self.assertTrue(wissen.video_grafik(img, t, design.THEMEN["nacht"], (60, 40, 1020, 660), schritt), t["id"])
                self.assertNotEqual(img.tobytes(), img0.tobytes(), t["id"])

    def test_liquiditaet_baut_sich_auf(self):
        from social import design, grafik
        th = design.THEMEN["nacht"]
        bilder = []
        for schritt in (1, 2, 3):
            img = design.hintergrund(th, 1080, 700).convert("RGBA")
            grafik.lern_chart(img, th, (60, 40, 1020, 660), "liquiditaet", schritt)
            bilder.append(img.tobytes())
        self.assertEqual(len(set(bilder)), 3)
