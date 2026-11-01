"""S13 Termine der Woche: Woche, Zeitumrechnung ET/UTC, Optionsverfall, Pflege-Warnung, Texte, Bild."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

import yaml

from social import pruefung, termine

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
LISTE = termine.laden(HIER / "inhalte" / "termine.yaml")


class TermineTest(unittest.TestCase):
    def test_letzter_freitag(self):
        self.assertEqual(termine.letzter_freitag(2026, 11), dt.date(2026, 11, 27))
        self.assertEqual(termine.letzter_freitag(2026, 12), dt.date(2026, 12, 25))
        self.assertEqual(termine.letzter_freitag(2027, 1), dt.date(2027, 1, 29))

    def test_woche_mit_utc_und_verfall_einmal(self):
        e = termine.woche(LISTE, dt.date(2026, 11, 23), "en")
        self.assertEqual([x["art"] for x in e], ["pce", "verfall"])
        self.assertEqual((e[0]["et"], e[0]["utc"]), ("8:30 AM", "13:30"))   # Winterzeit: ET = UTC-5
        self.assertEqual((e[1]["et"], e[1]["utc"]), ("3:00 AM", "08:00"))
        self.assertIn("October", e[0]["info"])

    def test_verfall_ueber_monatsgrenze(self):
        e = termine.woche(LISTE, dt.date(2027, 1, 25), "en")   # 25.-31.1., Verfall 29.1.
        self.assertIn("2027-01-29", [x["datum"] for x in e if x["art"] == "verfall"])
        self.assertEqual(sum(1 for x in e if x["art"] == "verfall"), 1)

    def test_sommerzeit(self):
        liste = {"arten": LISTE["arten"], "termine": [{"datum": "2027-06-09", "zeit": "14:00", "art": "fomc"}]}
        e = termine.woche(liste, dt.date(2027, 6, 7), "en")
        self.assertEqual(e[0]["utc"], "18:00")   # Sommerzeit: ET = UTC-4

    def test_liste_sortiert_und_bekannte_arten(self):
        daten = [dt.date.fromisoformat(str(t["datum"])) for t in LISTE["termine"]]
        self.assertEqual(daten, sorted(daten))
        self.assertTrue(all(t["art"] in LISTE["arten"] for t in LISTE["termine"]))

    def test_pflege_warnung(self):
        self.assertEqual(termine.pflege_luecken(LISTE, dt.date(2026, 11, 2)), [])
        self.assertTrue(any(l.startswith("pce") for l in termine.pflege_luecken(LISTE, dt.date(2026, 12, 14))))

    def test_texte_pruefung_und_bild(self):
        montag = dt.date(2026, 12, 7)
        e = termine.woche(LISTE, montag, "en")
        txt = termine.texte(e, CFG, "en")
        self.assertLessEqual(len(txt["x"]), 280)
        self.assertIn("Fed rate decision: Wed Dec 9, 19:00 UTC", txt["x"])
        self.assertIn("2:00 PM ET / 19:00 UTC", txt["telegram"])
        self.assertNotIn("http", txt["telegram"])   # keine Quellen im Beitrag
        fehler = pruefung.pruefen([txt["x"], txt["telegram"]], {"fakten": termine.fakten(e), "szenen": [0, 0]},
                                  CFG, set(), erlaubt_fusszeile=True)
        self.assertEqual(fehler, [])
        with tempfile.TemporaryDirectory() as d:
            from PIL import Image
            p = termine.bild(e, CFG, Path(d) / "post.png", montag, "en")
            self.assertEqual(Image.open(p).size, (1080, 1350))

    def test_deutsch(self):
        e = termine.woche(LISTE, dt.date(2026, 11, 2), "de")
        self.assertEqual(e[-1]["tag"], "FR")
        self.assertIn("Fr 6.11.", termine.texte(e, CFG, "de")["x"])

    def test_immer_kommende_woche(self):
        self.assertEqual(termine.kommende_woche(dt.date(2026, 11, 1)), dt.date(2026, 11, 2))   # Sonntag -> morgen
        self.assertEqual(termine.kommende_woche(dt.date(2026, 11, 2)), dt.date(2026, 11, 2))   # Montag -> diese Woche
        self.assertEqual(termine.kommende_woche(dt.date(2026, 11, 4)), dt.date(2026, 11, 9))   # Mittwoch -> naechste

    def test_ganztaegig_und_woche_2_november(self):
        e = termine.woche(LISTE, dt.date(2026, 11, 2), "en")
        self.assertEqual([x["art"] for x in e], ["ism", "wahl", "ism_dienst", "nfp"])
        txt = termine.texte(e, CFG, "en")
        self.assertIn("US midterm elections: Tue Nov 3, All day", txt["x"])
        self.assertIn("ISM manufacturing: Mon Nov 2, 15:00 UTC", txt["x"])
        fehler = pruefung.pruefen([txt["x"], txt["telegram"]], {"fakten": termine.fakten(e), "szenen": [0, 0]},
                                  CFG, set(), erlaubt_fusszeile=True)
        self.assertEqual(fehler, [])


if __name__ == "__main__":
    unittest.main()
