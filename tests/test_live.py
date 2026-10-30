"""Live-Eilmeldungen (Wunsch Tobias 30.10.2026 nach dem Binance-Hack): 2 Quellen reichen, mehr Eil-Woerter,
Lauf alle 10 Minuten rund um die Uhr."""
import re
import tempfile
import types
import unittest
from pathlib import Path

import yaml

import main
from social import news

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
JETZT = 1793300000


def m(quelle, titel, radar=False):
    return {"quelle": quelle, "titel": titel, "kurz": "", "link": f"https://x/{quelle}", "ts": JETZT,
            "gewicht": 0.8 if radar else 1.0, "radar": radar}


class EilTest(unittest.TestCase):
    def test_zwei_quellen_mit_radar_reichen(self):
        g = news.buendeln([m("Watcher Guru", "JUST IN: Binance hacked, $6.3 billion drained from hot wallets", True),
                           m("CoinDesk", "Binance hacked: $6.3 billion drained from hot wallets")])
        self.assertEqual(len(g), 1)
        self.assertTrue(g[0]["eil"])

    def test_eine_quelle_reicht_nicht(self):
        g = news.buendeln([m("Watcher Guru", "JUST IN: Binance hacked, $6.3 billion drained", True)])
        self.assertFalse(g[0]["eil"])

    def test_neue_eil_woerter(self):
        for t in ("Binance suspends withdrawals after security incident", "Withdrawals halted on major exchange",
                  "USDe loses its peg", "Stablecoin depegs to $0.91", "Attackers drained $40M from bridge"):
            self.assertTrue(news.EIL.search(t), t)
        for t in ("Bitcoin rises 2% ahead of Fed", "Exchange lists new token"):
            self.assertFalse(news.EIL.search(t), t)

    def test_tageslimit_aus_config(self):
        self.assertEqual(CFG["eil"]["max_pro_tag"], 5)
        laden = lambda url: (_ for _ in ()).throw(OSError())
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "news_stand.json"
            import json, time
            p.write_text(json.dumps({"links": [], "woerter": [], "eil": [time.time()] * 5}))
            args = types.SimpleNamespace(out=d, eil=True, senden=False, daten=None)
            aufrufe = []
            self.assertEqual(main.news_beitrag(args, CFG, {}, set(), laden=laden,
                                               schreiber=lambda g: aufrufe.append(g)), 0)
            self.assertEqual(aufrufe, [])


class ZeitplanTest(unittest.TestCase):
    def test_live_alle_10_minuten_rund_um_die_uhr(self):
        cron = (HIER / "deploy/plan.cron").read_text()
        zeile = next(z for z in cron.splitlines() if "live.sh" in z and not z.startswith("#"))
        self.assertTrue(zeile.startswith("5-55/10 * * * * root"))
        live = (HIER / "tools/live.sh").read_text()
        self.assertIn("news --eil --senden", live)
        self.assertIn("flock -n", live)
        self.assertIn("pause", live)

    def test_plan_hat_keinen_stunden_eil_lauf_mehr(self):
        plan = (HIER / "tools/plan.sh").read_text()
        self.assertFalse(re.search(r"^\s*[^#].*news --eil", plan, re.M))


if __name__ == "__main__":
    unittest.main()
