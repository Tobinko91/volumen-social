"""Einheitlicher Schluss jedes Reels (Wunsch Tobias 24.11.2026)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import reel

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


class SchlussTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp())
        Image.new("RGB", (1080, 1920), "black").save(self.o / "s.png")

    def tearDown(self):
        shutil.rmtree(self.o, ignore_errors=True)

    def bauen(self, spec):
        (self.o / "reel.json").write_text(json.dumps(spec))
        g = {}

        def sprechen(zeilen, o, cfg, key):
            g["zeilen"] = zeilen
            return [Path(f"{i}.mp3") for i in range(len(zeilen))], [5.5] * len(zeilen), "test"

        def schneiden(bilder, toene, dauern, ziel, cfg, texte=None):
            g["bilder"] = bilder
        reel.bauen(self.o, CFG, {}, sprechen=sprechen, schneiden=schneiden)
        return g

    def test_schluss_vor_dem_countdown(self):
        g = self.bauen({"thema": "t", "frage": {"name": "$BTC"}, "szenen": [{"bild": "s.png", "text": "News."}]})
        self.assertEqual(g["zeilen"][1], "Follow us for more. Like and comment: where do you think the price goes next?")
        self.assertEqual(Path(g["bilder"][1]).name, "schluss.png")
        self.assertEqual(Image.open(g["bilder"][1]).size, (1080, 1920))
        self.assertIn("What will BTC do", g["zeilen"][2])   # Countdown bleibt ganz am Ende

    def test_eigene_frage_abschalten_und_kein_doppel(self):
        g = self.bauen({"thema": "t", "schluss_frage": "which coin should we check next?",
                        "szenen": [{"bild": "s.png", "text": "News."}]})
        self.assertTrue(g["zeilen"][-1].endswith("which coin should we check next?"))
        g = self.bauen({"thema": "t", "schluss": False, "szenen": [{"bild": "s.png", "text": "News."}]})
        self.assertEqual(len(g["zeilen"]), 1)
        g = self.bauen({"thema": "t", "szenen": [{"bild": "s.png", "text": "Follow us for more. Bye."}]})
        self.assertEqual(len(g["zeilen"]), 1)   # Schluss schon im Text -> nicht doppelt


if __name__ == "__main__":
    unittest.main()
