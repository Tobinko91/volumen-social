"""YouTube Shorts (Punkt A, 01.11.2026): Login, Token, Upload (bis zur Google-Pruefung privat), Knopf."""
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from social import kanaele, telegram, video_posten, youtube

G = {"youtube_client_id": "cid", "youtube_client_secret": "cs", "youtube_refresh_token": "rt",
     "youtube_access_token": "at", "youtube_bis": time.time() + 3600}
TG = "📊 <b>Crypto market, Nov 1</b>\n\n• BTC +1.2%\n\n<i>Not financial advice.</i>"


class Antwort:
    def __init__(self, j, code=200, headers=None):
        self._j, self.status_code, self.content, self.text = j, code, b"x", json.dumps(j)
        self.headers = headers or {}

    def json(self):
        return self._j


class YouTubeTest(unittest.TestCase):
    def test_login_link_und_code(self):
        q = parse_qs(urlparse(youtube.login_link("cid", "s1")).query)
        self.assertEqual((q["redirect_uri"][0], q["access_type"][0], q["prompt"][0]),
                         ("https://whalesqueeze.com/youtube/", "offline", "consent"))
        self.assertIn("youtube.upload", q["scope"][0])
        self.assertEqual(youtube.code_aus_adresse("https://whalesqueeze.com/youtube/?state=s1&code=4%2FAB", "s1"), "4/AB")
        with self.assertRaises(youtube.YouTubeFehler):
            youtube.code_aus_adresse("https://whalesqueeze.com/youtube/?state=x&code=a", "s1")

    def test_token_wird_erneuert(self):
        g = dict(G, youtube_bis=0)
        gespeichert = {}
        tok = youtube.gueltiger_token(g, post=lambda url, data=None, timeout=None: Antwort(
            {"access_token": "neu", "expires_in": 3599}), sichern=lambda g, n: (g.update(n), gespeichert.update(n)))
        self.assertEqual(tok, "neu")
        self.assertNotIn("youtube_refresh_token", gespeichert)   # Google schickt beim Erneuern keinen neuen

    def test_titel_mit_shorts(self):
        titel, text = youtube.titel_und_text(TG)
        self.assertEqual(titel, "📊 Crypto market, Nov 1 #Shorts")
        self.assertLessEqual(len(youtube.titel_und_text("x" * 300)[0]), 100)
        self.assertIn("Not financial advice.", text)
        self.assertNotIn("<", text)

    def test_upload_privat(self):
        d = Path(tempfile.mkdtemp())
        try:
            v = d / "video.mp4"
            v.write_bytes(b"\x00" * 1000)
            gesehen = []

            def post(url, data=None, headers=None, timeout=None):
                gesehen.append(json.loads(data))
                self.assertEqual(headers["X-Upload-Content-Length"], "1000")
                return Antwort({}, 200, {"Location": "https://upload/abc"})

            def put(url, data=None, headers=None, timeout=None):
                self.assertEqual(url, "https://upload/abc")
                return Antwort({"id": "vid123"}, 200)
            link = youtube.hochladen(dict(G), v, TG, "private", post=post, put=put)
            self.assertTrue(link.startswith("https://youtube.com/shorts/vid123"))
            self.assertIn("Öffentlich", link)
            self.assertEqual(gesehen[0]["status"]["privacyStatus"], "private")
            self.assertFalse(gesehen[0]["status"]["selfDeclaredMadeForKids"])
            self.assertTrue(gesehen[0]["snippet"]["title"].endswith("#Shorts"))
        finally:
            shutil.rmtree(d)

    def test_knopf_und_nicht_eingerichtet(self):
        alle = [k["callback_data"] for z in telegram.knoepfe("b1")["inline_keyboard"] for k in z]
        self.assertIn("p|yt|b1", alle)
        self.assertTrue(kanaele.verfuegbar(G)["youtube"])
        with self.assertRaises(kanaele.NichtEingerichtet):
            video_posten.youtube({}, Path("x.mp4"), TG)
        self.assertIn("t.me/whalesqueeze", kanaele.telegram_hinweis(TG, "youtube", {"telegram_kanal": "@whalesqueeze"}))


    def test_alle_kanaele_ohne_youtube_einzeln_mit(self):
        """Wunsch Tobias 02.11.: „Alle Kanäle“ ohne YouTube (solange youtube.in_alle false), ▶️-Knopf geht weiter."""
        import json
        import sys
        import tempfile
        from unittest import mock
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
        import freigabe
        tmp = Path(tempfile.mkdtemp())
        try:
            o = tmp / "20261102-1430_markt_30s_video"
            o.mkdir()
            (o / "video.mp4").write_bytes(b"x")
            (o / "post_telegram.txt").write_text("T\n\nNot financial advice.")
            (o / "post_x.txt").write_text("T")
            gerufen = []
            poster = {z: (lambda z: lambda g, m, t: gerufen.append(z) or "ok")(z)
                      for z in ("telegram", "x", "instagram", "tiktok", "youtube")}
            g = dict(G, telegram_token="t", telegram_kanal="@w")
            with mock.patch.object(freigabe, "AUSGABE", tmp), mock.patch.object(freigabe, "PROTOKOLL", tmp / "p.jsonl"), \
                    mock.patch.object(video_posten, "POSTER", poster), \
                    mock.patch.object(kanaele, "_cfg", return_value={"youtube": {"in_alle": False},
                                                                     "instagram": {"story": False}}):
                freigabe.posten(g, o.name, "alle")
                self.assertNotIn("youtube", gerufen)
                freigabe.posten(g, o.name, "yt")
                self.assertIn("youtube", gerufen)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
