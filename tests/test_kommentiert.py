"""Knopf „✅ kommentiert“ und Kommentar-Bilanz (Wunsch Tobias 06.11.2026)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

from social import kommentiert

HIER = Path(__file__).resolve().parent.parent


class KommentiertTest(unittest.TestCase):
    def test_knoepfe_merken_bilanz(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "k.json"
            kommentiert.lauf_merken(p, "x11061530", [
                {"plattform": "X", "konto": "lookonchain", "link": "https://x.com/a/status/1"},
                {"plattform": "X", "konto": "glassnode", "link": "https://x.com/b/status/2"}] +
                [{"plattform": "YouTube", "konto": f"K{i}", "link": f"https://y/{i}"} for i in range(5)])
            kn = kommentiert.knoepfe("x11061530", 7, [[{"text": "alt", "callback_data": "f|ok|d"}]])
            self.assertEqual([len(r) for r in kn["inline_keyboard"]], [5, 2, 1])
            self.assertEqual(kn["inline_keyboard"][0][0]["callback_data"], "k|x11061530|1")
            self.assertTrue(all(len(b["callback_data"]) <= 64 for r in kn["inline_keyboard"] for b in r))
            self.assertIn("lookonchain", kommentiert.merken(p, "x11061530", "1", jetzt=1000))
            self.assertIn("Schon gemerkt", kommentiert.merken(p, "x11061530", "1", jetzt=1001))
            self.assertIn("zu alt", kommentiert.merken(p, "gibtsnicht", "1"))
            kommentiert.merken(p, "x11061530", "3", jetzt=1002)
            x = [{"ziel": "lookonchain", "likes": 10, "antworten": 2}, {"ziel": "lookonchain", "likes": 4, "antworten": 0},
                 {"ziel": "glassnode", "likes": 1, "antworten": 0}]
            text, wert = kommentiert.bilanz(kommentiert.laden(p), x, jetzt=2000)
            self.assertEqual(wert, {"lookonchain": 10.0, "glassnode": 1.0})
            self.assertIn("X 1", text)
            self.assertIn("Mehr bei @lookonchain", text)
            posts = [{"konto": "glassnode", "punkte": 900}, {"konto": "LookOnChain", "punkte": 5}, {"konto": "neu", "punkte": 50}]
            self.assertEqual([q["konto"] for q in kommentiert.sortieren(posts, wert)], ["LookOnChain", "glassnode", "neu"])

    def test_x_antworten(self):
        class R:
            status_code = 200

            def json(self):
                return {"data": [{"in_reply_to_user_id": "1", "public_metrics": {"like_count": 3, "reply_count": 1}},
                                 {"in_reply_to_user_id": "9", "public_metrics": {"like_count": 1}}],
                        "includes": {"users": [{"id": "1", "username": "lookonchain"}, {"id": "9", "username": "whalesqueeze"}]}}
        g = {"x_api_key": "a", "x_api_secret": "b", "x_access_token": "c", "x_access_secret": "d"}
        gesehen = []
        out = kommentiert.x_antworten(g, "whalesqueeze", get=lambda m, url, **kw: gesehen.append(url) or R())
        self.assertEqual(out, [{"ziel": "lookonchain", "likes": 3, "antworten": 1}])   # Antwort an uns selbst zaehlt nicht
        self.assertIn("from%3Awhalesqueeze", gesehen[0])

    def test_werkzeug(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["SOCIAL_AUSGABE"] = d
            os.environ["SOCIAL_GEHEIM"] = d
            try:
                import importlib
                sys.path.insert(0, str(HIER / "tools"))
                import kommentar_bilanz
                importlib.reload(kommentar_bilanz)
                t = kommentar_bilanz.main(x_holen=lambda: [{"ziel": "a", "likes": 2, "antworten": 0}])
                self.assertIn("@a", t)
                self.assertEqual(kommentiert.laden(Path(d) / "kommentiert.json")["wert"], {"a": 2.0})
            finally:
                os.environ.pop("SOCIAL_AUSGABE")
                os.environ.pop("SOCIAL_GEHEIM")
