"""S11 Wal-Karussell: Auswahl der Wale, Folien, Texte, Posten auf Instagram/TikTok/X/Telegram, Freigabe."""
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import yaml

from social import daten, kanaele, karussell, karussell_posten, pruefung
from social.bericht import format_aus_ordner

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


def _daten(werte: dict) -> daten.Daten:
    d = daten.laden(HIER / "beispieldaten")
    for i, (b, w) in enumerate(werte.items()):
        c = d.coins.setdefault(b, {})
        c.update({"mcap": 50e6, "wale_7d": {"wal": w, "boerse": -0.5}, "wale": {"wal": 40.0 + i, "boerse": 10.0},
                  "holder": 12000, "holder_7d": 1.2, "chg24": 3.0})
    for b in list(d.coins):
        if b not in werte:
            d.coins[b].pop("wale_7d", None)
    return d


class Antwort:
    def __init__(self, j, code=200):
        self._j, self.status_code, self.text, self.content, self.ok = j, code, json.dumps(j), b"x", code < 300

    def json(self):
        return self._j


class AuswahlTest(unittest.TestCase):
    def test_groesste_bewegung_beider_richtungen_ohne_sperrliste(self):
        d = _daten({"BAT": 2.0, "ZK": -6.0, "ALT": 0.5, "OGN": 4.0, "RSR": -1.0, "GTC": 3.0, "MAGIC": 0.0})
        wale = daten.wale_der_woche(d, {"GTC"}, n=4)
        self.assertEqual([w["base"] for w in wale], ["ZK", "OGN", "BAT", "RSR"])
        self.assertTrue(all(w["quelle"] == "7d" for w in wale))

    def test_kleine_coins_raus(self):
        d = _daten({"BAT": 2.0, "ZK": -6.0})
        d.coins["ZK"]["mcap"] = 5e6
        self.assertEqual([w["base"] for w in daten.wale_der_woche(d, set())], ["BAT"])


class FolienTest(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp()) / "20261108-1700_karussell"
        self.wale = daten.wale_der_woche(_daten({"BAT": 2.0, "ZK": -6.0, "OGN": 4.0}), set())

    def tearDown(self):
        shutil.rmtree(self.ordner.parent)

    def test_folien_und_vorschau(self):
        f = karussell.bauen(self.wale, CFG, self.ordner, "en", time.time())
        self.assertEqual(len(f), 5)   # Deckblatt + 3 Wale + Abschluss
        self.assertEqual(karussell.folien(self.ordner), f)
        self.assertEqual((self.ordner / "post.png").read_bytes(), f[0].read_bytes())
        from PIL import Image
        self.assertEqual(Image.open(f[1]).size, (1080, 1350))
        self.assertEqual(format_aus_ordner(self.ordner.name), "karussell")

    def test_texte_bestehen_pruefung(self):
        txt = karussell.texte(self.wale, CFG, "en")
        self.assertLessEqual(len(txt["x"]), 280)
        self.assertIn("$ZK: -6.0 pp", txt["x"])
        self.assertIn("Not financial advice.", txt["telegram"])
        fehler = pruefung.pruefen([txt["x"], txt["telegram"]], {"fakten": karussell.fakten(self.wale), "szenen": [0, 0]},
                                  CFG, set(), erlaubt_fusszeile=True)
        self.assertEqual(fehler, [])


class PostenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ordner = self.tmp / "20261108-1700_karussell"
        wale = daten.wale_der_woche(_daten({"BAT": 2.0, "ZK": -6.0, "OGN": 4.0}), set())
        self.folien = karussell.bauen(wale, CFG, self.ordner, "en", time.time())
        self.alt = kanaele.IG_ORDNER
        kanaele.IG_ORDNER = self.tmp / "oeffentlich"

    def tearDown(self):
        kanaele.IG_ORDNER = self.alt
        shutil.rmtree(self.tmp)

    def test_instagram_karussell(self):
        aufrufe = []

        def ig(methode, pfad, token, **p):
            aufrufe.append((methode, pfad, p))
            if pfad.endswith("/media") and p.get("is_carousel_item"):
                return {"id": f"k{len(aufrufe)}"}
            if pfad.endswith("/media"):
                return {"id": "c1"}
            if pfad == "c1":
                return {"status_code": "FINISHED"}
            if pfad.endswith("media_publish"):
                return {"id": "m1"}
            return {"permalink": "https://instagram.com/p/x"}
        with mock.patch.object(kanaele, "_ig", ig):
            link = karussell_posten.instagram({"instagram_token": "t", "instagram_user_id": "u"},
                                              self.ordner / "post.png", "Text\n\nNot financial advice.",
                                              warten=lambda s: None, pruefen_url=lambda u: 200)
        self.assertEqual(link, "https://instagram.com/p/x")
        kinder = [a for a in aufrufe if a[2].get("is_carousel_item")]
        self.assertEqual(len(kinder), 5)
        haupt = next(a for a in aufrufe if a[2].get("media_type") == "CAROUSEL")
        self.assertEqual(haupt[2]["children"].count(","), 4)
        self.assertEqual(list(kanaele.IG_ORDNER.iterdir()), [])   # oeffentliche Kopien wieder geloescht

    def test_tiktok_fotoserie(self):
        gesehen = {}

        def post(url, data=None, json=None, headers=None, timeout=None):
            if url.endswith("creator_info/query/"):
                return Antwort({"data": {"privacy_level_options": ["SELF_ONLY"]}, "error": {"code": "ok"}})
            if url.endswith("content/init/"):
                gesehen.update(json)
                return Antwort({"data": {"publish_id": "p1"}, "error": {"code": "ok"}})
            return Antwort({"data": {"status": "SEND_TO_USER_INBOX"}, "error": {"code": "ok"}})
        g = {"tiktok_client_key": "ck", "tiktok_client_secret": "cs", "tiktok_refresh_token": "rt",
             "tiktok_access_token": "at", "tiktok_bis": time.time() + 3600}
        karussell_posten.tiktok(g, self.ordner / "post.png", "Text", pruefen_url=lambda u: 200, post=post,
                                warten=lambda s: None)
        self.assertEqual(len(gesehen["source_info"]["photo_images"]), 5)
        self.assertEqual(list(kanaele.IG_ORDNER.iterdir()), [])

    def test_x_hoechstens_vier_bilder(self):
        gesehen = []

        def post(url, headers=None, files=None, data=None, json=None, timeout=None):
            gesehen.append(json)
            return Antwort({"data": {"id": f"{len(gesehen)}"}})
        g = {k: "v" for k in ("x_api_key", "x_api_secret", "x_access_token", "x_access_secret")}
        link = karussell_posten.x(g, self.ordner / "post.png", "Text", post=post)
        self.assertEqual(len(gesehen[-1]["media"]["media_ids"]), 4)
        self.assertIn("x.com", link)

    def test_telegram_album(self):
        gesehen = []

        def post(url, data=None, files=None, timeout=None):
            gesehen.append((url.rsplit("/", 1)[-1], data, sorted(files or {})))
            return Antwort({"ok": True, "result": [{"message_id": 7}]})
        link = karussell_posten.telegram({"telegram_token": "t", "telegram_kanal": "@whalesqueeze"},
                                         self.ordner / "post.png", "<b>Kopf</b>", post=post)
        self.assertEqual(link, "https://t.me/whalesqueeze/7")
        methode, data, dateien = gesehen[0]
        self.assertEqual(methode, "sendMediaGroup")
        self.assertEqual(len(json.loads(data["media"])), 5)
        self.assertEqual(json.loads(data["media"])[0]["caption"], "<b>Kopf</b>")

    def test_youtube_geht_nicht(self):
        with self.assertRaises(kanaele.NichtEingerichtet):
            karussell_posten.youtube({}, self.ordner / "post.png", "x")

    def test_freigabe_waehlt_karussell_poster(self):
        import sys
        sys.path.insert(0, str(HIER / "tools"))
        import freigabe
        aufgerufen = []
        (self.ordner / "post_telegram.txt").write_text("<b>T</b>\n\nNot financial advice.", encoding="utf-8")
        (self.ordner / "post_x.txt").write_text("T", encoding="utf-8")
        poster = dict(karussell_posten.POSTER, telegram=lambda g, m, t: aufgerufen.append(m) or "ok")
        with mock.patch.object(freigabe, "AUSGABE", self.tmp), \
                mock.patch.object(freigabe, "PROTOKOLL", self.tmp / "protokoll.jsonl"), \
                mock.patch.object(karussell_posten, "POSTER", poster):
            antwort = freigabe.posten({}, self.ordner.name, "tg")
            yt = freigabe.posten({}, self.ordner.name, "yt")
        self.assertIn("✅ telegram", antwort)
        self.assertEqual(aufgerufen, [self.ordner / "post.png"])
        self.assertIn("Bilderserie", yt)


if __name__ == "__main__":
    unittest.main()
