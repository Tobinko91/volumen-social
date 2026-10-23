"""Wunsch Tobias 22./23.10.2026: in Bildern, Videos und Texten nur 'Keine Anlageberatung'."""
import pathlib
import unittest

import yaml

WURZEL = pathlib.Path(__file__).resolve().parents[1]


class HinweisTest(unittest.TestCase):
    def test_nur_keine_anlageberatung(self):
        h = yaml.safe_load((WURZEL / "config.yaml").read_text(encoding="utf-8"))["hinweise"]
        self.assertEqual(h["fusszeile"], "Keine Anlageberatung")
        self.assertEqual(h["post_text"], "Keine Anlageberatung.")
        self.assertFalse(h.get("konflikt"))

    def test_kein_ki_hinweis_im_code(self):
        for datei in list((WURZEL / "social").glob("*.py")) + [WURZEL / "main.py"]:
            text = datei.read_text(encoding="utf-8")
            for wort in ("KI-erstellt", "KI erstellt", "AI-generated", "Totalverlust möglich"):
                self.assertNotIn(wort, text, f"{wort} in {datei.name}")


if __name__ == "__main__":
    unittest.main()
