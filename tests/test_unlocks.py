"""S22 Unlock-Posts + S26 Nachfolge-Reels (Wunsch Tobias 03./06.11.2026)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from PIL import Image

from social import unlocks as U

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
T = 1794402000 + 26 * 3600   # 12.11.2026, 15:00 deutsche Zeit


class UnlockTest(unittest.TestCase):
    def setUp(self):
        self.e = U.laden(HIER / "beispieldaten")
        self.allo, self.zro = self.e

    def test_geschichte_und_regeln(self):
        g = U.geschichte(self.allo)
        self.assertEqual((g["n"], g["gefallen"], g["median7"], g["vor_hoch"]), (4, 4, -4, 2))
        self.assertEqual(U.kandidat(self.allo), "muster")
        self.assertEqual(U.kandidat(self.zro), "kurz")          # gross (8.5 %), keine fruehere Geschichte
        self.assertIsNone(U.kandidat(dict(self.zro, pct=1, groesse_vergleich=1)))

    def test_text_ehrlich(self):
        tx = U.texte(self.allo, CFG)
        self.assertIn("In 4 of the last 4 ALLO unlocks, price fell in the 7 days after, median −4.0%.", tx["x"])
        self.assertIn("Only 4 cases, no rule.", tx["telegram"])
        self.assertLessEqual(len(tx["x"]), 280)
        self.assertEqual(tx["x"].count("$"), 1)
        for w in ("will dump", "will pump", "sell now", "buy now", "nox"):
            self.assertNotIn(w, (tx["x"] + tx["telegram"]).lower())
        for z in tx["sprech"]:
            self.assertNotIn("(", z)

    def test_nachfolge_sagt_auch_wenn_es_anders_kam(self):
        e = dict(self.allo, nachher=dict(self.allo["nachher"], tag1=4.2))
        self.assertIn("History didn't repeat this time.", " ".join(U.nachfolge_texte(e, CFG)["sprech"]))
        self.assertIn("This time it did too.", " ".join(U.nachfolge_texte(self.allo, CFG)["sprech"]))

    def test_auswahl(self):
        stand = {}
        a = U.auswahl(self.e, stand, T, set(), ["ALLO"])
        self.assertEqual([(x, e["base"]) for x, e in a], [("tag1", "ALLO"), ("post", "ZRO")])
        for x, e in a:
            U.merken(stand, x, e)
        self.assertEqual(U.auswahl(self.e, stand, T + 600, set(), ["ALLO"]), [])     # nie doppelt
        self.assertEqual(U.auswahl(self.e, {}, T, set(), []), [("post", self.zro)])   # ohne ersten Post kein Nachfolger
        tag7 = dict(self.allo, folge="tag7", nachher=dict(self.allo["nachher"], tag7=-4))
        st = {"gepostet": {U.schluessel(self.allo): ["post"]}}
        self.assertEqual(U.auswahl([tag7], st, T, set()), [])                          # tag7 ohne tag1, kleine Bewegung
        tag7["nachher"]["tag7"] = -15
        self.assertEqual(len(U.auswahl([tag7], st, T, set())), 1)                      # grosse Bewegung: doch
        self.assertEqual(U.auswahl(self.e, {}, T - 15 * 3600, set(), ["ALLO"]), [])   # Ruhezeit (00:00)
        self.assertEqual(U.auswahl(self.e, {}, T, {"ZRO", "ALLO"}, ["ALLO"]), [])     # Sperrliste

    def test_werkzeug_bilder(self):
        sys.path.insert(0, str(HIER / "tools"))
        import unlock_post
        d = Path(tempfile.mkdtemp())
        try:
            gesendet = []
            with mock.patch.object(unlock_post, "AUSGABE", d), mock.patch.object(unlock_post, "BASIS", d), \
                    mock.patch.dict("os.environ", {"SOCIAL_DATEN": str(HIER / "beispieldaten")}):
                o = unlock_post.main(jetzt=T, senden=lambda g, o, h: gesendet.append(h) or True,
                                     reel_bauen=lambda b, z, vo, c, g: "probe")
            self.assertEqual(len(o), 2)
            self.assertEqual(Image.open(o[0] / "post.png").size, (1080, 1920))   # Nachfolge: Reel-Bild
            self.assertEqual(Image.open(o[1] / "post.png").size, (1080, 1350))
            self.assertEqual(len(gesendet), 3)        # Nachfolge-Reel, ZRO-Bild, ZRO-Reel
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
