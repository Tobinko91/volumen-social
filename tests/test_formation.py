"""S27 Formation des Tages (Wunsch Tobias 09.11.2026)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import formation

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


class FormationTest(unittest.TestCase):
    def setUp(self):
        self.d = formation.laden(HIER / "beispieldaten")

    def test_texte_ehrlich(self):
        tx = formation.texte(self.d)
        self.assertEqual(len(tx["zeilen"]), 6)
        self.assertIn("−8.7%", tx["zeilen"][3])
        self.assertIn("The textbook was right.", tx["zeilen"][3])
        self.assertIn("58%", tx["zeilen"][4])
        self.assertIn("Without any pattern: 61%", tx["zeilen"][4])
        self.assertIn("No real edge.", tx["zeilen"][4])        # 58 % gegen Zufall 61 %
        self.assertLessEqual(len(tx["x"]), 280)
        self.assertTrue(tx["x"].endswith("Not financial advice."))
        for z in tx["zeilen"]:
            self.assertNotIn("(", z)
            for w in ("buy now", "sell now", "target", "guarant"):
                self.assertNotIn(w, z.lower())

    def test_ohne_statistik_faellt_nur_der_haken_weg(self):
        d = dict(self.d, statistik=None)
        self.assertEqual(len(formation.texte(d)["zeilen"]), 5)
        d2 = dict(self.d, ergebnis=dict(self.d["ergebnis"], r6=5.1, lehrbuch_stimmt=False))
        tx = formation.texte(d2)
        self.assertEqual(tx["titel_erg"], "The textbook was wrong")
        self.assertIn("+5.1%", tx["zeilen"][3])

    def test_unvollstaendige_daten(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "muster_des_tages.json").write_text(json.dumps(dict(self.d, kerzen_nachher=[[1, 1, 1, 1, 1]])))
            self.assertIsNone(formation.laden(t))
            self.assertIsNone(formation.laden(Path(t) / "fehlt"))

    def test_szenen_und_video(self):
        o = Path(tempfile.mkdtemp())
        try:
            folgen, tx = formation.szenen(self.d, o / "b")
            self.assertEqual([len(f) for f in folgen], [1, 5, 6, 1, 1, 1])     # Intro, Countdown 5..1, 6 Kerzen, ...
            self.assertEqual(Image.open(folgen[1][0][0]).size, (1080, 1920))
            self.assertAlmostEqual(sum(s for _, s in folgen[1]), 5.0)

            def sprechen(zeilen, ordner, cfg, key):
                ordner.mkdir(parents=True, exist_ok=True)
                toene = []
                for i, _ in enumerate(zeilen):
                    p = ordner / f"z{i}.mp3"
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                                    "-t", "1", "-c:a", "libmp3lame", str(p)], check=True)
                    toene.append(p)
                return toene, [1.0] * len(zeilen), "probe"
            v, q, _ = formation.video(self.d, o, CFG, {}, sprechen=sprechen)
            dauer = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                          "csv=p=0", str(v)], capture_output=True, text=True).stdout)
            self.assertGreater(dauer, 18)          # Countdown + Aufloesung haben Mindestdauern
            self.assertTrue((o / "ton" / "countdown_tick.mp3").exists())
        finally:
            shutil.rmtree(o)

    def test_format_name(self):
        from social import bericht
        self.assertEqual(bericht.format_aus_ordner("20261109-2130_formation_ZK_video"), "formation_video")
        self.assertIn("formation_video", bericht.NAMEN)
