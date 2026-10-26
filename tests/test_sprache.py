"""S1: Sprachparameter. Markt und Wal lassen sich auch auf Englisch erzeugen, gesendet wird Englisch nie."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from social import daten, formate, post, pruefung, sprache, wal

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
D = daten.laden(HIER / "beispieldaten")


class SpracheTest(unittest.TestCase):
    def test_gleiche_schluessel_in_allen_sprachen(self):
        for lang in sprache.SPRACHEN:
            self.assertEqual(set(sprache.T[lang]), set(sprache.T["de"]), lang)
            self.assertEqual(set(sprache.TAG[lang]), set(sprache.TAG["de"]), lang)

    def test_markt_englisch(self):
        b = formate.markt_30s(D, set(), "en")
        t = post.markt_texte(b, CFG)
        self.assertIn("Crypto market", t["x"])
        self.assertIn("Not financial advice.", t["x"])
        self.assertNotIn("Größte", t["x"] + t["telegram"])
        self.assertNotIn("Anlageberatung", t["x"] + t["telegram"])
        self.assertLessEqual(len(t["x"]), 280)
        f = pruefung.pruefen([t["x"], t["telegram"]], dict(b, szenen=[0, 0]), CFG, set(), erlaubt_fusszeile=True)
        self.assertEqual(f, [])

    def test_wal_englisch(self):
        w = daten.wal_des_tages(D, set())
        t = wal.texte(w, CFG, "en")
        self.assertIn("Whale of the day", t["x"])
        self.assertTrue(t["x"].endswith("Not financial advice."))
        f = pruefung.pruefen([t["x"], t["telegram"]], {"fakten": wal.fakten(w), "szenen": [0, 0]}, CFG, set(),
                             erlaubt_fusszeile=True)
        self.assertEqual(f, [])

    def test_deutsch_unveraendert(self):
        t = post.markt_texte(formate.markt_30s(D, set(), "de"), CFG)
        self.assertTrue(t["x"].startswith("Krypto-Markt am"))
        self.assertTrue(t["x"].endswith(CFG["hinweise"]["post_text"]))
        self.assertEqual(wal.texte(daten.wal_des_tages(D, set()), CFG)["x"].splitlines()[-1], "Keine Anlageberatung.")

    def test_englisch_wird_nie_gesendet(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, SOCIAL_GEHEIM=tmp)
            for fmt in ("markt", "wal"):
                extra = ["--art", "post"] if fmt == "markt" else []
                r = subprocess.run([sys.executable, "main.py", fmt, "--daten", "beispieldaten", "--sprache", "en",
                                    "--senden", "--out", tmp, *extra], cwd=HIER, capture_output=True, text=True,
                                   env=env)
                self.assertIn("nichts gesendet", r.stdout, r.stderr)
            xs = [p.read_text() for p in Path(tmp).glob("*/post_x.txt")]
            self.assertTrue(any("Crypto market" in x for x in xs))
            self.assertTrue(any("Whale of the day" in x for x in xs))
            tg = next(Path(tmp).glob("*_wal_*/post_telegram.txt")).read_text()
            self.assertIn("whalesqueeze.com/en/coin/", tg)


if __name__ == "__main__":
    unittest.main()
