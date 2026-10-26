import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from social import kanaele, kurse, telegram

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())


def lade(name):
    spec = importlib.util.spec_from_file_location(name, HIER / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class OAuthTest(unittest.TestCase):
    def test_bekannte_signatur_aus_der_x_doku(self):
        g = {"x_api_key": "xvz1evFS4wEEPTGEFPHBog", "x_api_secret": "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
             "x_access_token": "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
             "x_access_secret": "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"}
        kopf = kanaele.oauth_kopf("POST", "https://api.twitter.com/1.1/statuses/update.json", g,
                                  {"include_entities": "true",
                                   "status": "Hello Ladies + Gentlemen, a signed OAuth request!"},
                                  nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", ts="1318622958")
        self.assertIn('oauth_signature="hCtSmYh%2BiHYCEqBWrE7C7hYmtUk%3D"', kopf)

    def test_ohne_schluessel_nicht_eingerichtet(self):
        with self.assertRaises(kanaele.NichtEingerichtet):
            kanaele.x_posten({}, HIER / "assets/logo-1080.png", "x")
        self.assertEqual(kanaele.verfuegbar({}), {"telegram": False, "x": False, "instagram": False, "tiktok": False})

    def test_knoepfe_passen_in_64_zeichen(self):
        for zeile in telegram.knoepfe("20261022-0730_markt_30s")["inline_keyboard"]:
            for k in zeile:
                self.assertLessEqual(len(k["callback_data"]), 64)


class FreigabeTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.environ["SOCIAL_GEHEIM"] = self.d
        os.environ["SOCIAL_AUSGABE"] = self.d + "/ausgabe"
        self.f = lade("freigabe")
        o = Path(self.d) / "ausgabe" / "b1"
        o.mkdir(parents=True)
        shutil.copy(HIER / "assets/logo-1080.png", o / "post.png")
        (o / "post_x.txt").write_text("x Keine Anlageberatung.")
        (o / "post_telegram.txt").write_text("tg")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_posten_einmal_und_nicht_doppelt(self):
        aufrufe = []
        with mock.patch.dict(self.f.kanaele.POSTER, {"telegram": lambda g, b, t: aufrufe.append(t) or "link1",
                                                     "x": lambda g, b, t: aufrufe.append(t) or "link2"}):
            r1 = self.f.posten({}, "b1", "alle")
            r2 = self.f.posten({}, "b1", "tg")
        self.assertIn("link1", r1)
        self.assertIn("link2", r1)
        self.assertIn("schon gepostet", r2)
        self.assertEqual(len(aufrufe), 2)

    def test_pfad_von_aussen_wird_ignoriert(self):
        self.assertIn("nicht mehr vorhanden", self.f.posten({}, "../../etc", "tg"))

    def test_sperre_und_pause(self):
        self.assertIn("SOL", self.f.befehl({}, "/sperre sol"))
        self.assertNotIn("SOL", self.f.befehl({}, "/entsperre SOL"))
        self.f.befehl({}, "/pause")
        self.assertTrue(self.f.PAUSE.exists())
        self.f.befehl({}, "/weiter")
        self.assertFalse(self.f.PAUSE.exists())


class EingangTest(unittest.TestCase):
    def test_pruefung_aus_dem_chat(self):
        e = lade("eingang")
        with tempfile.TemporaryDirectory() as d:
            o = Path(d)
            shutil.copy(HIER / "assets/logo-1080.png", o / "post.png")
            (o / "post_x.txt").write_text("Jetzt kaufen! " + "a" * 300)
            (o / "post_telegram.txt").write_text("SOL steigt")
            f = e.pruefen(o, CFG, {"SOL"})
            self.assertTrue(any("zu lang" in x for x in f))
            self.assertTrue(any("jetzt kaufen" in x for x in f))
            self.assertTrue(any("Sperrliste" in x for x in f))
            self.assertTrue(any("Risiko-Hinweis" in x for x in f))


class KurseTest(unittest.TestCase):
    def test_bitunix_dann_binance(self):
        def get(url, p):
            if "bitunix" in url:
                raise OSError("weg")
            return [[i * 3600000, "1", "1", "1", str(1 + i / 100)] for i in range(80)]
        v = kurse.verlauf("BAT", get=get)
        self.assertEqual(len(v), 72)
        self.assertAlmostEqual(v[-1][1], 1.79)

    def test_keine_boerse_leer(self):
        self.assertEqual(kurse.verlauf("BAT", get=lambda u, p: (_ for _ in ()).throw(OSError())), [])


if __name__ == "__main__":
    unittest.main()
