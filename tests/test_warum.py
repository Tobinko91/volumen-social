"""„Why did it move?“ (Wunsch Tobias 04.11.2026): Regeln, Szenen, Zahlen-Pruefung, Texte."""
import unittest
from pathlib import Path

import yaml

from social import daten, pruefung, warum

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


def _kerzen(n=168, ende=1.0):
    return [{"t": i * 3600000, "o": 1.0, "h": 1.01 + (ende if i >= n - 24 else 0), "l": 0.99, "c": 1.0, "v": 1}
            for i in range(n)]


class RegelnTest(unittest.TestCase):
    def test_futures(self):
        self.assertEqual(warum.futures_befund(20, 15, -0.1)["label"], "Short squeeze")
        self.assertEqual(warum.futures_befund(20, -12, 0.01)["label"], "Short covering")
        self.assertEqual(warum.futures_befund(20, 15, 0.05)["label"], "Leverage rally")
        self.assertEqual(warum.futures_befund(-20, -15, 0.01)["label"], "Long flush")
        self.assertEqual(warum.futures_befund(-20, 15, -0.05)["label"], "New shorts")
        self.assertIsNone(warum.futures_befund(20, 3, 0.01))          # nichts Auffaelliges -> keine Behauptung
        self.assertIsNone(warum.futures_befund(20, None, 0.01))

    def test_spot_und_wale(self):
        self.assertEqual(warum.spot_befund(10, 80)["label"], "Real spot buying")
        self.assertEqual(warum.spot_befund(10, 20)["label"], "Futures-driven")
        self.assertIsNone(warum.spot_befund(10, 45))
        self.assertEqual(warum.wal_befund({"wale_7d": {"wal": -2.0, "boerse": 1.5}})["label"], "Coins to exchanges")
        self.assertEqual(warum.wal_befund({"wale_7d": {"wal": 1.4, "boerse": 0}})["label"], "Whales buying")
        self.assertIsNone(warum.wal_befund({"wale_7d": {"wal": 0.2, "boerse": 0.1}}))
        self.assertIsNone(warum.wal_befund({}))

    def test_chart_nur_rueckblick(self):
        b = warum.chart_befund(_kerzen(ende=1.0), 50)
        self.assertEqual(b["art"], "fib")
        self.assertIn("broke above last week's high", b["satz"])
        self.assertIsNone(warum.chart_befund(_kerzen(30), 50))


class BeitragTest(unittest.TestCase):
    def test_beispieldaten(self):
        from unittest import mock
        from social import sprache
        d = daten.laden(HIER / "beispieldaten")
        with mock.patch.object(warum, "haken_art", lambda tag=None: "frage"):
            b = warum.beitrag(d, set(), _kerzen(), "en")
        typen = [s["typ"] for s in b["szenen"]]
        self.assertEqual(typen[0], "warum_haken")
        self.assertEqual(typen[-2:], ["warum_urteil", "outro"])
        self.assertTrue(b["szenen"][0]["vorlage"].startswith("Why did BAT jump 52.8%"))
        self.assertIn("short squeeze", b["szenen"][-2]["vorlage"])
        zeilen = [s["vorlage"] for s in b["szenen"]]
        self.assertEqual(pruefung.pruefen(zeilen, b, CFG, set()), [])
        txt = warum.texte(b, CFG)
        self.assertLessEqual(len(txt["x"]), 280)
        self.assertIn("Not financial advice.", txt["x"])
        self.assertEqual(pruefung.pruefen([txt["x"], txt["telegram"]], dict(b, szenen=[0, 0]), CFG, set(),
                                          erlaubt_fusszeile=True), [])
        for w in ("target", "buy now", "entry", "stop loss"):   # keine Kursziele/Einstiege
            self.assertNotIn(w, " ".join(zeilen).lower())
        self.assertIsNotNone(sprache.T["en"]["cta"]["warum"])

    def test_sperrliste_und_ohne_regel(self):
        d = daten.laden(HIER / "beispieldaten")
        for n in d.news:
            if n["base"] != "BAT":
                n["chg24"] = 1.0
        b = warum.beitrag(d, {"BAT"}, None, "en")
        self.assertNotEqual(b["base"], "BAT")
        d.coins.get(b["base"], {}).update({"oi_chg4h": 1, "spot_anteil": 45, "wale_7d": None})
        for n in d.news:
            n["driver"] = None
        b = warum.beitrag(d, {"BAT"}, None, "en")
        self.assertIn("no clear driver", b["szenen"][-2]["vorlage"])


if __name__ == "__main__":
    unittest.main()
