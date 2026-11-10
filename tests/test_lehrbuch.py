"""S29 „The textbook is WRONG“ (Wunsch Tobias 10.11.2026)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from social import lehrbuch

HIER = Path(__file__).resolve().parent.parent


class LehrbuchTest(unittest.TestCase):
    def setUp(self):
        self.daten = lehrbuch.laden(HIER / "beispieldaten")
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_laden_und_reihenfolge(self):
        self.assertIn("double_top", self.daten)
        self.assertEqual(lehrbuch.naechste(self.daten, []), "double_top")
        self.assertEqual(lehrbuch.naechste(self.daten, ["double_top"]), "range_breakdown")
        # Double Bottom fehlt in den Daten -> diese Woche keine Folge (Reihenfolge bleibt)
        self.assertIsNone(lehrbuch.naechste(self.daten, ["double_top", "range_breakdown"]))
        alle = ["double_top", "range_breakdown", "double_bottom", "three_white_soldiers"]
        self.assertEqual(lehrbuch.naechste(self.daten, alle), "hammer")
        self.assertIsNone(lehrbuch.naechste(self.daten, alle + ["hammer"]))

    def test_ohne_daten(self):
        self.assertEqual(lehrbuch.laden(self.tmp), {})
        (self.tmp / "muster_des_tages.json").write_text(json.dumps({"lehrbuch_falsch": [{"muster": "double_top"}]}))
        self.assertNotIn("double_top", lehrbuch.laden(self.tmp))   # unvollstaendig -> ignoriert
        self.assertIsNone(lehrbuch.naechste(lehrbuch.laden(self.tmp), []))

    def test_texte_nennen_fallzahl_und_zufall(self):
        tx = lehrbuch.texte(self.daten["double_top"])
        alles = " ".join(tx["zeilen"])
        self.assertIn("26,598 cases", alles)
        self.assertIn("49.5%", alles)
        self.assertIn("55.0%", alles)
        self.assertIn("The textbook was wrong.", alles)
        self.assertIn("Worse than random.", alles)
        self.assertEqual(tx["zeilen"][-1], "Follow for the next myth.")
        self.assertLessEqual(len(tx["x"]), 280)
        self.assertTrue(tx["x"].endswith("Not financial advice."))
        self.assertEqual(tx["x"].count("$"), 1)   # X: nur ein Cashtag
        for w in ("buy now", "sell now", "target", "guarant", "get rich"):
            self.assertNotIn(w, (alles + tx["x"]).lower())

    def test_szenen_passen_zu_den_zeilen(self):
        folgen, tx = lehrbuch.szenen(self.daten["double_top"], self.tmp)
        self.assertEqual(len(folgen), len(tx["zeilen"]))
        self.assertEqual(len(folgen[2]), 7)   # 6 Kerzen nacheinander + Ergebnis
        for f in folgen:
            for p, sek in f:
                self.assertEqual(Image.open(p).size, (1080, 1920))
                self.assertGreater(sek, 0)

    def test_abschluss_hammer(self):
        s = self.daten["_statistik"]["hammer"]
        folgen, tx = lehrbuch.abschluss_szenen(s, self.tmp)
        self.assertEqual(len(folgen), len(tx["zeilen"]))
        alles = " ".join(tx["zeilen"])
        self.assertIn("12,518 cases", alles)
        self.assertIn("51.9%", alles)
        self.assertIn("45.0%", alles)
        self.assertIn("not a guarantee", alles)
        self.assertIn("after fees", alles)
        self.assertLessEqual(len(tx["x"]), 280)

    def test_video_mit_attrappen(self):
        folgen, tx = lehrbuch.szenen(self.daten["range_breakdown"], self.tmp / "b")
        gerufen = {}

        def sprechen(zeilen, ordner, cfg, key):
            return [Path(f"t{i}.mp3") for i in range(len(zeilen))], [1.0] * len(zeilen), "attrappe"

        def schneiden(bilder, toene, dauern, ziel, cfg, texte=None, untertitel_y=None):
            gerufen.update(n=len(bilder), dauern=dauern, y=untertitel_y)

        pfad, quelle = lehrbuch.video(folgen, tx, self.tmp, {}, {}, sprechen, schneiden)
        self.assertEqual(quelle, "attrappe")
        self.assertEqual(gerufen["n"], len(tx["zeilen"]))
        self.assertGreater(gerufen["dauern"][3], 5.0)   # Zahl-Karte bleibt lange genug stehen
        self.assertEqual(gerufen["y"], 1590)


if __name__ == "__main__":
    unittest.main()
