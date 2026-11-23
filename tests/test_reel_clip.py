"""Echter Video-Clip in einer Reel-Szene (Wunsch Tobias 23.11.2026)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import reel

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


class ClipTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp())
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=540x960:rate=30:duration=2",
                        str(self.o / "clip.mp4")], check=True)
        Image.new("RGB", (1080, 1920), "black").save(self.o / "s.png")

    def tearDown(self):
        shutil.rmtree(self.o, ignore_errors=True)

    def test_clip_als_bildfolge(self):
        (self.o / "reel.json").write_text(json.dumps({"thema": "t", "szenen": [
            {"bild": "s.png", "clip": "clip.mp4", "text": "He is back."}, {"bild": "s.png", "text": "Ende."}]}))
        g = {}

        def sprechen(zeilen, o, cfg, key):
            return [Path("a.mp3"), Path("b.mp3")], [1.0, 1.0], "test"

        def schneiden(bilder, toene, dauern, ziel, cfg, texte=None):
            g.update(bilder=bilder, dauern=dauern)
        reel.bauen(self.o, CFG, {}, sprechen=sprechen, schneiden=schneiden)
        folge = g["bilder"][0]
        self.assertEqual(len(folge), 30)                      # 2 s bei 15 Bildern/s
        self.assertEqual(Image.open(folge[0][0]).size, (1080, 1920))
        self.assertGreaterEqual(g["dauern"][0], 3.5)          # Clip laeuft ganz durch (2 s + 1,5 s Luft)
        self.assertEqual(g["bilder"][1], self.o / "s.png")


if __name__ == "__main__":
    unittest.main()
