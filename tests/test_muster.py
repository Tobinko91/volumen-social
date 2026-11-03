"""Echte Charts in Lern-Videos (Wunsch Tobias 03.11.2026): Muster finden, ehrlich bleiben, sonst Illustration."""
import random
import unittest

from social import muster, wissen


def kerzen_aus(pfad, docht=None):
    k, vorher = [], pfad[0]
    for i, c in enumerate(pfad):
        o = vorher
        k.append({"t": 1_762_000_000_000 + i * 14_400_000, "o": o, "h": max(o, c) * 1.003, "l": min(o, c) * 0.997,
                  "c": c, "v": 1})
        vorher = c
    if docht:
        i, tief = docht
        k[i]["l"] = tief
    return k


def liqui_kerzen():
    random.seed(4)
    pfad = [100_000 + random.uniform(-300, 300) for _ in range(10)]
    pfad += [99_000, 97_500, 96_000, 97_000, 98_500, 99_500, 99_000, 98_200, 97_800, 97_400, 97_600, 98_000, 97_200,
             97_100, 97_300, 97_000, 97_200, 99_000, 100_500, 101_500, 102_000]
    pfad += [102_000 + random.uniform(-400, 400) for _ in range(20)]
    # Tief bei Index 12 (96.000 Schluss), Docht bei Index 25 bis 95.200, Schluss 97.000 darueber, dann Anstieg
    return kerzen_aus(pfad, docht=(25, 95_200))


class MusterTest(unittest.TestCase):
    def test_liquiditaet_gefunden(self):
        k = liqui_kerzen()
        m = muster.liquiditaet(k)
        self.assertIsNotNone(m)
        self.assertEqual(m["docht_index"], 25)
        self.assertLess(m["docht"], m["tief"])
        self.assertGreater(k[25]["c"], m["tief"])

    def test_kein_muster_kein_echter_chart(self):
        k = kerzen_aus([100_000 + i * 200 for i in range(60)])   # nur Anstieg
        self.assertIsNone(muster.liquiditaet(k))
        t = next(t for t in wissen.themen() if t["id"] == "liquiditaetszone")
        self.assertIsNone(wissen.echter_chart(t, kerzen_holen=lambda *a: k))
        self.assertIsNone(wissen.echter_chart(t, kerzen_holen=lambda *a: []))   # Boerse nicht erreichbar

    def test_pump_nie_echt(self):
        t = next(t for t in wissen.themen() if t["id"] == "pump-and-dump")
        self.assertIsNone(wissen.echter_chart(t, kerzen_holen=lambda *a: liqui_kerzen()))

    def test_unterstuetzung_und_bruch(self):
        pfad = [100, 102, 105, 108, 105, 102, 100.2, 102, 105, 108.3, 105, 102, 100.1, 102, 105, 108.1, 104, 101, 98,
                95, 94]
        pfad = [p * 1000 for p in pfad] + [94_000 + i * 50 for i in range(30)]
        k = kerzen_aus([pfad[0]] * 4 + pfad)
        m = muster.unterstuetzung(k)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(len(m["support"]["beruehrungen"]), 2)
        self.assertIsNotNone(m["bruch_index"])

    def test_echter_chart_zeichnen(self):
        from social import design
        t = next(t for t in wissen.themen() if t["id"] == "liquiditaetszone")
        echt = wissen.echter_chart(t, kerzen_holen=lambda *a: liqui_kerzen())
        self.assertEqual(echt["titel"], "BTC · 4h")
        th = design.THEMEN["nacht"]
        bilder = []
        for schritt in (1, 2, 3):
            img = design.hintergrund(th, 1080, 700).convert("RGBA")
            self.assertTrue(wissen.video_grafik(img, t, th, (60, 40, 1020, 660), schritt, "en", echt))
            bilder.append(img.tobytes())
        self.assertEqual(len(set(bilder)), 3)


    def test_bild_beitrag_mit_echtem_chart(self):
        import tempfile
        from pathlib import Path
        import yaml
        cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
        t = next(t for t in wissen.themen() if t["id"] == "liquiditaetszone")
        echt = wissen.echter_chart(t, kerzen_holen=lambda *a: liqui_kerzen())
        with tempfile.TemporaryDirectory() as d:
            a = wissen.bild(t, cfg, Path(d) / "a.png", "2026-11-03")
            b = wissen.bild(t, cfg, Path(d) / "b.png", "2026-11-03", echt=echt)
            self.assertNotEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
