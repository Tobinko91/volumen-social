import os
import subprocess
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent


class ServerTest(unittest.TestCase):
    def test_skripte_sind_gueltiges_bash(self):
        for s in ["einrichten.sh", "auto_update.sh", "probe.sh", "probe_wissen.sh"]:
            r = subprocess.run(["bash", "-n", str(HIER / "tools" / s)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{s}: {r.stderr}")

    def test_keine_schluessel_im_repository(self):
        self.assertFalse((HIER / "secrets.yaml").exists() and
                         "secrets.yaml" not in (HIER / ".gitignore").read_text())

    def test_telegram_ohne_token_sendet_nichts(self):
        from social import telegram
        self.assertFalse(telegram.video_senden({}, HIER / "README.md", "x"))


if __name__ == "__main__":
    unittest.main()
