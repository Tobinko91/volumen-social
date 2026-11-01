"""Punkt C (01.11.2026): jeden Instagram-Beitrag auch als Story teilen."""
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from social import kanaele, story

HIER = Path(__file__).resolve().parent.parent
G = {"instagram_token": "ig", "instagram_user_id": "17"}


class StoryTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.alt = kanaele.IG_ORDNER
        kanaele.IG_ORDNER = self.d / "oeffentlich"

    def tearDown(self):
        kanaele.IG_ORDNER = self.alt
        shutil.rmtree(self.d)

    def test_bild_wird_9_zu_16(self):
        p = self.d / "post.png"
        Image.new("RGB", (1080, 1350), "white").save(p)
        z = story.story_bild(p, self.d / "s.jpg")
        self.assertEqual(Image.open(z).size, (1080, 1920))

    def _ig(self, gesehen):
        def ig(methode, pfad, token, **params):
            gesehen.append((pfad, params))
            if pfad.endswith("/media"):
                return {"id": "c1"}
            if pfad == "c1":
                return {"status_code": "FINISHED"}
            return {"id": "s1"}
        return ig

    def test_bild_und_video_als_story(self):
        p = self.d / "post.png"
        Image.new("RGB", (1080, 1350), "white").save(p)
        v = self.d / "video.mp4"
        v.write_bytes(b"v")
        alt = kanaele._ig
        try:
            for medium, feld in ((p, "image_url"), (v, "video_url")):
                gesehen = []
                kanaele._ig = self._ig(gesehen)
                self.assertEqual(story.posten(G, medium, warten=lambda s: None, pruefen_url=lambda u: 200),
                                 "Story geteilt")
                params = next(x for pf, x in gesehen if pf.endswith("/media"))
                self.assertEqual(params["media_type"], "STORIES")
                self.assertIn(feld, params)
                self.assertTrue(any(pf.endswith("/media_publish") for pf, _ in gesehen))
                self.assertEqual(list(kanaele.IG_ORDNER.iterdir()), [])
        finally:
            kanaele._ig = alt

    def test_ohne_token(self):
        with self.assertRaises(kanaele.NichtEingerichtet):
            story.posten({}, self.d / "x.png")


if __name__ == "__main__":
    unittest.main()
