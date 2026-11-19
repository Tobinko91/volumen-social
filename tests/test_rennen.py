"""Spar-Rennen zweier Aktien (Wunsch Tobias 19.11.2026)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import reel, rennen

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


def kurse(start, faktor, n=40):
    out, p = [], start
    for i in range(n):
        out.append((f"{1999 + i // 12}-{i % 12 + 1:02d}", p))
        p *= faktor
    return out


class RennenTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp()) / "chat_20261119-apple-nvidia-reel"
        self.o.mkdir(parents=True)
        for i in range(2):
            Image.new("RGB", (1080, 1920), (20, 15, 46)).save(self.o / f"szene_{i}.png")
        (self.o / "reel.json").write_text(json.dumps({"thema": "apple-nvidia", "ruhig": True, "untertitel": False,
                                                      "szenen": [
            {"bild": "szene_0.png", "text": "100 dollars a month since {ab_jahr}.",
             "rennen": {"a": {"symbol": "AAPL", "name": "Apple"}, "b": {"symbol": "NVDA", "name": "NVIDIA"},
                        "ab": "1999-01", "monat": 100, "sekunden": 4}},
            {"bild": "szene_1.png", "text": "Invested {investiert}.", "rennen_ende": True}]}))
        self.gesehen = {}

    def tearDown(self):
        shutil.rmtree(self.o.parent)

    def test_sparplan_rechnet_richtig(self):
        w = rennen.sparplan([("1999-01", 10.0), ("1999-02", 20.0)], [("1999-01", 5.0), ("1999-02", 5.0)], 100)
        self.assertEqual(w[-1]["inv"], 200)
        self.assertAlmostEqual(w[-1]["a"], (10 + 5) * 20)      # 10 + 5 Anteile zu 20 $
        self.assertAlmostEqual(w[-1]["b"], 200)                 # gleicher Kurs = eingezahlt
        self.assertEqual(rennen.achse(2_500_000), "$2.5M")
        self.assertEqual(rennen.geld(1234567.8), "$1,234,568")

    def test_reel_mit_rennen(self):
        def sprechen(zeilen, ordner, cfg, key):
            self.gesehen["zeilen"] = zeilen
            return [Path("a.mp3"), Path("b.mp3")], [2.0, 2.0], "elevenlabs"

        def schneiden(bilder, toene, dauern, ziel, cfg, texte=None):
            self.gesehen.update(bilder=bilder, dauern=dauern, texte=texte)
            ziel.write_bytes(b"mp4")

        holen = lambda s, ab: kurse(10, 1.05) if s == "AAPL" else kurse(5, 1.08)
        q = reel.bauen(self.o, CFG, {}, sprechen=sprechen, schneiden=schneiden, rennen_holen=holen)
        self.assertIn("Rennen: $4,000", q)
        self.assertEqual(self.gesehen["zeilen"][0], "100 dollars a month since 1999.")
        self.assertEqual(self.gesehen["zeilen"][1], "Invested $4,000.")   # Zahlen auch fuer spaetere Szenen
        self.assertEqual(self.gesehen["bilder"][1], [(folge_ende := self.gesehen["bilder"][0][-1][0], 0.1)])
        folge = self.gesehen["bilder"][0]
        self.assertEqual(len(folge), 40)
        self.assertAlmostEqual(sum(s for _, s in folge), 4.0)
        self.assertGreaterEqual(self.gesehen["dauern"][0], 5.5)     # Bildfolge laeuft ganz durch
        self.assertEqual(Image.open(folge[-1][0]).size, (1080, 1920))
        self.assertIsNone(self.gesehen["texte"])
        self.assertTrue(folge_ende.exists())

    def test_ohne_kurse_kein_video(self):
        def kaputt(s, ab):
            raise ConnectionError("Yahoo nicht erreichbar")
        with self.assertRaises(RuntimeError):
            reel.bauen(self.o, CFG, {}, sprechen=lambda *a: ([], [], ""), schneiden=lambda *a, **k: None,
                       rennen_holen=kaputt)

    def test_yahoo_antwort_lesen(self):
        class R:
            def json(self):
                return {"chart": {"result": [{"timestamp": [915148800 + i * 2_678_400 for i in range(13)],
                                              "indicators": {"adjclose": [{"adjclose": [1.0 + i for i in range(12)]
                                                                           + [None]}]}}]}}
        k = rennen.monatskurse("AAPL", "1999-01", get=lambda *a, **kw: R())
        self.assertEqual(len(k), 12)
        self.assertEqual(k[0], ("1999-01", 1.0))


if __name__ == "__main__":
    unittest.main()
