"""S24 Liquiditaetszonen + Eilmeldungen (Wunsch Tobias 06.11.2026)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from PIL import Image

from social import liquiditaet as L

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


class LiquiditaetTest(unittest.TestCase):
    def setUp(self):
        self.d = L.laden(HIER / "beispieldaten")
        self.top = self.d["coins"][0]

    def test_texte_regeln(self):
        tx = L.texte(self.top, CFG, self.d["pruefung"])
        alles = tx["x"] + tx["telegram"] + " ".join(tx["sprech"])
        self.assertIn("estimated", alles)
        for verboten in ("target price", "will reach", "will hit", "buy ", "sell "):
            self.assertNotIn(verboten, alles.lower().replace("not targets", ""))
        self.assertLessEqual(len(tx["x"]), 280)
        self.assertEqual(tx["x"].count("$"), 1)                     # X: nur ein Cashtag
        self.assertIn("held 58% of the time", tx["x"])              # nur weil pruefung wirkt: True
        for z in tx["sprech"]:
            self.assertNotIn("(", z)
            self.assertNotIn("$", z)

    def test_quote_nur_wenn_bestaetigt(self):
        pr = [dict(self.d["pruefung"][0], wirkt=None)]
        self.assertNotIn("held", L.texte(self.top, CFG, pr)["x"])

    def test_ohne_liquidationsmodell_nur_widerstand_unterstuetzung(self):
        bat = self.d["coins"][1]
        oben, unten = L.zonen(bat)
        self.assertTrue(oben and unten)
        self.assertTrue(all(z["art"] not in L.LIQ for z in oben + unten))
        self.assertNotIn("liquidation", L.texte(bat, CFG, self.d["pruefung"])["x"].replace("where the liquidity", ""))

    def test_preise_ohne_exponent(self):
        self.assertEqual(L.pr(0.00001681), "0.00001681")
        self.assertEqual(L.pr(23.234), "23.23")
        self.assertEqual(L.pr(76543.2), "76,543")

    def test_bilder_und_heatmap(self):
        o = Path(tempfile.mkdtemp())
        try:
            b = L.beitrag(self.top, o, CFG, self.d["pruefung"])
            self.assertEqual(Image.open(o / "post.png").size, (1080, 1350))
            self.assertEqual(Image.open(o / "heatmap.png").size, (1080, 1350))
            import json as _j
            self.assertEqual(_j.loads((o / "karussell.json").read_text())["folien"], ["post.png", "heatmap.png"])
            fokus = _j.loads(b["szenen"][2][0].with_suffix(".fokus.json").read_text())["fokus"]
            self.assertTrue(0 < fokus[0] < 1080 and 0 < fokus[1] < 1920)
            self.assertEqual(Image.open(b["szenen"][0][0]).size, (1080, 1920))
            self.assertEqual(len(b["szenen"]), 3)                   # Zonen, naechste Zonen, Heatmap
            self.assertIn("brightest band", b["szenen"][2][1].lower())
            h = L.hellster(self.top)
            self.assertGreater(h["abstand_pct"], 0)                 # Beispiel: Short-Cluster ueber dem Kurs
            bat = L.beitrag(self.d["coins"][1], o / "bat", CFG, self.d["pruefung"])
            self.assertFalse((o / "bat" / "heatmap.png").exists())  # ohne Futures keine Heatmap
            self.assertEqual(len(bat["szenen"]), 2)
        finally:
            shutil.rmtree(o)


class EilTest(unittest.TestCase):
    def setUp(self):
        self.d = L.laden(HIER / "beispieldaten")
        self.t = 1794300000 + 3 * 3600   # 10.11.2026 nachmittags deutsche Zeit

    def test_grenzen(self):
        stand = {}
        neu = L.eil_auswahl(self.d, stand, self.t, set())
        self.assertEqual([e["base"] for e in neu], ["PEPE"])
        L.eil_merken(stand, neu[0], self.t)
        self.assertEqual(L.eil_auswahl(self.d, stand, self.t + 60, set()), [])           # schon gemeldet
        e2 = dict(self.d["eilmeldungen"][0], erstmals=self.t)
        d2 = dict(self.d, eilmeldungen=[e2])
        self.assertEqual(L.eil_auswahl(d2, stand, self.t + 3600, set()), [])             # 12-Std.-Sperre je Coin
        self.assertEqual(len(L.eil_auswahl(d2, stand, self.t + 24 * 3600, set())), 1)   # naechster Tag, tagsueber
        self.assertEqual(L.eil_auswahl(self.d, {}, self.t, {"PEPE"}), [])               # Sperrliste
        self.assertEqual(L.eil_auswahl(self.d, {}, self.t, set(), max_tag=0), [])        # Tageslimit

    def test_ruhezeit(self):
        nacht = 1794300000 - 6 * 3600   # 23:20 deutsche Zeit
        from datetime import datetime
        from zoneinfo import ZoneInfo
        self.assertTrue(datetime.fromtimestamp(nacht, ZoneInfo("Europe/Berlin")).hour >= 22
                        or datetime.fromtimestamp(nacht, ZoneInfo("Europe/Berlin")).hour < 7)
        self.assertEqual(L.eil_auswahl(self.d, {}, nacht, set()), [])

    def test_werkzeug(self):
        sys.path.insert(0, str(HIER / "tools"))
        import liq_eil
        d = Path(tempfile.mkdtemp())
        try:
            gesendet = []
            with mock.patch.object(liq_eil, "AUSGABE", d), mock.patch.object(liq_eil, "BASIS", d), \
                    mock.patch.dict("os.environ", {"SOCIAL_DATEN": str(HIER / "beispieldaten")}):
                o = liq_eil.main(jetzt=self.t, senden=lambda g, o, h: gesendet.append(h) or True,
                                 reel_bauen=lambda b, ro, cfg, g: (ro / "video.mp4", "probe"))
                self.assertEqual(len(o), 1)
                self.assertEqual(len(gesendet), 2)                      # Bild + Reel
                self.assertEqual(liq_eil.main(jetzt=self.t + 600), [])   # nicht doppelt
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
