"""TikTok: Login-Link, Code aus der Adresse, Token erneuern, Foto-Beitrag (Entwurf/direkt), Aufraeumen."""
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from social import kanaele, telegram, tiktok

HIER = Path(__file__).resolve().parent.parent
LOGO = HIER / "assets/logo-1080.png"
G = {"tiktok_client_key": "ck", "tiktok_client_secret": "cs", "tiktok_refresh_token": "rt",
     "tiktok_access_token": "at", "tiktok_bis": time.time() + 3600}


class Antwort:
    def __init__(self, j, code=200):
        self._j, self.status_code, self.content, self.text = j, code, b"x", json.dumps(j)

    def json(self):
        return self._j


class TikTokTest(unittest.TestCase):
    def test_login_link_und_code(self):
        u = urlparse(tiktok.login_link("ck", "s1"))
        q = parse_qs(u.query)
        self.assertEqual((u.netloc, q["client_key"][0], q["redirect_uri"][0], q["state"][0]),
                         ("www.tiktok.com", "ck", "https://whalesqueeze.com/tiktok/", "s1"))
        self.assertIn("video.publish", q["scope"][0])
        self.assertEqual(tiktok.code_aus_adresse("https://whalesqueeze.com/tiktok/?code=ABC%2A&state=s1", "s1"), "ABC*")
        with self.assertRaises(tiktok.TikTokFehler):
            tiktok.code_aus_adresse("https://whalesqueeze.com/tiktok/?code=ABC&state=falsch", "s1")
        with self.assertRaises(tiktok.TikTokFehler):
            tiktok.code_aus_adresse("https://whalesqueeze.com/tiktok/?error=access_denied&state=s1", "s1")

    def test_token_erneuern_wenn_abgelaufen(self):
        g = dict(G, tiktok_bis=0)
        gesehen, gespeichert = [], {}

        def post(url, data=None, json=None, headers=None, timeout=None):
            gesehen.append(data)
            return Antwort({"access_token": "neu", "refresh_token": "rt2", "expires_in": 86400,
                            "refresh_expires_in": 31536000, "open_id": "o"})
        tok = tiktok.gueltiger_token(g, post, sichern=lambda g, n: (g.update(n), gespeichert.update(n)))
        self.assertEqual(tok, "neu")
        self.assertEqual(gesehen[0]["grant_type"], "refresh_token")
        self.assertEqual(gespeichert["tiktok_refresh_token"], "rt2")

    def test_speichern_behaelt_andere_schluessel(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "secrets.yaml"
            p.write_text(yaml.safe_dump({"x_api_key": "x"}))
            tiktok.speichern({}, {"tiktok_access_token": "a"}, p)
            self.assertEqual(yaml.safe_load(p.read_text()), {"x_api_key": "x", "tiktok_access_token": "a"})

    def test_titel_und_text(self):
        tg = "📊 <b>Crypto market, Oct 26</b>\n\n• BTC +1.2%\n🔗 <a href=\"https://whalesqueeze.com/en/?utm_source=telegram\">x</a>\n\n<i>Not financial advice.</i>"
        titel, text = tiktok.titel_und_text(tg)
        self.assertEqual(titel, "📊 Crypto market, Oct 26")
        self.assertNotIn("utm_", text)
        self.assertIn("link in bio", text)
        self.assertIn("Not financial advice.", text)
        self.assertLessEqual(len(tiktok.titel_und_text("a" * 200 + "\n" + "b" * 5000)[1]), tiktok.TEXT_MAX)
        self.assertLessEqual(len(tiktok.titel_und_text("a" * 200)[0]), tiktok.TITEL_MAX)


class TikTokPostenTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.alt = kanaele.IG_ORDNER
        kanaele.IG_ORDNER = self.d

    def tearDown(self):
        kanaele.IG_ORDNER = self.alt
        shutil.rmtree(self.d)

    def _post(self, aufrufe, optionen=("SELF_ONLY",), status="SEND_TO_USER_INBOX"):
        def post(url, data=None, json=None, headers=None, timeout=None):
            aufrufe.append((url.split("/v2/")[-1], json))
            if url.endswith("creator_info/query/"):
                return Antwort({"data": {"privacy_level_options": list(optionen)}, "error": {"code": "ok"}})
            if url.endswith("content/init/"):
                self.datei_da = list(self.d.glob("*.jpg"))
                return Antwort({"data": {"publish_id": "p1"}, "error": {"code": "ok"}})
            if url.endswith("status/fetch/"):
                return Antwort({"data": {"status": status}, "error": {"code": "ok"}})
            return Antwort({"error": {"code": "invalid_param", "message": "?"}}, 400)
        return post

    def test_entwurf_in_der_app(self):
        aufrufe = []
        m = kanaele.tiktok_posten(dict(G), LOGO, "📊 <b>Test</b>\n\nNot financial advice.", pruefen_url=lambda u: 200,
                                  post=self._post(aufrufe), warten=lambda s: None)
        self.assertIn("Entwurf", m)
        init = next(j for p, j in aufrufe if p.endswith("content/init/"))
        self.assertEqual((init["media_type"], init["post_mode"]), ("PHOTO", "MEDIA_UPLOAD"))
        self.assertTrue(init["source_info"]["photo_images"][0].startswith("https://whalesqueeze.com/medien/"))
        self.assertTrue(init["source_info"]["photo_images"][0].endswith(".jpg"))
        self.assertEqual(len(self.datei_da), 1)
        self.assertEqual(list(self.d.iterdir()), [])   # danach geloescht

    def test_direkt_ohne_pruefung_nur_privat(self):
        aufrufe = []
        m = tiktok.foto_posten(dict(G), "https://whalesqueeze.com/medien/x.jpg", "a", modus="direkt",
                               post=self._post(aufrufe, status="PUBLISH_COMPLETE"), warten=lambda s: None)
        init = next(j for p, j in aufrufe if p.endswith("content/init/"))
        self.assertEqual(init["post_mode"], "DIRECT_POST")
        self.assertEqual(init["post_info"]["privacy_level"], "SELF_ONLY")
        self.assertIn("privat", m)

    def test_fehler_wird_gemeldet(self):
        def post(url, **kw):
            return Antwort({"error": {"code": "url_ownership_unverified", "message": "verify"}}, 403)
        with self.assertRaises(tiktok.TikTokFehler) as e:
            kanaele.tiktok_posten(dict(G), LOGO, "a", pruefen_url=lambda u: 200, post=post, warten=lambda s: None)
        self.assertIn("url_ownership_unverified", str(e.exception))
        self.assertEqual(list(self.d.iterdir()), [])

    def test_nicht_verbunden_und_knopf(self):
        with self.assertRaises(kanaele.NichtEingerichtet):
            kanaele.tiktok_posten({}, LOGO, "a")
        self.assertTrue(kanaele.verfuegbar(G)["tiktok"])
        alle = [k["callback_data"] for z in telegram.knoepfe("b1")["inline_keyboard"] for k in z]
        self.assertIn("p|tt|b1", alle)


if __name__ == "__main__":
    unittest.main()
