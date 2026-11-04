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
        w = {"wale": {"wal": 30.0, "boerse": 10.0}}
        self.assertEqual(warum.wal_befund(dict(w, wale_7d={"wal": -2.0, "boerse": 1.5}))["label"], "Coins to exchanges")
        self.assertEqual(warum.wal_befund(dict(w, wale_7d={"wal": 1.4, "boerse": 0}))["label"], "Whales buying")
        self.assertIsNone(warum.wal_befund(dict(w, wale_7d={"wal": 0.2, "boerse": 0.1})))
        self.assertIsNone(warum.wal_befund({}))
        # CARV 04.11.: Wal-Anteil 0 % und -99,1 pp = Datenfehler, nie zeigen
        self.assertIsNone(warum.wal_befund({"wale": {"wal": 0.0, "boerse": 0}, "wale_7d": {"wal": -99.1}}))

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
        self.assertEqual(pruefung.pruefen(zeilen, b, warum.pruef_cfg(CFG), set()), [])
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


class VerliererUndVerlaufTest(unittest.TestCase):
    def test_richtung(self):
        d = daten.laden(HIER / "beispieldaten")
        d.news.append({"base": "MANTA", "chg24": -31.0, "driver": None})
        self.assertEqual(warum.auswahl(d, set(), "runter")["base"], "MANTA")
        self.assertGreater(warum.auswahl(d, set(), "hoch")["chg24"], 0)
        for n in d.news:
            n["chg24"] = abs(n["chg24"])
        self.assertIsNone(warum.auswahl(d, set(), "runter"))   # kein Verlierer -> kein Video

    def test_verlauf_speichern_und_satz(self):
        import tempfile
        from social import verlauf
        with tempfile.TemporaryDirectory() as t:
            o = Path(t)
            for h, f in ((7, 0.01), (6, 0.01), (0, -0.29)):
                verlauf.speichern({"BAT": {"funding": f, "oi": 1}}, o, 1_000_000 - h * 3600)
            v = verlauf.laden(o, "BAT")
            self.assertEqual(len(v), 3)
            verlauf.speichern({"BAT": {"funding": 1, "oi": 1}}, o, 1_000_000 + 60)   # < 30 Min. -> nicht doppelt
            self.assertEqual(len(verlauf.laden(o, "BAT")), 3)
        s = warum.verlauf_satz(v)
        self.assertEqual(s["satz"], "Funding went from +0.01% to -0.29% in 6 hours.")
        self.assertIsNone(warum.verlauf_satz(v[:1]))

    def test_beitrag_mit_verlauf_besteht_pruefung(self):
        d = daten.laden(HIER / "beispieldaten")
        v = [{"ts": 1000, "funding": 0.01}, {"ts": 1000 + 6 * 3600, "funding": -0.29}]
        b = warum.beitrag(d, set(), _kerzen(), "en", verlauf=v)
        fut = next(s for s in b["szenen"] if s["daten"].get("titel") == "FUTURES")
        self.assertIn("Funding went from +0.01% to -0.29% in 6 hours.", fut["vorlage"])
        self.assertEqual(pruefung.pruefen([s["vorlage"] for s in b["szenen"]], b, warum.pruef_cfg(CFG), set()), [])

    def test_stimme_im_gesundheits_check(self):
        import sys
        sys.path.insert(0, str(HIER / "tools"))
        import gesundheit
        self.assertTrue(gesundheit.stimme_eingerichtet(CFG, {"elevenlabs_api_key": "k"}))
        self.assertFalse(gesundheit.stimme_eingerichtet(CFG, {}))


class WunschCoinTest(unittest.TestCase):
    def test_coin_wahl_aus_bot_daten(self):
        d = daten.laden(HIER / "beispieldaten")
        w = warum.coin_wahl(d, "magic")
        self.assertEqual((w["base"], w["chg24"]), ("MAGIC", round(d.coins["MAGIC"]["chg24"], 1)))
        self.assertIsNone(warum.coin_wahl(d, "GIBTSNICHT"))
        b = warum.beitrag(d, set(), None, "en", wahl=w)
        self.assertEqual(b["base"], "MAGIC")

    def test_befehl(self):
        import sys
        from unittest import mock
        sys.path.insert(0, str(HIER / "tools"))
        import freigabe
        with mock.patch("subprocess.Popen") as p:
            t = freigabe.befehl({}, "/warum $clanker")
        self.assertIn("CLANKER", t)
        self.assertIn("--coin", p.call_args[0][0])
        self.assertIn("Ticker", freigabe.befehl({}, "/warum a-b"))


class EchteWerteTest(unittest.TestCase):
    """Tobias 04.11.: Kursverlauf, Volumen, abgeholte Zonen, Halter, Long/Short."""
    def _k(self):
        k = []
        for i in range(168):   # 6 Tage seitwaerts um 15 mit Hochs bei 16, dann Anstieg auf 23.9
            p = 15 + (1 if i % 20 == 10 else 0) if i < 144 else 15 + (i - 143) * 0.37
            k.append({"t": i * 3600000, "o": p, "h": p + 0.1, "l": p - 0.1, "c": p, "v": 100 if i < 144 else 600})
        return k

    def test_kurs_volumen_zonen(self):
        k = self._k()
        kb = warum.kurs_befund(k, True)
        self.assertIn("to a high of $23.98", kb["satz"])
        self.assertEqual(warum.volumen_befund(k)["r"], 6.0)
        zb = warum.zonen_befund(k, True)
        self.assertIn("old highs where short sellers had their stops", zb["satz"])
        self.assertEqual(warum.pr(23.234), "$23.23")
        self.assertEqual(warum.pr(0.045123), "$0.04512")

    def test_lsr_und_halter(self):
        from social import kurse
        rows = [{"timestamp": i, "longShortRatio": "1.5" if i else "0.8", "longAccount": "0.6"} for i in range(25)]
        l = kurse.long_short("X", get=lambda u, p: rows)
        self.assertEqual((l["jetzt"], round(l["long_pct"]), l["vor24"]), (1.5, 60, 0.8))
        self.assertIsNone(kurse.long_short("X", get=lambda u, p: {"code": -1121}))
        self.assertIn("so 60% of accounts are long (24 hours ago: 0.8)", warum.lsr_satz(l)["satz"])
        h = warum.halter_befund({"wale": {"wal": 41.2, "boerse": 12.5}})
        self.assertEqual(h["satz"], "Holders: whales hold 41.2% of the supply, exchanges 12.5%.")
        self.assertIsNone(warum.halter_befund({"wale": {"wal": 0, "boerse": 0}}))

    def test_ganzer_beitrag_besteht_pruefung(self):
        d = daten.laden(HIER / "beispieldaten")
        l = {"jetzt": 1.5, "long_pct": 60.0, "vor24": 0.8}
        b = warum.beitrag(d, set(), self._k(), "en", lsr=l)
        typen = [s["typ"] for s in b["szenen"]]
        self.assertEqual(typen[1], "warum_chart")
        text = " ".join(s["vorlage"] for s in b["szenen"])
        for teil in ("to a high of", "Long/short ratio", "daily average", "had their stops"):
            self.assertIn(teil, text)
        self.assertEqual(pruefung.pruefen([s["vorlage"] for s in b["szenen"]], b, warum.pruef_cfg(CFG), set()), [])
        txt = warum.texte(b, CFG)
        self.assertLessEqual(len(txt["x"]), 280)


if __name__ == "__main__":
    unittest.main()
