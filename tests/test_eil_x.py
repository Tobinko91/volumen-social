"""Eilmeldungen aus grossen X-Konten automatisch als Reel (Wunsch Tobias 25.11.2026)."""
import json
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import eil_x

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
TEXT = ("BREAKING: Bitcoin falls below $57,500 and ETH nears $1,600 as the selloff in crypto gains momentum. "
        "Another -$500 million worth of levered positions have been liquidated over the last 24 hours.")
SPEC = {"szenen": [{"etikett": "BREAKING", "kopf": "Crypto selloff speeds up", "text": "Breaking: Bitcoin slipped under 57,500 dollars."},
                   {"etikett": "LIQUIDATIONS", "kopf": "500 million wiped out", "text": "500 million dollars in leveraged bets were liquidated in 24 hours."},
                   {"etikett": "YOUR CALL", "kopf": "Bottom or more pain?", "text": "Is this the bottom? Tell us below."}],
        "coin": "BTC", "nur_kurs": False, "x": "Bitcoin under $57,500. $500M liquidated in 24h. Bottom or more pain? $BTC"}


def post(i=1, text=TEXT):
    return {"id": f"19{i:08d}", "konto": "KobeissiLetter", "text": text, "link": f"https://x.com/k/status/{i}"}


class EilXTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.o = Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def test_erkennen(self):
        ps = [post(1), post(2, "BREAKING: Oil jumps 5%"), post(3, "Bitcoin is interesting today"),
              post(4, "JUST IN: BlackRock buys more ETH")]
        self.assertEqual([p["id"][-1] for p in eil_x.erkennen(ps)], ["1", "4"])

    def test_zahlen_nur_aus_dem_post(self):
        self.assertTrue(eil_x.zahlen_ok(SPEC, TEXT))
        falsch = {"szenen": [{"kopf": "x", "text": "Bitcoin could fall to 40,000 dollars."}]}
        self.assertFalse(eil_x.zahlen_ok(falsch, TEXT))

    def test_reel_mit_live_chart_und_frage(self):
        gesendet = []
        out = eil_x.verarbeiten([post(1)], CFG, {}, self.o, schreiber=lambda p: SPEC,
                                senden=lambda g, o, h: gesendet.append(h), reel_bauen=lambda o: "test", jetzt=1_800_000_000)
        self.assertEqual(len(out), 1)
        r = json.loads((out[0] / "reel.json").read_text())
        self.assertEqual(r["szenen"][1]["chart"]["base"], "BTC")
        self.assertEqual(r["frage"]["name"], "$BTC")
        self.assertEqual(Image.open(out[0] / "szene_0.png").size, (1080, 1920))
        self.assertLessEqual(len((out[0] / "post_x.txt").read_text()), 280)
        self.assertIn("@KobeissiLetter", gesendet[0])
        # gleicher Post nie zweimal
        self.assertEqual(eil_x.verarbeiten([post(1)], CFG, {}, self.o, schreiber=lambda p: SPEC, jetzt=1_800_000_100), [])

    def test_kursalarm_hat_vorrang_und_tageslimit(self):
        (self.o / "kursalarm_stand.json").write_text(json.dumps({"BTC_marke_57500": 1_800_000_000 - 600,
                                                                 "BTC_preis": 57_400}))
        nur_kurs = dict(SPEC, nur_kurs=True)
        self.assertEqual(eil_x.verarbeiten([post(5)], CFG, {}, self.o, schreiber=lambda p: nur_kurs,
                                           jetzt=1_800_000_000), [])
        cfg = dict(CFG, eil_x={"aktiv": True, "max_pro_tag": 1})
        out = eil_x.verarbeiten([post(6), post(7)], cfg, {}, self.o, schreiber=lambda p: SPEC, jetzt=1_800_000_000)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
