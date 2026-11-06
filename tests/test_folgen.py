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
                self.assertIn("reply_markup", gesendet[-1])   # lange Liste: Knoepfe an der letzten Nachricht
                datum = folgen.heute()
                stand = folgen.stand_laden(Path(d) / "folgen_stand.json")
                self.assertEqual(len(stand["heute"][datum]["x"]), 10)
                self.assertIn("erledigt", freigabe.folge_knopf({}, "ok", datum))
                stand = folgen.stand_laden(Path(d) / "folgen_stand.json")
                self.assertEqual(len(stand["erledigt"]), 12)   # je 5 Instagram, TikTok + 2 YouTube (06.11.2026)
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


class ZehnJePlattformTest(unittest.TestCase):
    """Tobias 03.11.2026: je 10; sind alle gefolgt, weiter kommentieren (am laengsten nicht gezeigt zuerst)."""

    def test_auffuellen_mit_schon_gefolgten(self):
        konten = [{"plattform": "tiktok", "name": f"t{i}"} for i in range(4)]
        stand = {"erledigt": {"tiktok:t0": 1, "tiktok:t1": 1}, "gezeigt": {"tiktok:t0": "2026-11-03", "tiktok:t1": "2026-11-01"}}
        a = folgen.auswahl(konten, stand, 0, 0, {"tiktok": 3})
        self.assertEqual([k["name"] for k in a["andere"]], ["t2", "t3", "t1"])   # neue zuerst, dann t1 (aelter gezeigt)
        self.assertTrue(a["andere"][2]["schon"])
        text, _ = folgen.nachricht(a, "2026-11-04")
        self.assertIn("folgst du schon", text)


class LangeNachrichtTest(unittest.TestCase):
    def test_wird_geteilt_knoepfe_am_ende(self):
        from social import telegram
        gesehen = []

        class A:
            def json(self):
                return {"ok": True}

        def post(url, data=None, timeout=None):
            gesehen.append(data)
            return A()
        text = "\n".join(f"<code>Kommentar Nummer {i} mit etwas Text, damit es lang wird.</code>" for i in range(200))
        self.assertEqual(telegram.an_tobias({"telegram_token": "t", "telegram_chat_id": 1}, text, {"k": 1}, post=post), "ok")
        self.assertGreater(len(gesehen), 1)
        self.assertTrue(all(len(d["text"]) <= 4096 for d in gesehen))
        self.assertIn("reply_markup", gesehen[-1])
        self.assertNotIn("reply_markup", gesehen[0])


class KeineWiederholungTest(unittest.TestCase):
    """06.11.2026 Tobias: Links von gestern kamen heute wieder. Jetzt: 7 Tage Sperre, YouTube jeden Tag neue Videos."""

    def test_konto_erst_nach_7_tagen_wieder(self):
        konten = [{"plattform": "tiktok", "name": f"t{i}"} for i in range(3)] + [{"plattform": "x", "name": "a"}]
        stand = {"erledigt": {"tiktok:t0": 1, "tiktok:t1": 1},
                 "gezeigt": {"tiktok:t0": "2026-11-05", "tiktok:t1": "2026-10-29", "tiktok:t2": "2026-11-05",
                             "x:a": "2026-11-05"}}
        a = folgen.auswahl(konten, stand, 5, 0, {"tiktok": 3}, "2026-11-06", 7)
        self.assertEqual([k["name"] for k in a["andere"]], ["t1"])   # t0/t2 gestern gezeigt, t1 vor 8 Tagen
        self.assertEqual(a["x"], [])

    def test_youtube_suche_neu_und_je_kanal_eins(self):
        class A:
            def __init__(self, j):
                self.j = j

            def json(self):
                return self.j

        def get(url, params=None, timeout=None):
            if url.endswith("/search"):
                self.assertEqual(params["order"], "viewCount")
                return A({"items": [
                    {"id": {"videoId": "v1"}, "snippet": {"title": "BTC after the jobs report", "channelTitle": "K1"}},
                    {"id": {"videoId": "v2"}, "snippet": {"title": "Second from K1", "channelTitle": "K1"}},
                    {"id": {"videoId": "v3"}, "snippet": {"title": "Gestern gezeigt", "channelTitle": "K3"}},
                    {"id": {"videoId": "v4"}, "snippet": {"title": "Altcoins &amp; whales", "channelTitle": "K4"}}]})
            return A({"items": [{"id": "v1", "statistics": {"viewCount": "500"}},
                                {"id": "v2", "statistics": {"viewCount": "900"}},
                                {"id": "v4", "statistics": {"viewCount": "2000"}}]})
        v = folgen.youtube_suche("k", ["bitcoin news"], ausser={"v3"}, get=get)
        self.assertEqual([x["id"] for x in v], ["v4", "v2"])   # meistgesehen zuerst, K1 nur einmal, v3 schon gezeigt
        self.assertEqual(v[0]["titel"], "Altcoins & whales")
        a = {"x": [], "andere": [], "videos": v, "suche": folgen.suchlinks(["bitcoin news"])}
        text, _ = folgen.nachricht(a, "2026-11-06")
        self.assertIn("watch?v=v4", text)
        self.assertIn("tiktok.com/search/video?q=bitcoin%20news", text)
        self.assertIn("instagram.com/explore/tags/bitcoinnews/", text)

    def test_begriffe_wechseln_taeglich(self):
        alle = ["a", "b", "c", "d", "e"]
        self.assertNotEqual(folgen.begriffe_heute(alle, "2026-11-06"), folgen.begriffe_heute(alle, "2026-11-07"))
        self.assertEqual(len(folgen.begriffe_heute(alle, "2026-11-06")), 2)
