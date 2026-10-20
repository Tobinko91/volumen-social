import tempfile
import types
import unittest
from pathlib import Path

import yaml

import main
from social import news

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
RSS = (HIER / "tests/feeds/rss.xml").read_text()
ATOM = (HIER / "tests/feeds/atom.xml").read_text()
JETZT = 1792490400  # 20.10.2026 12:00 UTC


def laden(url):
    if "btc-echo" in url:
        return ATOM
    if "coindesk" in url or "theblock" in url:
        return RSS
    raise OSError("offline")


class NewsTest(unittest.TestCase):
    def test_rss_und_atom_werden_gelesen(self):
        a = news.parse_feed(RSS, {"name": "X"})
        b = news.parse_feed(ATOM, {"name": "Y"})
        self.assertEqual(len(a), 2)
        self.assertEqual(b[0]["link"], "https://example.de/b1")
        self.assertIn("0,25 %", b[0]["kurz"])

    def test_kaputter_feed_stoppt_nicht(self):
        m, status = news.einsammeln(jetzt=JETZT, laden=laden)
        self.assertTrue(any("Fehler" in v for v in status.values()))
        self.assertGreaterEqual(len(m), 5)

    def test_gleiches_ereignis_wird_gebuendelt(self):
        m, _ = news.einsammeln(jetzt=JETZT, laden=laden)
        g = news.buendeln(m)
        self.assertIn("ETF", g[0]["meldungen"][0]["titel"])
        self.assertGreaterEqual(len(g[0]["quellen"]), 3)
        self.assertTrue(g[0]["eil"])

    def test_beitrag_pruefung_und_kein_doppelt(self):
        def schreiber(g):
            return {"geeignet": True, "rubrik": "ETF", "schlagzeile": "SEC genehmigt ersten Solana-ETF",
                    "kernsatz": "Die US-Börsenaufsicht hat den ersten Spot-ETF auf Solana genehmigt.",
                    "punkte": ["Die Gebühr liegt bei 0,25 %.", "Mehrere Medien berichten übereinstimmend."],
                    "x": "Die SEC hat den ersten Solana Spot-ETF genehmigt. Gebühr: 0,25 %.", "coins": ["SOL"]}
        orig = news.einsammeln
        news.einsammeln = lambda laden=None, **k: orig(jetzt=JETZT, laden=laden)
        try:
            with tempfile.TemporaryDirectory() as d:
                args = types.SimpleNamespace(out=d, eil=False, senden=False)
                self.assertEqual(main.news_beitrag(args, CFG, {}, set(), laden=laden, schreiber=schreiber), 0)
                x = next(Path(d).glob("*_news/post_x.txt")).read_text()
                self.assertLessEqual(len(x), 280)
                self.assertIn("Quelle:", x)
                # zweiter Lauf: dieselbe Nachricht nicht noch einmal
                for p in Path(d).glob("*_news"):
                    p.rename(p.with_name("alt_" + p.name))
                main.news_beitrag(args, CFG, {}, set(), laden=laden, schreiber=schreiber)
                neu = [p for p in Path(d).glob("*_news") if not p.name.startswith("alt_")]
                if neu:
                    self.assertNotIn("ETF", (neu[0] / "quellen.json").read_text())
        finally:
            news.einsammeln = orig

    def test_erfundene_zahl_faellt_durch(self):
        def schreiber(g):
            return {"geeignet": True, "rubrik": "ETF", "schlagzeile": "SEC genehmigt Solana-ETF",
                    "kernsatz": "Zuflüsse von 750 Millionen erwartet.", "punkte": ["Gebühr 0,25 %."],
                    "x": "SEC genehmigt Solana-ETF.", "coins": []}
        orig = news.einsammeln
        news.einsammeln = lambda laden=None, **k: orig(jetzt=JETZT, laden=laden)
        try:
            with tempfile.TemporaryDirectory() as d:
                args = types.SimpleNamespace(out=d, eil=False, senden=False)
                self.assertEqual(main.news_beitrag(args, CFG, {}, set(), laden=laden, schreiber=schreiber), 1)
        finally:
            news.einsammeln = orig

    def test_sperrliste(self):
        def schreiber(g):
            return {"geeignet": True, "rubrik": "ETF", "schlagzeile": "SEC genehmigt Solana-ETF",
                    "kernsatz": "Genehmigt.", "punkte": ["Gebühr 0,25 %."], "x": "SEC genehmigt SOL-ETF.",
                    "coins": ["SOL"]}
        orig = news.einsammeln
        news.einsammeln = lambda laden=None, **k: orig(jetzt=JETZT, laden=laden)
        try:
            with tempfile.TemporaryDirectory() as d:
                args = types.SimpleNamespace(out=d, eil=False, senden=False)
                self.assertEqual(main.news_beitrag(args, CFG, {}, {"SOL"}, laden=laden, schreiber=schreiber), 1)
        finally:
            news.einsammeln = orig


if __name__ == "__main__":
    unittest.main()
