import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from social import daten, formate, links, post, pruefung

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())


class LinkTest(unittest.TestCase):
    def test_alle_kennungen(self):
        u = urlparse(links.link("tiktok", "markt_30s", "20261024-0730_markt"))
        self.assertEqual((u.scheme, u.netloc, u.path), ("https", "whalesqueeze.com", "/"))
        self.assertEqual(parse_qs(u.query), {"utm_source": ["tiktok"], "utm_medium": ["social"],
                                             "utm_campaign": ["markt_30s"], "utm_content": ["20261024-0730_markt"]})

    def test_jeder_kanal_und_unbekannter_kanal(self):
        for k in ("tiktok", "instagram", "youtube", "x", "telegram"):
            self.assertIn(f"utm_source={k}&", links.link(k, "news", "a"))
        with self.assertRaises(ValueError):
            links.link("facebook", "news", "a")

    def test_pfad_sprache_und_sonderzeichen(self):
        self.assertTrue(links.link("x", "Coin Check!", "ä b", pfad="coin/ake/").startswith(
            "https://whalesqueeze.com/coin/ake/?"))
        self.assertIn("utm_campaign=coin-check", links.link("x", "Coin Check!", "x"))
        self.assertTrue(links.link("x", "bio", "profil", lang="en").startswith("https://whalesqueeze.com/en/?"))

    def test_bio_links(self):
        b = links.bio_links()
        self.assertEqual(b["instagram"], "https://whalesqueeze.com/?utm_source=instagram&utm_medium=social"
                                         "&utm_campaign=bio&utm_content=profil")
        self.assertEqual(len(b), 5)

    def test_telegram_link_vor_hinweis_und_pruefung_bestanden(self):
        d = daten.laden(HIER / "beispieldaten")
        b = formate.markt_30s(d, set())
        t = post.markt_texte(b, CFG)
        tg = links.mit_telegram_link(t["telegram"], b["format"], "20261024-0730_markt")
        self.assertIn('href="https://whalesqueeze.com/?utm_source=telegram&amp;utm_medium=social', tg)
        self.assertTrue(tg.rstrip().endswith("</i>"))   # Hinweis bleibt letzte Zeile
        f = pruefung.pruefen([t["x"], tg], dict(b, szenen=[0, 0]), CFG, set(), erlaubt_fusszeile=True)
        self.assertEqual(f, [])

    def test_fremde_zahlen_fallen_weiter_auf(self):
        f = pruefung.pruefen(["BTC steigt 999 Prozent https://whalesqueeze.com/?utm_content=123"],
                             {"fakten": {}, "szenen": [0]}, CFG, set())
        self.assertTrue(any("999" in x for x in f))
        self.assertFalse(any("123" in x for x in f))

    def test_zu_lang_fuer_telegram_kein_halber_link(self):
        lang = "x" * 1000
        self.assertEqual(links.mit_telegram_link(lang, "news", "a"), lang)

    def test_beschreibungen_je_kanal(self):
        b = links.beschreibungen("Text", "markt_30s", "id1")
        self.assertEqual(set(b), {"youtube", "tiktok", "instagram"})
        self.assertIn("utm_source=youtube", b["youtube"])

    def test_x_posts_ohne_link(self):
        # X zeigt Beitraege mit Links seltener -> Link nur im Profil, nie im X-Text
        d = daten.laden(HIER / "beispieldaten")
        t = post.markt_texte(formate.markt_30s(d, set()), CFG)
        self.assertNotIn("http", t["x"])


if __name__ == "__main__":
    unittest.main()
