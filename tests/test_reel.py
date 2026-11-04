"""Reel aus dem Redaktions-Chat: Server spricht den Text, zeichnet den echten Chart, schneidet das Video."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from PIL import Image

from social import reel

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


def _kerzen(n=48):
    return [{"t": 1_762_214_400_000 + i * 900_000, "o": 76000 + i * 10, "h": 76100 + i * 10, "l": 75900 + i * 10,
             "c": 76050 + i * 10, "v": 1.0} for i in range(n)]


class ReelTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp()) / "chat_20261104-midterms-3-reel"
        self.o.mkdir(parents=True)
        for i in range(2):
            Image.new("RGB", (1080, 1920), (20, 15, 46)).save(self.o / f"szene_{i}.png")
        (self.o / "reel.json").write_text(json.dumps({"thema": "midterms-3", "szenen": [
            {"bild": "szene_0.png", "text": "Bitcoin dipped.",
             "chart": {"base": "BTC", "intervall": "15m", "anzahl": 48, "box": [60, 700, 1020, 1500]}},
            {"bild": "szene_1.png", "text": "Then it bounced."}]}))
        self.gesehen = {}

    def tearDown(self):
        shutil.rmtree(self.o.parent)

    def _sprechen(self, zeilen, ordner, cfg, key):
        self.gesehen["zeilen"], self.gesehen["key"] = zeilen, key
        return [Path("a.mp3"), Path("b.mp3")], [2.5, 2.5], "elevenlabs"

    def _schneiden(self, bilder, toene, dauern, ziel, cfg):
        self.gesehen["bilder"] = bilder
        ziel.write_bytes(b"mp4")
        return ziel

    def test_chart_stimme_video(self):
        q = reel.bauen(self.o, CFG, {"elevenlabs_api_key": "k"}, kerzen_holen=lambda b, i, n: _kerzen(n),
                       sprechen=self._sprechen, schneiden=self._schneiden)
        self.assertEqual(q, "elevenlabs")
        self.assertEqual(self.gesehen["zeilen"], ["Bitcoin dipped.", "Then it bounced."])
        self.assertEqual(self.gesehen["key"], "k")
        self.assertEqual(self.gesehen["bilder"][0].name, "chart_szene_0.png")   # echter Chart eingezeichnet
        self.assertEqual(self.gesehen["bilder"][1].name, "szene_1.png")
        self.assertEqual(Image.open(self.gesehen["bilder"][0]).size, (1080, 1920))
        self.assertTrue((self.o / "video.mp4").exists())

    def test_ohne_kurse_trotzdem_video(self):
        q = reel.bauen(self.o, CFG, {}, kerzen_holen=lambda b, i, n: [], sprechen=self._sprechen,
                       schneiden=self._schneiden)
        self.assertIn("Chart fehlt", q)
        self.assertEqual(self.gesehen["bilder"][0].name, "szene_0.png")

    def test_eingang_baut_reel_vor_dem_senden(self):
        sys.path.insert(0, str(HIER / "tools"))
        import eingang
        tmp = self.o.parent
        ein = tmp / "eingang" / "20261104-midterms-3-reel"
        shutil.copytree(self.o, ein)
        Image.new("RGB", (1080, 1350)).save(ein / "post.png")
        (ein / "post_x.txt").write_text("X\nNot financial advice.")
        (ein / "post_telegram.txt").write_text("T\n\n<i>Not financial advice.</i>")
        gesendet = []
        with mock.patch.object(eingang, "EINGANG", tmp / "eingang"), mock.patch.object(eingang, "AUSGABE", tmp), \
                mock.patch.object(eingang, "BASIS", tmp), \
                mock.patch.object(reel, "bauen", lambda z, c, g: (z / "video.mp4").write_bytes(b"v") and "elevenlabs"), \
                mock.patch.object(eingang.telegram, "vorschlag_senden",
                                  lambda g, z, h: gesendet.append((z, h, (z / "video.mp4").exists())) or True):
            eingang.main()
        self.assertEqual(len(gesendet), 1)
        self.assertTrue(gesendet[0][2])
        self.assertIn("🎙 Ton: elevenlabs", gesendet[0][1])


if __name__ == "__main__":
    unittest.main()
