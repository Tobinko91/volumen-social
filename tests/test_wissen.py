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
            self.assertEqual(len(b["szenen"]), len(t.get("video_punkte") or t["punkte"]) + 2)
            woerter = sum(len(sz["vorlage"].split()) for sz in b["szenen"])
            self.assertLessEqual(woerter, cfg["text"]["max_woerter_wissen"], t["id"])   # 08.11.: 15-18-Sek.-Reels
            self.assertEqual(b["szenen"][0]["typ"], "lern_haken")
            zeilen = [s["vorlage"] for s in b["szenen"]]
            self.assertEqual(_p.pruefen(zeilen, {"fakten": b["fakten"], "szenen": b["szenen"]}, cfg, set()), [], t["id"])


if __name__ == "__main__":
    unittest.main()


class NeueThemenTest(unittest.TestCase):
    """08.11.2026 Tobias: mehr Lern-Reels. Jede Zahl der neuen Themen nachgerechnet."""

    def test_rechnungen(self):
        import math
        self.assertEqual([round(0.999 ** n * 100, 1) for n in (10, 50, 100)], [99.0, 95.1, 90.5])   # Gebuehren
        self.assertEqual([round(100 / (1 + r), 1) for r in (1, 2, 3)], [50.0, 33.3, 25.0])          # Chance/Risiko
        self.assertEqual([round(10 / (s / 100)) for s in (2, 5, 10)], [500, 200, 100])              # Positionsgroesse
        self.assertEqual([round(f * 3 * 365) for f in (0.01, 0.05, 0.1)], [11, 55, 110])            # Funding (einfach)
        self.assertEqual([round(100 * (1 - 1 / (1 + m / 100)), 1) for m in (25, 50, 100)], [20.0, 33.3, 50.0])  # Unlock
        self.assertEqual([round(100 * (1 - 1 / (1 + p / 100)), 1) for p in (50, 100, 200)], [33.3, 50.0, 66.7])  # FOMO
        self.assertAlmostEqual(0.7 * 1 - 0.3 * 3, -0.2)                                              # Trefferquote
        self.assertEqual([round(math.log(2) / math.log(1 + r / 100)) for r in (6, 8, 12)], [12, 9, 6])  # Regel 72
        self.assertEqual([round(1000 / 1.03 ** 10), round(1000 / 1.03 ** 20), round(1000 / 1.05 ** 10)], [744, 554, 614])
        self.assertEqual(sum(2 ** i for i in range(6)), 63)                                          # Verdoppeln

    def test_genug_themen_fuer_zwei_am_tag(self):
        self.assertGreaterEqual(len(wissen.themen()), 23)


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


class HakenFrageTest(unittest.TestCase):
    """04.11.2026: erster Satz im Lern-Video ist eine Frage; Zahlen darin muessen im Thema vorkommen."""
    def test_jedes_thema_hat_frage_mit_geprueften_zahlen(self):
        import re
        import yaml
        from pathlib import Path
        themen = yaml.safe_load((Path(__file__).resolve().parent.parent / "inhalte" / "wissen.yaml").read_text())
        for t in themen:
            self.assertIn("?", t["haken"], t["id"])
            for z in re.findall(r"\d[\d,.]*", t["haken"]):
                self.assertIn(z.rstrip(".,"), t["titel"] + " " + " ".join(t["punkte"]), (t["id"], z))


class SchrittGrafikTest(unittest.TestCase):
    """04.11.2026 Tobias: Grafik baut sich auf, letzter Schritt zeigt die Vervielfachung (Einzahlung vs. Ertrag)."""
    def test_sparplan_passt_zu_den_texten(self):
        from social import wissen
        g, e = wissen.sparplan(155)
        self.assertEqual((round(g[155]), e[155], round(g[155] - e[155])), (50173, 31000, 19173))
        marken = [next(m for m in range(1, 156) if g[m] >= z) for z in (10000, 20000, 30000, 40000, 50000)]
        self.assertEqual(marken, [45, 80, 109, 133, 155])
        self.assertEqual([b - a for a, b in zip([0] + marken, marken)], [45, 35, 29, 24, 22])

    def test_schritte_zeichnen_ohne_fehler(self):
        from PIL import Image
        from social import design, wissen
        th = design.thema_waehlen("markt", "x")
        for t in wissen.themen():
            for s in (None, 1, 2, 3):
                img = Image.new("RGBA", (1080, 1920))
                wissen.video_grafik(img, t, th, (60, 600, 1020, 1200), s if s else 3 if t["id"] in wissen.CHART_ART
                                    else None, "en")
