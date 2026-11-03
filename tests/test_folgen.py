"""Folge-Liste (Wunsch Tobias 31.10.2026): X per Knopf ueber die Schnittstelle, andere Plattformen per Link."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from social import folgen

HIER = Path(__file__).resolve().parent.parent
G = {"x_api_key": "a", "x_api_secret": "b", "x_access_token": "c", "x_access_secret": "d"}
KONTEN = [{"plattform": "x", "name": "glassnode", "warum": "On-Chain"},
          {"plattform": "x", "name": "gibtsnicht123", "warum": "?"},
          {"plattform": "x", "name": "CoinDesk", "warum": "News"},
          {"plattform": "instagram", "name": "watcher.guru", "warum": "Eil"},
          {"plattform": "youtube", "name": "benjaminjcowen", "warum": "Zyklen"}]


class Antwort:
    def __init__(self, j, code=200):
        self._j, self.status_code, self.content, self.text = j, code, b"x", json.dumps(j)

    def json(self):
        return self._j


class FolgenTest(unittest.TestCase):
    def test_liste_im_repo_ist_gueltig(self):
        k = folgen.liste()
        self.assertGreaterEqual(len([x for x in k if x["plattform"] == "x"]), 10)
        schon = {"kobeissiletter", "watcherguru", "whale_alert", "lookonchain"}   # schon von Hand gefolgt
        self.assertFalse(schon & {x["name"].lower() for x in k if x["plattform"] == "x"})
        self.assertEqual(len({(x["plattform"], x["name"].lower()) for x in k}), len(k))   # keine Doppelten

    def test_auswahl_ueberspringt_erledigte(self):
        a = folgen.auswahl(KONTEN, {"erledigt": {"x:glassnode": 1}}, n_x=1, n_andere=5)
        self.assertEqual([k["name"] for k in a["x"]], ["gibtsnicht123"])
        self.assertEqual([k["plattform"] for k in a["andere"]], ["instagram", "youtube"])

    def test_nachricht_mit_knoepfen_und_links(self):
        a = folgen.auswahl(KONTEN, {}, n_x=3)
        text, k = folgen.nachricht(a, "2026-10-31")
        self.assertIn('href="https://x.com/glassnode"', text)
        self.assertIn('href="https://www.instagram.com/watcher.guru/"', text)
        self.assertIn('href="https://www.youtube.com/@benjaminjcowen"', text)
        daten = [b["callback_data"] for b in k["inline_keyboard"][0]]
        self.assertEqual(daten, ["f|x|2026-10-31", "f|ok|2026-10-31"])
        self.assertTrue(all(len(d) <= 64 for d in daten))
        t, k = folgen.nachricht({"x": [], "andere": []}, "2026-10-31")
        self.assertIsNone(k)

    def test_x_folgen(self):
        aufrufe = []

        def anfrage(methode, url, json=None, timeout=None, headers=None):
            aufrufe.append((methode, url, json))
            self.assertTrue(headers["Authorization"].startswith("OAuth "))
            if url.endswith("/users/me"):
                return Antwort({"data": {"id": "999"}})
            if "/users/by?" in url:
                return Antwort({"data": [{"id": "1", "username": "glassnode"}, {"id": "3", "username": "CoinDesk"}]})
            if url.endswith("/users/999/following"):
                if json["target_user_id"] == "3":
                    return Antwort({"title": "Too Many Requests"}, 429)
                return Antwort({"data": {"following": True, "pending_follow": False}})
            return Antwort({}, 404)
        stand = {}
        z = folgen.x_folgen(G, ["glassnode", "gibtsnicht123", "CoinDesk"], stand, anfrage=anfrage,
                            warten=lambda s: None)
        self.assertEqual(stand["x_eigene_id"], "999")
        q = parse_qs(urlparse(next(u for m, u, j in aufrufe if "/users/by?" in u)).query)
        self.assertEqual(q["usernames"], ["glassnode,gibtsnicht123,CoinDesk"])
        self.assertEqual(z[0], "✅ @glassnode")
        self.assertIn("nicht gefunden", z[1])
        self.assertTrue(z[2].startswith("❌ @CoinDesk: 429"))
        self.assertIn("morgen", z[3])
        self.assertIn("x:glassnode", stand["erledigt"])
        self.assertNotIn("x:coindesk", stand["erledigt"])   # Limit: bleibt fuer morgen offen
        folgen.x_folgen(G, ["glassnode"], stand, anfrage=anfrage, warten=lambda s: None)
        self.assertEqual(sum(1 for m, u, j in aufrufe if u.endswith("/users/me")), 1)   # eigene ID gemerkt

    def test_ohne_x_schluessel(self):
        with self.assertRaises(folgen.FolgenFehler):
            folgen.x_folgen({}, ["a"], {})


class KnopfTest(unittest.TestCase):
    def test_taegliche_liste_und_knopf_andere_erledigt(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["SOCIAL_AUSGABE"] = d
            os.environ["SOCIAL_GEHEIM"] = d
            try:
                import importlib
                import sys
                sys.path.insert(0, str(HIER / "tools"))
                import folgen as werkzeug
                import freigabe
                importlib.reload(werkzeug)
                importlib.reload(freigabe)
                gesendet = []
                (Path(d) / "secrets.yaml").write_text(yaml.safe_dump({"telegram_token": "t", "telegram_chat_id": 1}))
                werkzeug.main(senden=lambda url, data=None, timeout=None: gesendet.append(data))
                self.assertIn("reply_markup", gesendet[0])
                datum = folgen.heute()
                stand = folgen.stand_laden(Path(d) / "folgen_stand.json")
                self.assertEqual(len(stand["heute"][datum]["x"]), 10)
                self.assertIn("erledigt", freigabe.folge_knopf({}, "ok", datum))
                stand = folgen.stand_laden(Path(d) / "folgen_stand.json")
                self.assertEqual(len(stand["erledigt"]), 10)   # 4 Instagram + 4 TikTok + 2 YouTube (02.11.2026)
                self.assertIn("X-Schlüssel fehlen", freigabe.folge_knopf({}, "x", datum))
                self.assertIn("zu alt", freigabe.folge_knopf({}, "x", "2020-01-01"))
            finally:
                os.environ.pop("SOCIAL_AUSGABE")
                os.environ.pop("SOCIAL_GEHEIM")


if __name__ == "__main__":
    unittest.main()


class AnTobiasTest(unittest.TestCase):
    """Fehler 02.11.2026: Folge-Liste kam nie an, niemand merkte es. Jetzt: Antwort pruefen, ohne HTML nochmal."""

    def test_html_abgelehnt_dann_ohne_formatierung(self):
        from social import telegram
        gesehen = []

        class A:
            def __init__(self, j):
                self.j = j

            def json(self):
                return self.j

        def post(url, data=None, timeout=None):
            gesehen.append(data)
            return A({"ok": False, "description": "can't parse entities"} if "parse_mode" in data else {"ok": True})
        g = {"telegram_token": "t", "telegram_chat_id": 1}
        self.assertEqual(telegram.an_tobias(g, "<b>Folge-Liste</b> <x>", post=post), "ok")
        self.assertEqual(len(gesehen), 2)
        self.assertEqual(gesehen[1]["text"], "Folge-Liste ")
        self.assertIn("fehlt", telegram.an_tobias({}, "x", post=post))


class InstaTikTokTest(unittest.TestCase):
    """Wunsch Tobias 02.11.2026: Instagram- und TikTok-Konten jeden Tag, mit Kommentar zum Einkopieren."""

    def test_je_plattform(self):
        a = folgen.auswahl(folgen.liste(), {}, 10, 5, {"instagram": 4, "tiktok": 4, "youtube": 2})
        pl = [k["plattform"] for k in a["andere"]]
        self.assertEqual((pl.count("instagram"), pl.count("tiktok"), pl.count("youtube")), (4, 4, 2))

    def test_kommentare_geprueft_und_in_nachricht(self):
        import yaml as _y
        cfg = _y.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
        fakten = {"window_hours": 24, "share_of_small_caps_up_24h_percent": 38.5, "small_caps_tracked": 412}

        class A:
            def raise_for_status(self):
                pass

            def json(self):
                return {"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps({"kommentare": [
                    {"text": "Only 38.5% of 412 small caps are green over 24h. Do you see the same?", "deutsch": "a"},
                    {"text": "Whales bought 9,999 BTC today.", "deutsch": "erfunden"},
                    {"text": "Check our page https://x.y", "deutsch": "Link"},
                    {"text": "Only 38.5% of 412 small caps are green over 24h. Do you see the same?", "deutsch": "doppelt"}]})}]}
        k = folgen.kommentare_schreiben(3, fakten, cfg, "key", post=lambda *a, **kw: A())
        self.assertEqual(len(k), 1)
        a = folgen.auswahl(folgen.liste(), {}, 0, 5, {"instagram": 1})
        text, _ = folgen.nachricht(a, "2026-11-03", k)
        self.assertIn("<code>Only 38.5% of 412 small caps", text)
        self.assertIn("instagram.com", text)


class YouTubeVideoTest(unittest.TestCase):
    """Wunsch Tobias 03.11.2026: YouTube-Kommentar passend zum neuesten Video."""

    def test_neuestes_video(self):
        class A:
            def __init__(self, j):
                self.j = j

            def json(self):
                return self.j

        def get(url, params=None, timeout=None):
            if url.endswith("/channels"):
                self.assertEqual(params["forHandle"], "@CoinBureau")
                return A({"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]})
            return A({"items": [{"snippet": {"title": "Midterms and crypto: what to expect", "description": "We look at...",
                                             "publishedAt": "2026-11-03T12:00:00Z", "resourceId": {"videoId": "abc"}}}]})
        import datetime as dt
        jetzt = dt.datetime(2026, 11, 3, 18, tzinfo=dt.timezone.utc).timestamp()
        v = folgen.youtube_neuestes("CoinBureau", "k", get=get, jetzt=jetzt)
        self.assertEqual(v["link"], "https://www.youtube.com/watch?v=abc")
        self.assertIn("Midterms", v["text"])
        self.assertIsNone(folgen.youtube_neuestes("CoinBureau", "k", get=get, jetzt=jetzt + 30 * 86400))   # zu alt

    def test_nachricht_mit_video_kommentar(self):
        a = {"x": [], "andere": [{"plattform": "youtube", "name": "CoinBureau", "warum": "Bildung",
                                  "video": {"link": "https://www.youtube.com/watch?v=abc", "titel": "Midterms and crypto"},
                                  "kommentar": "Great timing. Which result matters most for BTC tonight?"},
                                 {"plattform": "tiktok", "name": "x", "warum": "y"}]}
        text, _ = folgen.nachricht(a, "2026-11-03", [{"text": "Love this. How do you see the midterms for BTC?"}])
        self.assertIn("watch?v=abc", text)
        self.assertIn("<code>Great timing.", text)
        self.assertIn("<code>Love this.", text)
