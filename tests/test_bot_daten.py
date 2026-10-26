"""Neue Bot-Daten (Bot 9.10): markt.json und wale_7d/holder/wale_verlauf, jeweils mit Rueckfall."""
import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from social import daten, formate, post, pruefung, wal

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
D = daten.laden(HIER / "beispieldaten")


def ohne_neue_felder(d):
    d = copy.deepcopy(d)
    d.markt = None
    for c in d.coins.values():
        for k in ("wale_7d", "holder", "holder_7d", "wale_verlauf"):
            c.pop(k, None)
    return d


class MarktTest(unittest.TestCase):
    def test_markt_json_wird_gelesen(self):
        self.assertIsNotNone(D.markt)
        m = daten.marktlage(D)
        self.assertEqual(m["quelle"], "bot")
        self.assertEqual(m["median_24h"], round(D.markt["alt_median_24h"], 1))
        self.assertEqual(m["anteil_plus"], round(D.markt["alt_anteil_plus"]))
        self.assertEqual(m["btc_24h"], round(D.markt["btc"]["chg24"], 1))

    def test_rueckfall_ohne_markt_json(self):
        d = ohne_neue_felder(D)
        m = daten.marktlage(d)
        self.assertEqual(m["quelle"], "ersatz")
        self.assertEqual(m["median_24h"], daten.marktbreite(d)["median_24h"])
        self.assertNotIn("btc_24h", m)

    def test_markt_json_mit_null_nimmt_ersatz(self):
        d = copy.deepcopy(D)
        d.markt = dict(d.markt, alt_median_24h=None)
        self.assertEqual(daten.marktlage(d)["quelle"], "ersatz")

    def test_markt_30s_mit_btc_besteht_pruefung(self):
        b = formate.markt_30s(D, set())
        self.assertIn("Bitcoin", " ".join(s["vorlage"] for s in b["szenen"]))
        t = post.markt_texte(b, CFG)
        self.assertIn("Bitcoin", t["x"])
        self.assertLessEqual(len(t["x"]), 280)
        f = pruefung.pruefen([t["x"], t["telegram"]], dict(b, szenen=[0, 0]), CFG, set(), erlaubt_fusszeile=True)
        self.assertEqual(f, [])
        zeilen = [s["vorlage"] for s in b["szenen"]]
        self.assertEqual(pruefung.pruefen(zeilen, b, CFG, set()), [])

    def test_markt_30s_ohne_markt_json_wie_bisher(self):
        b = formate.markt_30s(ohne_neue_felder(D), set())
        self.assertNotIn("Bitcoin", " ".join(s["vorlage"] for s in b["szenen"]))


class WalTest(unittest.TestCase):
    def test_groesste_veraenderung_7_tage(self):
        w = daten.wal_des_tages(D, set())
        self.assertEqual(w["quelle"], "7d")
        self.assertEqual(w["base"], "BAT")      # |+2,4| > |-0,8|
        self.assertEqual(w["wal_7d"], 2.4)
        self.assertGreater(len(w["verlauf"]), 2)

    def test_sperrliste(self):
        self.assertEqual(daten.wal_des_tages(D, {"BAT"})["base"], "ZK")

    def test_rueckfall_hoechster_anteil(self):
        d = ohne_neue_felder(D)
        w = daten.wal_des_tages(d, set())
        self.assertEqual(w["quelle"], "anteil")
        kand = {b: c["wale"]["wal"] for b, c in d.coins.items()
                if c.get("wale") and (c.get("mcap") or 0) >= 20e6 and c["wale"].get("wal") is not None}
        self.assertEqual(w["base"], max(kand, key=kand.get))
        self.assertIsNone(w["wal_7d"])

    def test_texte_bestehen_pruefung_und_keine_empfehlung(self):
        for d in (D, ohne_neue_felder(D)):
            w = daten.wal_des_tages(d, set())
            t = wal.texte(w, CFG)
            self.assertLessEqual(len(t["x"]), 280)
            self.assertIn("Keine Anlageberatung", t["x"])
            f = pruefung.pruefen([t["x"], t["telegram"]], {"fakten": wal.fakten(w), "szenen": [0, 0]}, CFG,
                                 set(), erlaubt_fusszeile=True)
            self.assertEqual(f, [], t)

    def test_bild(self):
        with tempfile.TemporaryDirectory() as tmp:
            for d in (D, ohne_neue_felder(D)):
                p = wal.bild(daten.wal_des_tages(d, set()), CFG, Path(tmp) / "w.png")
                self.assertTrue(p.exists())

    def test_keine_wal_daten(self):
        d = ohne_neue_felder(D)
        for c in d.coins.values():
            c["wale"] = None
        self.assertIsNone(daten.wal_des_tages(d, set()))


if __name__ == "__main__":
    unittest.main()
