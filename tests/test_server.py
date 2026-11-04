import os
import subprocess
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent


class ServerTest(unittest.TestCase):
    def test_skripte_sind_gueltiges_bash(self):
        for s in ["einrichten.sh", "auto_update.sh", "probe.sh", "probe_wissen.sh", "probe_news.sh", "plan.sh"]:
            r = subprocess.run(["bash", "-n", str(HIER / "tools" / s)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{s}: {r.stderr}")

    def test_keine_schluessel_im_repository(self):
        self.assertFalse((HIER / "secrets.yaml").exists() and
                         "secrets.yaml" not in (HIER / ".gitignore").read_text())

    def test_telegram_ohne_token_sendet_nichts(self):
        from social import telegram
        self.assertFalse(telegram.video_senden({}, HIER / "README.md", "x"))

    def test_plan_ruhezeit(self):
        plan = (HIER / "tools" / "plan.sh").read_text()
        for stunde in ["22", "23", "00", "01", "02", "03", "04", "05", "06"]:
            self.assertNotIn(f"{stunde}:00)", plan)

    def test_wal_des_tages_im_plan(self):
        plan = (HIER / "tools" / "plan.sh").read_text()
        self.assertIn("19:00) lauf wal", plan)

    def test_us_zeiten(self):
        # Entscheidung Tobias 27.10.2026: Postingzeiten fuer das US-Publikum; ab 1.11.2026 US-Winterzeit (+1 Std.)
        plan = (HIER / "tools" / "plan.sh").read_text()
        for zeile in ("14:30) lauf markt --art post; lauf warum", "15:00|20:00|21:00) lauf news", "16:00) lauf coincheck",
                      "21:30) lauf wissen", "17:30) sudo -u redaktion env $UMGEBUNG python3 tools/folgen.py"):
            self.assertIn(zeile, plan)


if __name__ == "__main__":
    unittest.main()
