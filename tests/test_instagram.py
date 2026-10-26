"""Instagram: Bild als JPEG in den oeffentlichen Ordner, Container -> Status -> Veroeffentlichen, danach aufraeumen."""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from social import kanaele, telegram

HIER = Path(__file__).resolve().parent.parent
LOGO = HIER / "assets/logo-1080.png"


class Antwort:
    def __init__(self, j, code=200):
        self._j, self.status_code, self.content, self.text = j, code, b"x", str(j)

    def json(self):
        return self._j


class InstagramTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.alt = kanaele.IG_ORDNER
        kanaele.IG_ORDNER = self.d

    def tearDown(self):
        kanaele.IG_ORDNER = self.alt
        shutil.rmtree(self.d)

    def test_nicht_eingerichtet(self):
        with self.assertRaises(kanaele.NichtEingerichtet):
            kanaele.instagram_posten({}, LOGO, "x")
        self.assertFalse(kanaele.verfuegbar({})["instagram"])
        self.assertTrue(kanaele.verfuegbar({"instagram_token": "t"})["instagram"])

    def test_ablauf_und_aufraeumen(self):
        aufrufe = []
        gesehen = {}

        def anfrage(methode, url, params=None, data=None, timeout=None):
            p = params or data
            aufrufe.append((methode, url.rsplit("/", 1)[-1], dict(p)))
            if url.endswith("/me"):
                return Antwort({"user_id": "17841", "username": "whalesqueeze"})
            if url.endswith("/media"):
                gesehen["datei"] = list(self.d.glob("*.jpg"))   # Bild liegt waehrend des Abholens bereit
                return Antwort({"id": "C1"})
            if url.endswith("/C1"):
                return Antwort({"status_code": "FINISHED"})
            if url.endswith("/media_publish"):
                return Antwort({"id": "M1"})
            if url.endswith("/M1"):
                return Antwort({"permalink": "https://www.instagram.com/p/abc/"})
            return Antwort({"error": {"message": "unbekannt"}}, 400)

        tg = "📊 <b>Krypto-Markt</b>\n\n• BTC: +1,2 %\n🔗 <a href=\"https://whalesqueeze.com/?utm_source=telegram&amp;a=1\">Mehr Daten: whalesqueeze.com</a>\n\n<i>Keine Anlageberatung.</i>"
        with mock.patch.object(kanaele.requests, "request", side_effect=anfrage):
            link = kanaele.instagram_posten({"instagram_token": "geheim"}, LOGO, tg, warten=lambda s: None,
                                            pruefen_url=lambda u: 200)
        self.assertEqual(link, "https://www.instagram.com/p/abc/")
        self.assertEqual([a[1] for a in aufrufe], ["me", "media", "C1", "media_publish", "M1"])
        media = aufrufe[1][2]
        self.assertTrue(media["image_url"].startswith("https://whalesqueeze.com/medien/"))
        self.assertTrue(media["image_url"].endswith(".jpg"))
        self.assertNotIn("<b>", media["caption"])
        self.assertNotIn("utm_source", media["caption"])
        self.assertIn("link in bio", media["caption"])
        self.assertIn("Keine Anlageberatung.", media["caption"])   # Text des Beitrags bleibt, wie er ist
        self.assertEqual(len(gesehen["datei"]), 1)
        self.assertEqual(list(self.d.iterdir()), [])     # danach geloescht

    def test_ordner_nicht_oeffentlich(self):
        with self.assertRaises(kanaele.NichtEingerichtet) as e:
            kanaele.instagram_posten({"instagram_token": "t"}, LOGO, "x", pruefen_url=lambda u: 401)
        self.assertIn("/medien/", str(e.exception))
        self.assertEqual(list(self.d.iterdir()), [])

    def test_fehler_wird_gemeldet(self):
        with mock.patch.object(kanaele.requests, "request",
                               return_value=Antwort({"error": {"message": "Invalid OAuth access token"}}, 400)):
            with self.assertRaises(RuntimeError) as e:
                kanaele.instagram_posten({"instagram_token": "t"}, LOGO, "x", pruefen_url=lambda u: 200)
        self.assertIn("Invalid OAuth", str(e.exception))
        self.assertEqual(list(self.d.iterdir()), [])

    def test_unterschrift_laenge(self):
        t = kanaele.instagram_text("a" * 5000)
        self.assertLessEqual(len(t), kanaele.IG_MAX)
        self.assertTrue(t.endswith(kanaele.IG_TAGS["en"]))

    def test_knopf(self):
        alle = [k["callback_data"] for z in telegram.knoepfe("b1")["inline_keyboard"] for k in z]
        self.assertIn("p|ig|b1", alle)


class TokenTest(unittest.TestCase):
    def test_verlaengern_und_fehler(self):
        alt = os.environ.get("SOCIAL_GEHEIM")
        self.addCleanup(lambda: os.environ.__setitem__("SOCIAL_GEHEIM", alt) if alt else os.environ.pop("SOCIAL_GEHEIM", None))
        with tempfile.TemporaryDirectory() as d:
            os.environ["SOCIAL_GEHEIM"] = d
            (Path(d) / "secrets.yaml").write_text(yaml.safe_dump({"instagram_token": "alt", "x": 1}))
            spec = importlib.util.spec_from_file_location("igtok", HIER / "tools/instagram_token.py")
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            self.assertEqual(m.main(erneuern=lambda t: ("neu", 5184000), melden=lambda g, t: None), 0)
            g = yaml.safe_load((Path(d) / "secrets.yaml").read_text())
            self.assertEqual((g["instagram_token"], g["x"]), ("neu", 1))
            meldung = []

            def kaputt(t):
                raise RuntimeError("expired")
            self.assertEqual(m.main(erneuern=kaputt, melden=lambda g, t: meldung.append(t)), 1)
            self.assertIn("expired", meldung[0])


if __name__ == "__main__":
    unittest.main()
