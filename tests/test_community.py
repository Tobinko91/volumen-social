"""Community-Tipp BUY/SELL (Entscheidung Tobias 10.11.2026)."""
import json
import tempfile
import unittest
from pathlib import Path

from social import community


class CommunityTest(unittest.TestCase):
    def test_stimme(self):
        self.assertEqual(community.stimme("SELL for sure"), "sell")
        self.assertEqual(community.stimme("buy 🚀"), "buy")
        self.assertEqual(community.stimme("Long!"), "buy")
        self.assertIsNone(community.stimme("buy or sell? no idea"))
        self.assertIsNone(community.stimme("great video"))
        self.assertIsNone(community.stimme("Sellers everywhere"))   # nur ganze Woerter

    def test_je_autor_einmal_und_minimum(self):
        e = [("a", "sell"), ("a", "sell"), ("a", "buy"), ("b", "buy")] + [(f"x{i}", "SELL") for i in range(20)]
        z = community.zaehlen(e)
        self.assertEqual(z, {"buy": 1, "sell": 21})
        self.assertEqual(community.ergebnis(z), {"n": 22, "mehrheit": "sell", "pct": 95})
        self.assertIsNone(community.ergebnis({"buy": 5, "sell": 9}))          # unter 20
        self.assertIsNone(community.ergebnis({"buy": 15, "sell": 15}))        # unentschieden

    def test_youtube_id(self):
        self.assertEqual(community.youtube_id("https://youtube.com/shorts/abcDEF12345 (privat: …)"), "abcDEF12345")
        self.assertIsNone(community.youtube_id("Entwurf"))

    def test_holen_youtube_und_instagram(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "gepostet.json").write_text(json.dumps({
                "youtube": "https://youtube.com/shorts/abcDEF12345", "instagram": "https://www.instagram.com/reel/XYZ/"}))

            class R:
                def __init__(self, j): self.j = j
                def json(self): return self.j

            def get(url, params=None, timeout=None):
                self.assertEqual(params["videoId"], "abcDEF12345")
                return R({"items": [{"snippet": {"topLevelComment": {"snippet": {
                    "authorChannelId": {"value": f"c{i}"}, "textOriginal": "sell"}}}} for i in range(15)]})

            def ig(methode, pfad, token, **kw):
                if pfad == "me":
                    return {"user_id": "1"}
                if pfad == "1/media":
                    return {"data": [{"id": "m9", "permalink": "https://www.instagram.com/reel/XYZ/"}]}
                self.assertEqual(pfad, "m9/comments")
                return {"data": [{"username": f"u{i}", "text": "BUY" if i < 2 else "short it"} for i in range(8)]}

            erg, hinweis = community.holen(Path(t), {"youtube_api_key": "k", "instagram_token": "t"}, {}, get, ig)
            self.assertEqual(erg, {"n": 23, "mehrheit": "sell", "pct": 91})
            self.assertIn("YouTube 15", hinweis)
            self.assertIn("Instagram 8", hinweis)

    def test_nicht_gepostet(self):
        with tempfile.TemporaryDirectory() as t:
            erg, hinweis = community.holen(Path(t), {}, {})
            self.assertIsNone(erg)
            self.assertIn("nicht gepostet", hinweis)


if __name__ == "__main__":
    unittest.main()
