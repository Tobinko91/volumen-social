"""S31 zeitversetzt posten: Fenster, Aufteilung, geplante Posts nachholen, Verwerfen stoppt."""
import datetime as dt
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from social import zeitplan

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
B = zeitplan.BERLIN


def ts(h, m=0, tag=2):
    return dt.datetime(2026, 11, tag, h, m, tzinfo=B).timestamp()


class ZeitplanTest(unittest.TestCase):
    def test_fenster(self):
        self.assertEqual(zeitplan.faellig("18:00", ts(14, 30)), ts(18))          # vorher: warten
        self.assertEqual(zeitplan.faellig("18:00", ts(20, 15)), ts(20, 15))      # drin: sofort
        self.assertEqual(zeitplan.faellig("18:00", ts(0, 10, 3)), ts(18, 0, 3))  # nach Mitternacht: heute 18 Uhr

    def test_aufteilen_routine(self):
        ziele = ["telegram", "x", "instagram", "tiktok"]
        sofort, spaeter = zeitplan.aufteilen(ziele, "markt_video", False, CFG, ts(14, 31))
        self.assertEqual(sofort, ["telegram", "x"])
        self.assertEqual(spaeter, {"instagram": ts(18), "tiktok": ts(19)})

    def test_bild_ohne_tiktok_news_sofort(self):
        ziele = ["telegram", "x", "instagram", "tiktok"]
        sofort, spaeter = zeitplan.aufteilen(ziele, "markt", True, CFG, ts(14, 31))
        self.assertNotIn("tiktok", sofort + list(spaeter))
        self.assertEqual(zeitplan.aufteilen(ziele, "news", False, CFG, ts(14, 31)), (ziele, {}))
        self.assertEqual(zeitplan.aufteilen(ziele, "redaktion", False, CFG, ts(9))[1], {})

    def test_aus(self):
        cfg = dict(CFG, zeitplan={"aktiv": False})
        self.assertEqual(zeitplan.aufteilen(["instagram"], "wal", True, cfg, ts(9)), (["instagram"], {}))


class FreigabeGeplantTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(HIER / "tools"))
        import freigabe
        import geplant
        self.f, self.gp = freigabe, geplant
        self.tmp = Path(tempfile.mkdtemp())
        self.o = self.tmp / "20261102-1430_markt_30s_video"
        self.o.mkdir()
        (self.o / "video.mp4").write_bytes(b"x")
        (self.o / "post_telegram.txt").write_text("T\n\nNot financial advice.")
        (self.o / "post_x.txt").write_text("T")
        self.gerufen = []
        poster = {z: (lambda z: lambda g, m, t: self.gerufen.append(z) or "ok")(z)
                  for z in ("telegram", "x", "instagram", "tiktok", "youtube")}
        from social import kanaele, video_posten
        self.patches = [mock.patch.object(freigabe, "AUSGABE", self.tmp),
                        mock.patch.object(freigabe, "PROTOKOLL", self.tmp / "p.jsonl"),
                        mock.patch.object(freigabe, "PAUSE", self.tmp / ".pause"),
                        mock.patch.object(video_posten, "POSTER", poster),
                        mock.patch.object(kanaele, "_cfg", return_value=dict(CFG, instagram={"story": False})),
                        mock.patch.object(freigabe, "geheim", return_value={})]
        for p in self.patches:
            p.start()
        self.g = {"telegram_token": "t", "telegram_kanal": "@w", "instagram_token": "i",
                  **{k: "v" for k in ("tiktok_client_key", "tiktok_client_secret", "tiktok_refresh_token")}}

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp)

    def test_alle_plant_und_holt_nach(self):
        with mock.patch.object(self.f.time, "time", return_value=ts(14, 31)):
            antwort = self.f.posten(self.g, self.o.name, "alle")
        self.assertEqual(self.gerufen, ["telegram", "x"])
        self.assertIn("⏰ instagram: geplant um 18:00", antwort)
        self.assertEqual(self.gp.main(jetzt=ts(17), senden=False), [])          # noch nicht faellig
        self.gp.main(jetzt=ts(18, 2), senden=False)
        self.assertEqual(self.gerufen, ["telegram", "x", "instagram"])
        self.gp.main(jetzt=ts(19, 2), senden=False)
        self.gp.main(jetzt=ts(19, 12), senden=False)                            # nicht doppelt
        self.assertEqual(self.gerufen, ["telegram", "x", "instagram", "tiktok"])

    def test_verwerfen_stoppt_geplantes(self):
        with mock.patch.object(self.f.time, "time", return_value=ts(14, 31)):
            self.f.posten(self.g, self.o.name, "alle")
        self.f.posten(self.g, self.o.name, "nein")
        self.assertEqual(self.gp.main(jetzt=ts(23), senden=False), [])
        st = json.loads((self.o / "gepostet.json").read_text())
        self.assertIn("instagram", st["geplant"])


if __name__ == "__main__":
    unittest.main()
