"""Punkt D (01.11.2026): Kommentar-Assistent – Posts holen, Kommentare pruefen, Nachricht an Tobias."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from social import kommentare

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
MARKT = {"median_24h": -0.8, "anteil_plus": 41, "anzahl": 312, "btc_24h": 1.2}
FAKTEN = kommentare.fakten_aus_markt(MARKT)
POST = "BREAKING: Spot Bitcoin ETFs saw $176 million in inflows on Tuesday."


class Antwort:
    def __init__(self, j, code=200):
        self._j, self.status_code, self.text = j, code, json.dumps(j)

    def json(self):
        return self._j


class KommentarTest(unittest.TestCase):
    def test_posts_je_konto_der_staerkste(self):
        gesehen = []

        def get(methode, url, headers=None, timeout=None):
            gesehen.append(url)
            return Antwort({"data": [
                {"id": "1", "author_id": "a", "text": "low", "public_metrics": {"like_count": 5}},
                {"id": "2", "author_id": "a", "text": "high", "public_metrics": {"like_count": 50, "reply_count": 9}},
                {"id": "3", "author_id": "b", "text": "other", "public_metrics": {"like_count": 20}}],
                "includes": {"users": [{"id": "a", "username": "KobeissiLetter"}, {"id": "b", "username": "lookonchain"}]}})
        g = {"x_api_key": "a", "x_api_secret": "b", "x_access_token": "c", "x_access_secret": "d"}
        p = kommentare.posts_holen(g, ["KobeissiLetter", "lookonchain"], get=get)
        self.assertEqual([x["id"] for x in p], ["2", "3"])
        self.assertEqual(p[0]["link"], "https://x.com/KobeissiLetter/status/2")
        q = parse_qs(urlparse(gesehen[0]).query)
        self.assertIn("from:KobeissiLetter OR from:lookonchain", q["query"][0])
        self.assertEqual(len(gesehen), 1)

    def test_pruefung(self):
        gut = "In the small caps we track, only 41% are green over 24h. Do ETF inflows reach alts this time?"
        self.assertEqual(kommentare.pruefen(gut, POST, FAKTEN, CFG, set()), [])
        self.assertEqual(kommentare.pruefen("$176 million in one day is solid. Where does it go next?", POST,
                                            FAKTEN, CFG, set()), [])   # Zahl aus dem Post erlaubt
        self.assertTrue(any("77" in f for f in kommentare.pruefen("77% of alts are green.", POST, FAKTEN, CFG, set())))
        self.assertIn("Link im Kommentar", kommentare.pruefen("See whalesqueeze.com for 41%.", POST, FAKTEN, CFG, set()))
        self.assertIn("Eigenwerbung", kommentare.pruefen("Follow us for more: 41% green.", POST, FAKTEN, CFG, set()))
        self.assertTrue(kommentare.pruefen("Das ist nicht gut und wird auch so bleiben, 41%.", POST, FAKTEN, CFG, set()))

    def test_nachricht_zum_kopieren(self):
        t = kommentare.nachricht([{"konto": "KobeissiLetter", "likes": 50, "text": POST, "link": "https://x.com/k/status/2",
                                   "kommentar": "Only 41% <green>.", "deutsch": "Nur 41 % grün."}])
        self.assertIn("<code>Only 41% &lt;green&gt;.</code>", t)
        self.assertIn("DE: Nur 41 % grün.", t)
        self.assertIn("🔗 https://x.com/k/status/2", t)

    def test_werkzeug_ende_zu_ende(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["SOCIAL_AUSGABE"] = d
            os.environ["SOCIAL_GEHEIM"] = d
            try:
                (Path(d) / "secrets.yaml").write_text(yaml.safe_dump({"telegram_token": "t", "telegram_chat_id": 1}))
                sys.path.insert(0, str(HIER / "tools"))
                import importlib
                import kommentare as werkzeug
                importlib.reload(werkzeug)
                posts = [{"id": "2", "konto": "KobeissiLetter", "text": POST, "likes": 50, "punkte": 70,
                          "link": "https://x.com/KobeissiLetter/status/2"},
                         {"id": "3", "konto": "lookonchain", "text": "Whale bought ETH.", "likes": 20, "punkte": 20,
                          "link": "https://x.com/lookonchain/status/3"}]
                vorschlaege = [{"id": "2", "text": "Meanwhile only 41% of small caps are green over 24h.", "deutsch": "x"},
                               {"id": "3", "text": "That's 999 ETH more than yesterday.", "deutsch": "y"}]   # erfunden
                gesendet = []

                class Ok:
                    def json(self):
                        return {"ok": True}

                def senden(url, data=None, timeout=None):
                    gesendet.append(data["text"])
                    return Ok()
                r = werkzeug.main(posts_holen=lambda: posts, schreiber=lambda ps: vorschlaege, markt=MARKT,
                                  senden=senden)
                self.assertEqual(r, 0)
                self.assertEqual(len(gesendet), 1)
                self.assertIn("41%", gesendet[0])
                self.assertNotIn("999", gesendet[0])   # Kommentar mit erfundener Zahl fliegt raus
                stand = json.loads((Path(d) / "kommentare_stand.json").read_text())
                self.assertEqual(stand["ids"], ["2"])
                gesendet.clear()   # zweiter Lauf: derselbe Post kommt nicht noch einmal, nur der Hinweis „keine neuen“
                werkzeug.main(posts_holen=lambda: posts[:1], schreiber=lambda ps: vorschlaege, markt=MARKT,
                              senden=senden)
                self.assertEqual(len(gesendet), 1)
                self.assertIn("keine neuen Posts", gesendet[0])
                gesendet.clear()   # X-Fehler wird gemeldet statt verschwiegen (Fehler 02.11.2026)

                def kaputt():
                    raise RuntimeError("X-Suche: 402 CreditsDepleted")
                self.assertEqual(werkzeug.main(posts_holen=kaputt, markt=MARKT, senden=senden), 1)
                self.assertIn("402", gesendet[0])
            finally:
                os.environ.pop("SOCIAL_AUSGABE")
                os.environ.pop("SOCIAL_GEHEIM")

    def test_plan(self):
        self.assertIn("15:30|20:30) sudo -u redaktion env $UMGEBUNG python3 tools/kommentare.py --senden",
                      (HIER / "tools/plan.sh").read_text())


class AnlassTest(unittest.TestCase):
    """Tobias 03.11.2026: Kommentare mit Frage zum aktuellen Anlass (z. B. Midterms), nicht nur Statistik."""

    def test_anlaesse_heute_morgen(self):
        import datetime as dt
        from social import kommentare as km
        a = km.anlaesse(dt.datetime(2026, 11, 3, 18).timestamp())
        self.assertIn("US midterm elections today", a)
        self.assertTrue(any("tomorrow" in x for x in a))
        self.assertIn("US midterm elections yesterday", km.anlaesse(dt.datetime(2026, 11, 4, 8).timestamp()))

    def test_prompt_will_gespraech(self):
        from social import folgen, kommentare as km
        for system in (km.SYSTEM, folgen.KOMMENTAR_SYSTEM):
            self.assertIn("current_events", system)
            self.assertIn("question", system)
            self.assertNotIn("Exactly one concrete number", system)


if __name__ == "__main__":
    unittest.main()
