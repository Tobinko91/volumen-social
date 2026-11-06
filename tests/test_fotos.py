"""Foto-Bibliothek, Hingucker-Bilder und A/B-Test (Wunsch Tobias 06.11.2026)."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from social import bildpaket, fotos


def meta(lizenz, autor="Jane Doe"):
    return {"LicenseShortName": {"value": lizenz}, "Artist": {"value": f"<a href='x'>{autor}</a>"}}


class LizenzTest(unittest.TestCase):
    def test_nur_freie_lizenzen(self):
        self.assertEqual(fotos.lizenz(meta("Public domain")), (True, "Public domain", ""))
        self.assertTrue(fotos.lizenz(meta("CC0"))[0])
        ok, _, credit = fotos.lizenz(meta("CC BY-SA 4.0", "Gage Skidmore"))
        self.assertTrue(ok)
        self.assertEqual(credit, "Photo: Gage Skidmore · CC BY-SA 4.0")
        for schlecht in ("CC BY-NC 2.0", "CC BY-ND 4.0", "CC BY-NC-SA 3.0", "Fair use", "", "All rights reserved"):
            self.assertFalse(fotos.lizenz(meta(schlecht))[0], schlecht)


class SucheTest(unittest.TestCase):
    def test_filter_und_reihenfolge(self):
        def info(lz, w=2000, h=2400, mime="image/jpeg"):
            return [{"thumburl": "https://u/t.jpg", "descriptionurl": "https://c/d", "width": w, "height": h,
                     "mime": mime, "extmetadata": meta(lz)}]
        seiten = {"1": {"index": 1, "title": "File:Jerome Powell speaking.jpg", "imageinfo": info("CC BY 2.0")},
                  "2": {"index": 2, "title": "File:Jerome Powell official portrait.jpg", "imageinfo": info("Public domain")},
                  "3": {"index": 3, "title": "File:Powell caricature.jpg", "imageinfo": info("CC0")},
                  "4": {"index": 4, "title": "File:Jerome Powell press.jpg", "imageinfo": info("CC BY-NC 2.0")},
                  "5": {"index": 5, "title": "File:Jerome Powell small.jpg", "imageinfo": info("CC0", 400, 300)},
                  "6": {"index": 6, "title": "File:Fed building.jpg", "imageinfo": info("CC0")},
                  "7": {"index": 7, "title": "File:Jerome Powell aussortiert.jpg", "imageinfo": info("CC0")}}

        class A:
            def json(self):
                return {"query": {"pages": seiten}}
        p = {"slug": "powell", "suche": "Jerome Powell", "muss": "Powell", "ohne": ["File:Jerome Powell aussortiert.jpg"]}
        k = fotos.suchen(p, get=lambda *a, **kw: A())
        self.assertEqual([x["titel"] for x in k], ["File:Jerome Powell official portrait.jpg",
                                                   "File:Jerome Powell speaking.jpg"])
        self.assertEqual(k[0]["credit"], "")
        self.assertIn("CC BY 2.0", k[1]["credit"])

    def test_holen_und_waehlen(self):
        with tempfile.TemporaryDirectory() as d:
            ziel = Path(d)

            class A:
                content = b"jpg"

                def json(self):
                    return {"query": {"pages": {"1": {"index": 1, "title": "File:Kevin Warsh official.jpg",
                                                      "imageinfo": [{"thumburl": "https://u/1.jpg", "width": 1200,
                                                                     "height": 1500, "mime": "image/jpeg",
                                                                     "extmetadata": meta("Public domain")}]}}}}
            idx = fotos.holen(ziel, [{"slug": "warsh", "name": "Kevin Warsh", "suche": "Kevin Warsh", "muss": "Warsh"}],
                              get=lambda *a, **kw: A())
            self.assertEqual(idx["warsh"][0]["datei"], "warsh/1.jpg")
            self.assertTrue((ziel / "warsh" / "1.jpg").exists())
            self.assertEqual(fotos.waehlen(ziel, "warsh", "x")["name"], "Kevin Warsh")
            self.assertIsNone(fotos.waehlen(ziel, "gibtsnicht"))

    def test_personenliste(self):
        import yaml
        p = yaml.safe_load((Path(__file__).resolve().parent.parent / "inhalte" / "personen.yaml").read_text())
        self.assertEqual(len(p), 20)
        self.assertEqual(len({x["slug"] for x in p}), 20)
        self.assertTrue(all(x["muss"] and x["suche"] for x in p))


class HinguckerTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "fotos" / "warsh").mkdir(parents=True)
        Image.new("RGB", (1200, 1500), (120, 110, 100)).save(self.d / "fotos" / "warsh" / "1.jpg")
        (self.d / "fotos" / "fotos.json").write_text(json.dumps({"warsh": [
            {"datei": "warsh/1.jpg", "credit": "Photo: A · CC BY 4.0", "name": "Kevin Warsh"}]}))
        self.o = self.d / "chat_20261106-hot-x"
        self.o.mkdir()
        Image.new("RGB", (1080, 1350)).save(self.o / "post.png")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def test_drei_arten(self):
        for spec in ({"art": "foto", "person": "warsh", "kopf": "Fed signals a December hike", "unter": "Nov 6"},
                     {"art": "zitat", "person": "warsh", "zitat": "Conditions are quite positive.",
                      "wer": "Fed Chair Kevin Warsh", "wann": "Nov 5, 2026"},
                     {"art": "vergleich", "kopf": "Jobs beat", "etikett": "US JOBS",
                      "reihen": [["Expected", 60000, "60K"], ["Actual", 165000, "165K"], ["September", 60000, "60K"]]}):
            (self.o / "hingucker.json").write_text(json.dumps(spec))
            p = bildpaket.aus_spec(self.o, self.d / "fotos")
            self.assertEqual(Image.open(p).size, (1200, 675), spec["art"])

    def test_ohne_foto_kein_hingucker(self):
        (self.o / "hingucker.json").write_text(json.dumps({"art": "foto", "person": "niemand", "kopf": "x"}))
        self.assertIsNone(bildpaket.aus_spec(self.o, self.d / "fotos"))
        self.assertEqual(bildpaket.x_bilder(self.o / "post.png"), [self.o / "post.png"])

    def test_ab_test_abwechselnd(self):
        stand = self.d / "stand.json"
        arten = []
        for i in range(4):
            o = self.d / f"b{i}"
            o.mkdir()
            Image.new("RGB", (10, 10)).save(o / "post.png")
            Image.new("RGB", (10, 10)).save(o / "hingucker.png")
            arten.append(bildpaket.test_zuteilen(o, stand))
            self.assertEqual(bildpaket.test_zuteilen(o, stand), arten[-1])   # gleicher Beitrag bleibt in seiner Gruppe
            n = len(bildpaket.x_bilder(o / "post.png"))
            self.assertEqual(n, 2 if arten[-1] == "mit" else 1)
        self.assertEqual(arten, ["mit", "ohne", "mit", "ohne"])

    def test_wochenbericht_vergleich(self):
        from social import bericht
        prot = [{"ereignis": "gepostet", "kanal": "x", "link": f"l{i}", "bildtest": "mit" if i % 2 else "ohne"}
                for i in range(12)]
        x = {f"l{i}": {"aufrufe": 2000 if i % 2 else 1000, "likes": 10, "reposts": 1, "antworten": 1} for i in range(12)}
        b = bericht.bildtest(prot, x)
        self.assertEqual((len(b["mit"]), len(b["ohne"])), (6, 6))
        t = "\n".join(bericht.bildtest_text(b))
        self.assertIn("+100 % Aufrufe", t)
        self.assertIn("für alle Beiträge einführen", t)
        bericht.protokollieren(self.d / "p.jsonl", self.o.name, "gepostet", "x", "l")
        (self.o / "bildtest.json").write_text(json.dumps({"art": "mit"}))
        (self.d / "p2.jsonl")
        bericht.protokollieren(self.d / "p.jsonl", self.o.name, "gepostet", "x", "l2")
        zeilen = bericht.protokoll_laden(self.d / "p.jsonl")
        self.assertNotIn("bildtest", zeilen[0])
        self.assertEqual(zeilen[1]["bildtest"], "mit")


if __name__ == "__main__":
    unittest.main()


class EinbauTest(unittest.TestCase):
    def test_x_laedt_beide_bilder_hoch(self):
        from unittest import mock
        from social import kanaele
        d = Path(tempfile.mkdtemp())
        Image.new("RGB", (10, 10)).save(d / "post.png")
        Image.new("RGB", (10, 10)).save(d / "hingucker.png")
        (d / "bildtest.json").write_text(json.dumps({"art": "mit"}))
        gesehen = []

        class R:
            status_code = 200

            def __init__(self, j):
                self.j = j

            def json(self):
                return self.j

        def post(url, **kw):
            gesehen.append((url, kw.get("files", {}).get("media", [None])[0] if kw.get("files") else kw.get("json")))
            return R({"data": {"id": str(len(gesehen))}})
        g = {"x_api_key": "a", "x_api_secret": "b", "x_access_token": "c", "x_access_secret": "d"}
        with mock.patch.object(kanaele.requests, "post", post):
            kanaele.x_posten(g, d / "post.png", "Text")
        self.assertEqual([g_[1] for g_ in gesehen[:2]], ["hingucker.png", "post.png"])   # Hingucker zuerst
        self.assertEqual(gesehen[2][1]["media"]["media_ids"], ["1", "2"])

    def test_eingang_zeichnet_hingucker(self):
        import os
        import shutil
        import sys
        from unittest import mock
        d = Path(tempfile.mkdtemp())
        try:
            (d / "fotos" / "trump").mkdir(parents=True)
            Image.new("RGB", (1200, 1500)).save(d / "fotos" / "trump" / "1.jpg")
            (d / "fotos" / "fotos.json").write_text(json.dumps({"trump": [{"datei": "trump/1.jpg", "credit": ""}]}))
            ein = d / "eingang" / "20261106-hot-test"
            ein.mkdir(parents=True)
            Image.new("RGB", (1080, 1350)).save(ein / "post.png")
            (ein / "post_x.txt").write_text("X\nNot financial advice.")
            (ein / "post_telegram.txt").write_text("T\n\n<i>Not financial advice.</i>")
            (ein / "hingucker.json").write_text(json.dumps({"art": "foto", "person": "trump", "kopf": "Trump speaks"}))
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
            import eingang
            gesendet, fotos_tg = [], []
            with mock.patch.object(eingang, "EINGANG", d / "eingang"), mock.patch.object(eingang, "AUSGABE", d), \
                    mock.patch.object(eingang, "BASIS", d), mock.patch.object(eingang, "FOTOS", d / "fotos"), \
                    mock.patch.object(eingang.telegram, "foto_an_tobias", lambda g, b, t: fotos_tg.append(b) or True), \
                    mock.patch.object(eingang.telegram, "vorschlag_senden", lambda g, z, h: gesendet.append(h) or True):
                eingang.main()
            self.assertIn("MIT Hingucker", gesendet[0])
            self.assertTrue((d / "chat_20261106-hot-test" / "hingucker.png").exists())
            self.assertEqual(len(fotos_tg), 1)
        finally:
            shutil.rmtree(d)
