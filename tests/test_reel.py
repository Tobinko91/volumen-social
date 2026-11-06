"""Reel aus dem Redaktions-Chat: Server spricht den Text, zeichnet den echten Chart, schneidet das Video."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from PIL import Image

from social import reel

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


def _kerzen(n=48):
    return [{"t": 1_762_214_400_000 + i * 900_000, "o": 76000 + i * 10, "h": 76100 + i * 10, "l": 75900 + i * 10,
             "c": 76050 + i * 10, "v": 1.0} for i in range(n)]


class ReelTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp()) / "chat_20261104-midterms-3-reel"
        self.o.mkdir(parents=True)
        for i in range(2):
            Image.new("RGB", (1080, 1920), (20, 15, 46)).save(self.o / f"szene_{i}.png")
        (self.o / "reel.json").write_text(json.dumps({"thema": "midterms-3", "szenen": [
            {"bild": "szene_0.png", "text": "Bitcoin dipped.",
             "chart": {"base": "BTC", "intervall": "15m", "anzahl": 48, "box": [60, 700, 1020, 1500]}},
            {"bild": "szene_1.png", "text": "Then it bounced."}]}))
        self.gesehen = {}

    def tearDown(self):
        shutil.rmtree(self.o.parent)

    def _sprechen(self, zeilen, ordner, cfg, key):
        self.gesehen["zeilen"], self.gesehen["key"] = zeilen, key
        return [Path("a.mp3"), Path("b.mp3")], [2.5, 2.5], "elevenlabs"

    def _schneiden(self, bilder, toene, dauern, ziel, cfg, texte=None):
        self.gesehen["bilder"], self.gesehen["texte"] = bilder, texte
        ziel.write_bytes(b"mp4")
        return ziel

    def test_chart_stimme_video(self):
        q = reel.bauen(self.o, CFG, {"elevenlabs_api_key": "k"}, kerzen_holen=lambda b, i, n: _kerzen(n),
                       sprechen=self._sprechen, schneiden=self._schneiden)
        self.assertTrue(q.startswith("elevenlabs; Chart BTC:"))
        self.assertEqual(self.gesehen["zeilen"], ["Bitcoin dipped.", "Then it bounced."])
        self.assertEqual(self.gesehen["key"], "k")
        self.assertEqual(self.gesehen["bilder"][0].name, "chart_szene_0.png")   # echter Chart eingezeichnet
        self.assertEqual(self.gesehen["bilder"][1].name, "szene_1.png")
        self.assertEqual(Image.open(self.gesehen["bilder"][0]).size, (1080, 1920))
        self.assertTrue((self.o / "video.mp4").exists())
        self.assertEqual(self.gesehen["texte"], ["Bitcoin dipped.", "Then it bounced."])   # Untertitel

    def test_ohne_kurse_trotzdem_video(self):
        q = reel.bauen(self.o, CFG, {}, kerzen_holen=lambda b, i, n: [], sprechen=self._sprechen,
                       schneiden=self._schneiden)
        self.assertIn("Chart fehlt", q)
        self.assertEqual(self.gesehen["bilder"][0].name, "szene_0.png")

    def test_eingang_baut_reel_vor_dem_senden(self):
        sys.path.insert(0, str(HIER / "tools"))
        import eingang
        tmp = self.o.parent
        ein = tmp / "eingang" / "20261104-midterms-3-reel"
        shutil.copytree(self.o, ein)
        Image.new("RGB", (1080, 1350)).save(ein / "post.png")
        (ein / "post_x.txt").write_text("X\nNot financial advice.")
        (ein / "post_telegram.txt").write_text("T\n\n<i>Not financial advice.</i>")
        gesendet = []
        with mock.patch.object(eingang, "EINGANG", tmp / "eingang"), mock.patch.object(eingang, "AUSGABE", tmp), \
                mock.patch.object(eingang, "BASIS", tmp), \
                mock.patch.object(reel, "bauen", lambda z, c, g: (z / "video.mp4").write_bytes(b"v") and "elevenlabs"), \
                mock.patch.object(eingang.telegram, "vorschlag_senden",
                                  lambda g, z, h: gesendet.append((z, h, (z / "video.mp4").exists())) or True):
            eingang.main()
        self.assertEqual(len(gesendet), 1)
        self.assertTrue(gesendet[0][2])
        self.assertIn("🎙 Ton: elevenlabs", gesendet[0][1])


class ChartZahlTest(unittest.TestCase):
    """05.11.2026 Tobias: Ein Chart ohne Zahl sagt nichts -> Veraenderung seit Ereignis in den Sprechtext."""
    def test_prozent_seit_ereignis(self):
        o = Path(tempfile.mkdtemp())
        try:
            Image.new("RGB", (1080, 1920)).save(o / "s.png")
            (o / "reel.json").write_text(json.dumps({"thema": "t", "szenen": [
                {"bild": "s.png", "text": "Bitcoin is {chg} since the Senate call, now {bis}.",
                 "text_ohne": "Here is Bitcoin since the Senate call.",
                 "chart": {"base": "BTC", "intervall": "1h", "anzahl": 60, "box": [60, 700, 1020, 1500],
                           "ab_ts": 1_000_000, "ab_text": "the call"}}]}))
            k = [{"t": (1_000_000 + i * 3600) * 1000, "o": 100 + i, "h": 102 + i, "l": 99 + i, "c": 101 + i, "v": 1}
                 for i in range(-10, 40)]
            gesehen = {}

            def sp(z, o_, c, key):
                gesehen["z"] = z
                return [Path("a.mp3")], [3.0], "elevenlabs"
            q = reel.bauen(o, CFG, {}, kerzen_holen=lambda b, i, n: k, sprechen=sp,
                           schneiden=lambda *a, **kw: None)
            self.assertEqual(gesehen["z"], ["Bitcoin is +41.4% since the Senate call, now $140."])
            self.assertIn("Chart BTC: +41.4%", q)
            reel.bauen(o, CFG, {}, kerzen_holen=lambda b, i, n: [], sprechen=sp, schneiden=lambda *a, **kw: None)
            self.assertEqual(gesehen["z"], ["Here is Bitcoin since the Senate call."])
            spec = json.loads((o / "reel.json").read_text())
            spec["szenen"][0]["chart"]["zahl_ab_ereignis"] = True   # Zahl erst ab Ereignis (Open 100), nicht 1h davor
            (o / "reel.json").write_text(json.dumps(spec))
            reel.bauen(o, CFG, {}, kerzen_holen=lambda b, i, n: k, sprechen=sp, schneiden=lambda *a, **kw: None)
            self.assertEqual(gesehen["z"], ["Bitcoin is +40.0% since the Senate call, now $140."])
        finally:
            shutil.rmtree(o)


class UntertitelTest(unittest.TestCase):
    def test_stuecke_und_zeiten(self):
        from social import video
        self.assertEqual(video.stuecke("Election night. Bitcoin slid to a seven-week low."),
                         ["Election night.", "Bitcoin slid to", "a seven-week low."])
        with tempfile.TemporaryDirectory() as d:
            ut = video.untertitel("Election night. Bitcoin slid to a seven-week low.", 4.0, Path(d), 0, CFG)
            self.assertEqual(len(ut), 8)                      # ein Bild je Wort (aktives Wort hervorgehoben)
            self.assertEqual((ut[0][1], ut[-1][2]), (0.0, 4.0))
            self.assertTrue(all(a < e for _, a, e in ut))
            self.assertTrue(all(ut[k][2] == ut[k + 1][1] for k in range(7)))   # lueckenlos
            self.assertEqual(Image.open(ut[0][0]).size, (1080, 1920))

    def test_echte_zeitmarken(self):
        from social import stimme, video
        al = {"characters": list("Hi there."), "character_start_times_seconds": [0, .1, .2, .3, .4, .5, .6, .7, .8],
              "character_end_times_seconds": [.1, .2, .3, .4, .5, .6, .7, .8, .9]}
        w = stimme.woerter_aus_ausrichtung(al)
        self.assertEqual(w, [{"w": "Hi", "a": 0, "e": 0.2}, {"w": "there.", "a": 0.3, "e": 0.9}])
        with tempfile.TemporaryDirectory() as d:
            ut = video.untertitel("Hi there.", 1.5, Path(d), 0, CFG, w, y=1310)
        self.assertEqual([(a, e) for _, a, e in ut], [(0.0, 0.3), (0.3, 1.5)])

    def test_elevenlabs_speichert_marken(self):
        import base64
        from social import stimme

        class R:
            status_code = 200

            def json(self):
                return {"audio_base64": base64.b64encode(b"mp3").decode(),
                        "alignment": {"characters": list("Go"), "character_start_times_seconds": [0, .1],
                                      "character_end_times_seconds": [.1, .2]}}
        cfg = {"stimme": {"voice_id": "v1", "modell": "eleven_flash_v2_5"}}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(stimme.requests, "post", return_value=R()) as p:
            stimme._elevenlabs("Go", Path(d) / "a.mp3", cfg, "k")
            self.assertIn("with-timestamps", p.call_args[0][0])
            self.assertEqual((Path(d) / "a.mp3").read_bytes(), b"mp3")
            self.assertEqual(json.loads((Path(d) / "a.json").read_text()), [{"w": "Go", "a": 0, "e": 0.2}])

    def test_formate_ohne_satzkasten(self):
        from social import video
        self.assertEqual(video.ut_formate(CFG, ["a"]), {"texte": ["a"], "untertitel_y": 1230})
        self.assertEqual(video.ut_formate({"video": {}}, ["a"]), {})


class ReelAusBildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.o = self.tmp / "20261104-1430_markt_30s"
        self.o.mkdir()
        Image.new("RGB", (1080, 1350), (40, 30, 80)).save(self.o / "post.png")
        (self.o / "post_x.txt").write_text("📊 Market check\n$ZK whales +6.0 pp · BTC $75,740\n#crypto https://t.me/x\n"
                                           "Not financial advice.")
        (self.o / "post_telegram.txt").write_text("<b>T</b>\n\n<i>Not financial advice.</i>")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_sprechtext(self):
        z = reel.sprechtext((self.o / "post_x.txt").read_text())
        self.assertEqual(z, ["Market check.", "ZK whales +6.0 pp, BTC $75,740.", "Not financial advice."])

    def test_aus_bild(self):
        gesehen = {}

        def sprechen(zeilen, ordner, cfg, key):
            gesehen["n"] = len(zeilen)
            return [Path(f"{i}.mp3") for i in range(len(zeilen))], [3.0] * len(zeilen), "elevenlabs"

        def schneiden(bilder, toene, dauern, ziel, cfg, texte=None):
            gesehen["n_texte"] = len(texte)
            gesehen["groesse"] = Image.open(bilder[0]).size
            ziel.write_bytes(b"v")
        neu, q = reel.aus_bild(self.o, CFG, {}, sprechen=sprechen, schneiden=schneiden)
        self.assertEqual((neu.name, q), ("20261104-1430_markt_30s_video", "elevenlabs"))
        self.assertEqual(gesehen, {"n": 3, "n_texte": 3, "groesse": (1080, 1920)})
        from social.bericht import format_aus_ordner
        self.assertEqual(format_aus_ordner(neu.name), "markt_video")
        self.assertEqual(reel.aus_bild(self.o, CFG, {})[1], "schon gebaut")

    def test_knopf_nur_bei_bildern_und_freigabe(self):
        from social import telegram
        alle = lambda r: [k["callback_data"] for z in telegram.knoepfe("b1", reel=r)["inline_keyboard"] for k in z]
        self.assertIn("p|reel|b1", alle(True))
        self.assertNotIn("p|reel|b1", alle(False))
        sys.path.insert(0, str(HIER / "tools"))
        import freigabe
        with mock.patch.object(freigabe, "AUSGABE", self.tmp), \
                mock.patch.object(reel, "aus_bild", lambda o, c, g: (o.parent / (o.name + "_video"), "elevenlabs")), \
                mock.patch.object(telegram, "vorschlag_senden", lambda g, o, h: True):
            self.assertIn("Reel gebaut", freigabe.posten({}, self.o.name, "reel"))
            (self.o / "video.mp4").write_bytes(b"v")
            self.assertIn("schon ein Video", freigabe.posten({}, self.o.name, "reel"))


if __name__ == "__main__":
    unittest.main()


class AbkuerzungTest(unittest.TestCase):
    """06.11.2026 Tobias (ALLO-Reel): Tilde, × und M/B/T klar sprechen (Millionen oder Milliarden?)."""

    def test_sprechen(self):
        from social import stimme
        self.assertEqual(stimme.sprech_wort("~160M"), ["about", "160", "million"])
        self.assertEqual(stimme.sprech_wort("~17×"), ["about", "17", "times"])
        self.assertEqual(stimme.sprech_wort("$9.3M"), ["9.3", "million", "dollars"])
        self.assertEqual(stimme.sprech_wort("$1.2T."), ["1.2", "trillion", "dollars."])
        self.assertEqual(stimme.sprech_wort("-2.5B"), ["minus", "2.5", "billion"])
        self.assertEqual(stimme.sprech_wort("~$13.52"), ["about", "14", "dollars"])   # nur ein „about“
        self.assertEqual(stimme.sprech_wort("2026"), ["2026"])
        text, laengen = stimme.sprechbar("~160M tokens, ~17× the last unlocks")
        self.assertEqual(text, "about 160 million tokens, about 17 times the last unlocks")
        self.assertEqual(sum(laengen), len(text.split()))   # Zeitmarken passen weiter zu den Untertiteln

    def test_mal_zeichen_bleibt_im_sprechtext(self):
        self.assertEqual(reel.sprechtext("~160M tokens, ~17× the last unlocks"),
                         ["~160M tokens, ~17x the last unlocks."])
