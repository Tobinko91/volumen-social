"""Video-Haken und Whale of the day als Video (Wunsch Tobias 01.11.2026)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from social import daten, formate, pruefung, wal

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())


class HakenTest(unittest.TestCase):
    def test_erste_szene_ist_die_groesste_bewegung(self):
        d = daten.laden(HIER / "beispieldaten")
        b = formate.markt_30s(d, set(), "en")
        s0 = b["szenen"][0]
        self.assertEqual(s0["typ"], "haken")
        groesste = max(b["fakten"]["mover"], key=lambda m: abs(m["chg24"]))
        self.assertEqual(s0["daten"]["base"], groesste["base"])
        self.assertTrue(s0["vorlage"].startswith(f"{groesste['base']} jumped"))
        self.assertEqual(b["szenen"][-1]["vorlage"], "Follow WhaleSqueeze for daily crypto data.")
        zeilen = [s["vorlage"] for s in b["szenen"]]
        self.assertEqual(pruefung.pruefen(zeilen, b, CFG, set()), [])
        self.assertNotIn("dot com", " ".join(zeilen))   # Website noch hinter Passwort

    def test_auf_deutsch(self):
        d = daten.laden(HIER / "beispieldaten")
        b = formate.markt_30s(d, set(), "de")
        self.assertIn("in 24 Stunden um", b["szenen"][0]["vorlage"])


class WalVideoTest(unittest.TestCase):
    def test_szenen_und_pruefung(self):
        d = daten.laden(HIER / "beispieldaten")
        w = daten.wal_des_tages(d, set())
        b = wal.video_szenen(w, "en")
        typen = [s["typ"] for s in b["szenen"]]
        self.assertEqual(typen[0], "wal_haken")
        self.assertEqual(typen[-1], "outro")
        zeilen = [s["vorlage"] for s in b["szenen"]]
        self.assertEqual(pruefung.pruefen(zeilen, {"fakten": b["fakten"], "szenen": b["szenen"]}, CFG, set()), [])
        self.assertNotIn("know", " ".join(zeilen).lower())   # keine Andeutung von Insiderwissen

    def test_ohne_verlauf_und_holder(self):
        w = {"base": "ABC", "quelle": "anteil", "wal": 12.5, "boerse": None, "wal_7d": None, "boerse_7d": None,
             "holder": None, "holder_7d": None, "chg24": 1.0, "verlauf": []}
        b = wal.video_szenen(w, "en")
        self.assertEqual([s["typ"] for s in b["szenen"]], ["wal_haken", "outro"])
        self.assertEqual(b["szenen"][0]["vorlage"], "Whales hold 12.5 percent of ABC.")

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg fehlt")
    def test_wal_lauf_baut_bild_und_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, SOCIAL_GEHEIM=tmp)
            r = subprocess.run([sys.executable, "main.py", "wal", "--daten", "beispieldaten", "--out", tmp],
                               cwd=HIER, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(list(Path(tmp).glob("*_wal_*/post.png")))
            v = list(Path(tmp).glob("*_wal_*_video/video.mp4"))
            self.assertTrue(v)
            self.assertTrue((v[0].parent / "post_telegram.txt").exists())
            self.assertFalse((v[0].parent / "post.png").exists())   # ein Vorschlag = ein Medium


if __name__ == "__main__":
    unittest.main()
