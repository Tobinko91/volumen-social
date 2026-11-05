"""Video-Haken und Whale of the day als Video (Wunsch Tobias 01.11.2026)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

from social import daten, formate, pruefung, wal

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())


class HakenTest(unittest.TestCase):
    def test_erste_szene_ist_die_groesste_bewegung(self):
        from unittest import mock
        d = daten.laden(HIER / "beispieldaten")
        with mock.patch.object(formate, "haken_art", lambda tag: "zahl"):
            z = formate.markt_30s(d, set(), "en")["szenen"][0]
        self.assertTrue(z["vorlage"].startswith(f"{z['daten']['base']} jumped"))   # A/B: Aussage mit Zahl
        self.assertEqual((z["haken"], z["daten"]["_frage"]), ("zahl", None))
        with mock.patch.object(formate, "haken_art", lambda tag: "frage"):
            b = formate.markt_30s(d, set(), "en")
        s0 = b["szenen"][0]
        self.assertEqual(s0["haken"], "frage")
        self.assertEqual(s0["daten"]["_frage"], f"WHY DID {s0['daten']['base']} JUMP?")
        self.assertEqual(s0["typ"], "haken")
        groesste = max(b["fakten"]["mover"], key=lambda m: abs(m["chg24"]))
        self.assertEqual(s0["daten"]["base"], groesste["base"])
        self.assertTrue(s0["vorlage"].startswith(f"Why did {groesste['base']} jump"))   # Frage als Haken
        self.assertIn("?", s0["vorlage"])
        self.assertEqual(b["szenen"][-1]["vorlage"],
                         "Which coin should we check tomorrow? Comment below. And follow WhaleSqueeze.")
        self.assertEqual(b["szenen"][-1]["daten"]["_cta"], "Which coin should we check tomorrow?")
        zeilen = [s["vorlage"] for s in b["szenen"]]
        self.assertEqual(pruefung.pruefen(zeilen, b, CFG, set()), [])
        self.assertNotIn("dot com", " ".join(zeilen))   # Website noch hinter Passwort
        self.assertNotIn("percent", " ".join(zeilen))   # Wunsch 01.11.: Zeichen statt Wort
        self.assertIn(f"{groesste['chg24']}%", s0["vorlage"])

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
        import datetime as dt
        from social import sprache
        frage_tag = next(dt.date(2026, 11, d) for d in (5, 6) if sprache.haken_art(dt.date(2026, 11, d), True) == "frage")
        with unittest.mock.patch.object(sprache, "haken_test_an", lambda: True):
            b = wal.video_szenen(w, "en", tag=frage_tag)   # fester Frage-Tag, sonst haengt der Test vom Datum ab
        self.assertEqual([s["typ"] for s in b["szenen"]], ["wal_haken", "outro"])
        self.assertEqual(b["szenen"][0]["vorlage"], "What are whales doing with ABC? They hold 12.5% of it.")

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
