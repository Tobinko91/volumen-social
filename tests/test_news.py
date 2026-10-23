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
                self.assertNotIn("Quelle", x)
                tg = next(Path(d).glob("*_news/post_telegram.txt")).read_text()
                self.assertNotIn("Quelle", tg)
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


class NewsLayoutTest(unittest.TestCase):
    D = {"geeignet": True, "rubrik": "ETF", "schlagzeile": "SEC genehmigt ersten Solana-ETF",
         "kernsatz": "Die Gebühr liegt bei 0,25 % und die Zuflüsse bei 1,2 Mrd. $.",
         "punkte": ["Mehrere Medien berichten übereinstimmend.", "Weitere Anträge sind offen."],
         "x": "Die SEC hat den ersten Solana Spot-ETF genehmigt.", "coins": ["SOL"]}
    G = {"quellen": ["CoinDesk", "The Block"], "meldungen": []}

    def test_alle_layouts_ohne_quelle(self):
        from social import news_post
        kurs = [(i * 14400000, 100 + i * 0.5) for i in range(42)]
        with tempfile.TemporaryDirectory() as d:
            for lay in news_post.LAYOUTS:
                z = Path(d) / lay / "post.png"
                news_post.bild(self.D, self.G, CFG, z, kurs=kurs, layout=lay, jetzt=JETZT)
                self.assertEqual((z.parent / "layout.txt").read_text(), lay)
            # Chart ohne Kurs faellt auf klassisch zurueck
            z = Path(d) / "ohne" / "post.png"
            news_post.bild(self.D, self.G, CFG, z, kurs=None, layout="chart", jetzt=JETZT)
            self.assertEqual((z.parent / "layout.txt").read_text(), "klassisch")

    def test_kennzahl_und_hinweis(self):
        from social import news_post
        self.assertEqual(news_post.kennzahl(self.D), "0,25 %")
        self.assertIn("nur für dich", news_post.quellen_hinweis(self.G))
        self.assertNotIn("Quelle", news_post.texte(self.D, self.G, CFG)["x"])

    def test_layouts_wechseln(self):
        from social import news_post
        kurs = [(i, 1.0 + i) for i in range(42)]
        gesehen = {news_post.layout_waehlen(dict(self.D, schlagzeile=f"Meldung {i}"), kurs) for i in range(40)}
        self.assertEqual(gesehen, set(news_post.LAYOUTS))
