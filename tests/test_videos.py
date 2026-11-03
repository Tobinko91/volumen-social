"""Videos (Wunsch Tobias 01.11.2026): Musik ohne Stimme, Video-Vorschlag, Reels/TikTok/X/Telegram posten."""
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from social import kanaele, musik, tiktok, video_posten

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
G = {"telegram_token": "t", "telegram_kanal": "@whalesqueeze", "x_api_key": "a", "x_api_secret": "b",
     "x_access_token": "c", "x_access_secret": "d", "instagram_token": "ig", "instagram_user_id": "17",
     "tiktok_client_key": "ck", "tiktok_client_secret": "cs", "tiktok_refresh_token": "rt",
     "tiktok_access_token": "at", "tiktok_bis": time.time() + 3600}
TG = "📊 <b>Crypto market</b>\n\n• BTC +1.2%\n\n<i>Not financial advice.</i>"


class Antwort:
    def __init__(self, j, code=200):
        self._j, self.status_code, self.content, self.text = j, code, b"x", json.dumps(j)

    def json(self):
        return self._j


class MusikTest(unittest.TestCase):
    def test_musik_einstellungen(self):
        self.assertEqual(CFG["video"]["musik"], "/opt/volumen-social/musik")   # 02.11.: eigene Stuecke statt erzeugt
        self.assertEqual(CFG["stimme"]["anbieter"], "openai")   # 03.11.: Stimme per OpenAI
        self.assertIsNone(musik.pfad({"video": {"musik": None}}, Path("/tmp")))
        self.assertIsNone(musik.pfad({"video": {"musik": "/gibt/es/nicht.mp3"}}, Path("/tmp")))

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg fehlt")
    def test_musik_ordner_wechselt_taeglich(self):
        with tempfile.TemporaryDirectory() as d:
            o = Path(d)
            self.assertIsNone(musik.pfad({"video": {"musik": str(o)}}, o))   # leer = ohne Musik
            for n in ("a.mp3", "b.m4a", "notiz.txt"):
                (o / n).write_bytes(b"x")
            c = {"video": {"musik": str(o)}}
            self.assertEqual({musik.pfad(c, o, 0).name, musik.pfad(c, o, 1).name}, {"a.mp3", "b.m4a"})

    def test_bot_speichert_musik(self):
        import sys
        from unittest import mock
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
        import freigabe

        class R:
            content = b"ID3"

            def raise_for_status(self):
                pass
        with tempfile.TemporaryDirectory() as d, mock.patch.object(freigabe, "MUSIK", Path(d) / "musik"), \
                mock.patch.object(freigabe, "tg", return_value={"ok": True, "result": {"file_path": "music/f.mp3"}}):
            m = {"audio": {"file_id": "x", "file_name": "Tech Ambient (Velario).mp3", "mime_type": "audio/mpeg"}}
            antwort = freigabe.musik_speichern({"telegram_token": "t"}, m, holen=lambda url, timeout=None: R())
            self.assertIn("Tech_Ambient_Velario_.mp3", antwort)
            self.assertTrue((Path(d) / "musik" / "Tech_Ambient_Velario_.mp3").exists())
            self.assertIn("keine Audiodatei", freigabe.musik_speichern({}, {"document": {"file_name": "a.pdf"}}))
            self.assertIn("1 Stücke", freigabe.befehl({}, "/musik"))

    def test_musik_wird_erzeugt_und_wiederverwendet(self):
        with tempfile.TemporaryDirectory() as d:
            p = musik.erzeugen(Path(d) / "m.m4a", 6)
            self.assertGreater(p.stat().st_size, 10_000)
            t = p.stat().st_mtime
            musik.erzeugen(p, 6)
            self.assertEqual(p.stat().st_mtime, t)
            out = subprocess.run(["ffmpeg", "-i", str(p), "-af", "volumedetect", "-f", "null", "-"],
                                 capture_output=True, text=True).stderr
            mittel = float(out.split("mean_volume:")[1].split("dB")[0])
            self.assertGreater(mittel, -30)   # hoerbar, nicht nur Rauschen


class PostenTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.alt = video_posten.IG_ORDNER
        video_posten.IG_ORDNER = self.d / "oeffentlich"
        self.video = self.d / "video.mp4"
        self.video.write_bytes(b"\x00" * (5 * 1024 * 1024))   # 5 MB -> 2 Teile beim X-Upload

    def tearDown(self):
        video_posten.IG_ORDNER = self.alt
        shutil.rmtree(self.d)

    def test_telegram(self):
        gesehen = []

        def post(url, data=None, files=None, timeout=None):
            gesehen.append((url.rsplit("/", 1)[-1], data))
            return Antwort({"ok": True, "result": {"message_id": 42}})
        self.assertEqual(video_posten.telegram(G, self.video, TG, post=post), "https://t.me/whalesqueeze/42")
        self.assertEqual(gesehen[0][0], "sendVideo")
        self.assertEqual(gesehen[0][1]["chat_id"], "@whalesqueeze")

    def test_x_in_teilen(self):
        aufrufe = []

        def anfrage(methode, url, headers=None, timeout=None, **kw):
            aufrufe.append((methode, url, kw))
            self.assertTrue(headers["Authorization"].startswith("OAuth "))
            if url.endswith("/initialize"):
                self.assertEqual(kw["json"]["media_category"], "tweet_video")
                return Antwort({"data": {"id": "m1"}})
            if url.endswith("/append"):
                return Antwort({}, 204)
            if url.endswith("/finalize"):
                return Antwort({"data": {"id": "m1", "processing_info": {"state": "pending", "check_after_secs": 1}}})
            if "command=STATUS" in url:
                return Antwort({"data": {"processing_info": {"state": "succeeded"}}})
            if url.endswith("/2/tweets"):
                self.assertEqual(kw["json"]["media"]["media_ids"], ["m1"])
                return Antwort({"data": {"id": "77"}})
            return Antwort({}, 404)
        link = video_posten.x(G, self.video, "Text\nNot financial advice.", anfrage=anfrage, warten=lambda s: None)
        self.assertEqual(link, "https://x.com/i/web/status/77")
        teile = [kw["data"]["segment_index"] for m, u, kw in aufrufe if u.endswith("/append")]
        self.assertEqual(teile, ["0", "1"])
        q = parse_qs(urlparse(next(u for m, u, kw in aufrufe if "STATUS" in u)).query)
        self.assertEqual(q["media_id"], ["m1"])

    def test_instagram_reel(self):
        gesehen = []
        stati = iter(["IN_PROGRESS", "FINISHED"])

        def ig(methode, pfad, token, **params):
            gesehen.append((methode, pfad, params))
            if pfad.endswith("/media"):
                self.datei = list(video_posten.IG_ORDNER.glob("*.mp4"))
                return {"id": "c1"}
            if pfad == "c1":
                return {"status_code": next(stati)}
            if pfad.endswith("/media_publish"):
                return {"id": "m9"}
            return {"permalink": "https://www.instagram.com/reel/abc/"}
        alt = kanaele._ig
        kanaele._ig = ig
        try:
            link = video_posten.instagram(G, self.video, TG, warten=lambda s: None, pruefen_url=lambda u: 200)
        finally:
            kanaele._ig = alt
        self.assertEqual(link, "https://www.instagram.com/reel/abc/")
        p = next(x for m, pf, x in gesehen if pf.endswith("/media"))
        self.assertEqual((p["media_type"], p["share_to_feed"]), ("REELS", "true"))
        self.assertTrue(p["video_url"].startswith("https://whalesqueeze.com/medien/") and p["video_url"].endswith(".mp4"))
        self.assertEqual(len(self.datei), 1)
        self.assertEqual(list(video_posten.IG_ORDNER.iterdir()), [])   # danach geloescht

    def test_tiktok_entwurf_und_direkt(self):
        aufrufe = []

        def post(url, data=None, json=None, headers=None, timeout=None):
            aufrufe.append((url.split("/v2/")[-1], json))
            if url.endswith("creator_info/query/"):
                return Antwort({"data": {"privacy_level_options": ["SELF_ONLY"]}, "error": {"code": "ok"}})
            if url.endswith("video/init/"):
                return Antwort({"data": {"publish_id": "p1"}, "error": {"code": "ok"}})
            if url.endswith("status/fetch/"):
                st = "SEND_TO_USER_INBOX" if any("inbox" in a for a, _ in aufrufe) else "PUBLISH_COMPLETE"
                return Antwort({"data": {"status": st}, "error": {"code": "ok"}})
            return Antwort({"error": {"code": "invalid_param"}}, 400)
        m = video_posten.tiktok(dict(G), self.video, TG, pruefen_url=lambda u: 200, post=post, warten=lambda s: None)
        init = next(j for a, j in aufrufe if a.endswith("inbox/video/init/"))
        self.assertEqual(init["source_info"]["source"], "PULL_FROM_URL")
        self.assertTrue(init["source_info"]["video_url"].endswith(".mp4"))
        self.assertIn("Video-Entwurf", m)
        self.assertIn("nächsten Nachricht", m)   # Text kommt als eigene Kopier-Nachricht (freigabe.py)
        aufrufe.clear()
        m = tiktok.video_posten(dict(G), "https://whalesqueeze.com/medien/x.mp4", TG, modus="direkt", post=post,
                                warten=lambda s: None)
        init = next(j for a, j in aufrufe if a == "post/publish/video/init/")
        self.assertEqual(init["post_info"]["privacy_level"], "SELF_ONLY")
        self.assertIn("privat", m)


class ProzentTest(unittest.TestCase):
    def test_claude_text_bekommt_zeichen(self):
        from social import texte
        self.assertEqual(texte.prozent_zeichen("ESPORTS jumped 113.7 percent in 24 hours.", "en"),
                         "ESPORTS jumped 113.7% in 24 hours.")
        self.assertEqual(texte.prozent_zeichen("Half did better than plus 6.9 percent, BTC minus 1.2 percent.", "en"),
                         "Half did better than +6.9%, BTC -1.2%.")
        self.assertEqual(texte.prozent_zeichen("BAT liegt 52,8 Prozent höher.", "de"), "BAT liegt 52,8 % höher.")
        self.assertIn('never the word "percent"', texte.SYSTEM["en"])


class VorschlagTest(unittest.TestCase):
    def test_freigabe_nimmt_video_poster(self):
        import os
        import sys
        import importlib
        with tempfile.TemporaryDirectory() as d:
            os.environ["SOCIAL_AUSGABE"] = d
            try:
                sys.path.insert(0, str(HIER / "tools"))
                import freigabe
                importlib.reload(freigabe)
                o = Path(d) / "20261101-1430_markt_30s_video"
                o.mkdir()
                (o / "video.mp4").write_bytes(b"v")
                (o / "post_telegram.txt").write_text(TG)
                (o / "post_x.txt").write_text("x")
                gesehen = []
                nachrichten = []
                freigabe.tg = lambda g, methode, **d: nachrichten.append(d)
                alt = dict(video_posten.POSTER)
                video_posten.POSTER["telegram"] = lambda g, m, t: gesehen.append(m.name) or "ok"
                try:
                    r = freigabe.posten({}, o.name, "tg")
                finally:
                    video_posten.POSTER.update(alt)
                self.assertEqual(gesehen, ["video.mp4"])
                self.assertIn("✅ telegram: ok", r)
                # TikTok-Entwurf: Text kommt als eigene Nachricht zum Antippen
                video_posten.POSTER["tiktok"] = lambda g, m, t: "Video-Entwurf in der TikTok-App: …"
                try:
                    freigabe.posten({"telegram_chat_id": 1}, o.name, "tt")
                finally:
                    video_posten.POSTER.update(alt)
                self.assertTrue(nachrichten and nachrichten[-1]["text"].startswith("🎵 TikTok-Text"))
                self.assertIn("<code>", nachrichten[-1]["text"])
                self.assertIn("#crypto", nachrichten[-1]["text"])
            finally:
                os.environ.pop("SOCIAL_AUSGABE")


if __name__ == "__main__":
    unittest.main()
