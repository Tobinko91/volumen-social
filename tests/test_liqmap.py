"""S28 Liquidity Map of the Day (Wunsch Tobias 09.11.2026)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import liqmap

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


class LiqMapTest(unittest.TestCase):
    def setUp(self):
        self.d = liqmap.laden(HIER / "beispieldaten")

    def test_texte(self):
        tx = liqmap.texte(self.d, CFG)
        self.assertLessEqual(len(tx["x"]), 280)
        self.assertEqual(tx["x"].count("$"), 1)                       # nur $BTC als Cashtag
        self.assertIn("estimated", tx["x"].lower())
        self.assertNotIn("target price", tx["telegram"].lower())
        self.assertIn("already ran into the estimated short-liquidation cluster", tx["x"])
        for z in tx["sprech"]:
            self.assertNotIn("(", z)

    def test_karussell(self):
        o = Path(tempfile.mkdtemp())
        try:
            folien, szenen = liqmap.bauen(self.d, o, CFG)
            self.assertEqual(len(folien), 3)                          # BTC, Top, Flop
            self.assertEqual(json.loads((o / "karussell.json").read_text())["folien"][0], "folie_00.png")
            self.assertEqual(Image.open(szenen[0]).size, (1080, 1920))
            d = dict(self.d, top=None)
            self.assertEqual(len(liqmap.bauen(d, o / "nur_btc", CFG)[0]), 1)   # ohne Top nur BTC
        finally:
            shutil.rmtree(o)

    def test_main(self):
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run([sys.executable, "main.py", "liqmap", "--daten", "beispieldaten", "--out", t],
                               cwd=HIER, capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-500:])
            self.assertIn("3 Folien", r.stdout)
            self.assertEqual(liqmap.laden(Path(t)), None)


if __name__ == "__main__":
    unittest.main()
