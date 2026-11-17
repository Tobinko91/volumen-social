"""S30 (Tobias 14.11.2026): Reels nur mit Live-Daten, Abbruch wenn die Lage gedreht hat."""
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER / "tools"))
from social import reel  # noqa: E402

JETZT = 1_800_000_000.0


def kerzen(preise, start):
    return [{"t": int((start + i * 3600) * 1000), "o": p, "h": p * 1.01, "l": p * 0.99, "c": p, "v": 1}
            for i, p in enumerate(preise)]


class LiveTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp())
        self.web = self.o / "web"
        (self.web / "coins").mkdir(parents=True)
        (self.web / "kerzen").mkdir()
        (self.web / "coins" / "AKE.json").write_text(json.dumps({"base": "AKE", "ts": JETZT - 60, "funding": -0.786}))
        Image.new("RGB", (1200, 900), "black").save(self.web / "kerzen" / "AKE_15m.png")
        (self.web / "liquiditaet.json").write_text(json.dumps({"funding_extrem": [
            {"base": "AKE", "funding": -0.786, "kerzen_png": "kerzen/AKE_15m.png"}]}))
        self.start = JETZT - 48 * 3600
        self.k = kerzen([0.0024] * 5 + [0.005, 0.009, 0.013] + [0.01367] * 40, self.start)

    def tearDown(self):
        shutil.rmtree(self.o, ignore_errors=True)

    def lv(self, **kw):
        return dict({"base": "AKE", "tief_ab_ts": self.start, "marken": [{"preis": 0.0062}],
                     "abbruch": {"preis_unter": 0.0100, "funding_ueber": 0}}, **kw)

    def test_werte(self):
        import os
        os.utime(self.web / "kerzen" / "AKE_15m.png", (JETZT, JETZT))
        w = reel.live_werte(self.lv(), lambda b, i, n: self.k, self.web, JETZT)
        self.assertEqual(w["funding"], "-0.79%")
        self.assertEqual(w["funding_abs"], "0.79%")
        self.assertEqual(w["preis"], "$0.01367")
        self.assertEqual(w["vom_tief"], f"+{(0.01367 / (0.0024 * 0.99) - 1) * 100:.0f}%")
        self.assertEqual(w["marke_0_abstand"], "-55%")
        self.assertTrue(w["_kerzen_png"].endswith("AKE_15m.png"))

    def test_abbruch(self):
        k = kerzen([0.0024] * 5 + [0.013, 0.0090], self.start)
        with self.assertRaises(reel.Abbruch):
            reel.live_werte(self.lv(), lambda b, i, n: k, self.web, JETZT)
        (self.web / "coins" / "AKE.json").write_text(json.dumps({"base": "AKE", "ts": JETZT - 60, "funding": 0.01}))
        with self.assertRaises(reel.Abbruch):
            reel.live_werte(self.lv(), lambda b, i, n: self.k, self.web, JETZT)
        # altes Funding (> 30 Min.) zaehlt nicht als live
        (self.web / "coins" / "AKE.json").write_text(json.dumps({"base": "AKE", "ts": JETZT - 7200, "funding": -0.5}))
        (self.web / "liquiditaet.json").write_text("{}")
        with self.assertRaises(reel.Abbruch):
            reel.live_werte(self.lv(abbruch={"funding_pflicht": True}), lambda b, i, n: self.k, self.web, JETZT)

    def test_bot_bild_und_fokus(self):
        Image.new("RGB", (1080, 1920), "navy").save(self.o / "szene_0.png")
        p = reel.bot_bild_szene(self.o, {"bild": "szene_0.png", "fokus": [0.9, 0.5]},
                                str(self.web / "kerzen" / "AKE_15m.png"), {})
        self.assertEqual(Image.open(p).size, (1080, 1920))
        fx, fy = json.loads(p.with_suffix(".fokus.json").read_text())["fokus"]
        self.assertGreater(fx, 800)

    def test_live_texte(self):
        import eingang
        (self.o / "live_werte.json").write_text(json.dumps({"vom_tief": "+470%", "funding": "-0.79%"}))
        (self.o / "post_x.txt").write_text("$AKE {vom_tief} in 48h, funding {funding}")
        eingang.live_texte(self.o)
        self.assertEqual((self.o / "post_x.txt").read_text(), "$AKE +470% in 48h, funding -0.79%")
        (self.o / "live_werte.json").unlink()
        (self.o / "post_x.txt").write_text("$AKE {vom_tief}")
        (self.o / "post_x_ohne.txt").write_text("$AKE: shorts piling in")
        eingang.live_texte(self.o)
        self.assertEqual((self.o / "post_x.txt").read_text(), "$AKE: shorts piling in")


if __name__ == "__main__":
    unittest.main()


class FrageTest(unittest.TestCase):
    """17.11.2026 Tobias: Abschlussfrage mit 5-s-Countdown bei Meldungen zu handelbaren Coins/Aktien."""

    def test_frage_am_ende(self):
        import yaml
        cfg = yaml.safe_load((HIER / "config.yaml").read_text())
        with tempfile.TemporaryDirectory() as t:
            o = Path(t)
            Image.new("RGB", (1080, 1920), "navy").save(o / "s.png")
            (o / "reel.json").write_text(json.dumps({"thema": "x", "frage": {"name": "$NVDA"},
                                                     "szenen": [{"bild": "s.png", "text": "Nvidia reports today."}]}))
            gerufen = {}

            def sprechen(zeilen, ordner, cfg_, key):
                ordner.mkdir(parents=True, exist_ok=True)
                gerufen["zeilen"] = zeilen
                return [ordner / f"t{i}.mp3" for i in range(len(zeilen))], [2.0] * len(zeilen), "probe"

            def schneiden(bilder, toene, dauern, ziel, cfg_, texte=None):
                gerufen.update(bilder=bilder, dauern=dauern)

            reel.bauen(o, cfg, {}, kerzen_holen=lambda *a: [], sprechen=sprechen, schneiden=schneiden)
            self.assertEqual(len(gerufen["zeilen"]), 2)
            self.assertIn("What will NVDA do after this news? Up or down?", gerufen["zeilen"][1])
            self.assertNotIn("buy", gerufen["zeilen"][1].lower())
            letzte = gerufen["bilder"][-1]
            self.assertEqual(len(letzte), 5)                       # 5 Bilder: 5, 4, 3, 2, 1
            self.assertGreaterEqual(gerufen["dauern"][-1], 5.0)     # Countdown passt ganz hinein
            self.assertEqual(Image.open(letzte[0][0]).size, (1080, 1920))

    def test_ohne_frage_unveraendert(self):
        import yaml
        cfg = yaml.safe_load((HIER / "config.yaml").read_text())
        with tempfile.TemporaryDirectory() as t:
            o = Path(t)
            Image.new("RGB", (1080, 1920), "navy").save(o / "s.png")
            (o / "reel.json").write_text(json.dumps({"thema": "x", "szenen": [{"bild": "s.png", "text": "Hi."}]}))
            n = {}
            reel.bauen(o, cfg, {}, kerzen_holen=lambda *a: [],
                       sprechen=lambda z, o_, c, k: ([o_ / "t.mp3"], [2.0], "p"),
                       schneiden=lambda b, t_, d, z, c, texte=None: n.update(b=b))
            self.assertEqual(len(n["b"]), 1)
