"""Wunsch Tobias 26.10.2026: News direkt formulieren (kein 'Berichten zufolge'), konkrete Termine, mehr Tiefe."""
import datetime as dt
import unittest
from pathlib import Path

import yaml

from social import news_text, pruefung, telegram

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
MONTAG = dt.datetime(2026, 10, 26, 8, 0, tzinfo=news_text.BERLIN)


class DirektTest(unittest.TestCase):
    def test_berichten_zufolge_faellt_durch(self):
        f = pruefung.pruefen(["Berichten zufolge tagt die Fed."], {"fakten": "", "szenen": [0]}, CFG, set(),
                             erlaubt_fusszeile=True)
        self.assertTrue(any("berichten zufolge" in x for x in f))

    def test_prompt_verlangt_direkte_fakten_und_termine(self):
        self.assertIn('nicht\n  "Berichten zufolge', news_text.SYSTEM)
        self.assertIn("Uhrzeit in deutscher Zeit", news_text.SYSTEM)

    def test_uhrzeit_umrechnung_winterzeit_lücke(self):
        # 26.10.2026: Deutschland schon Winterzeit (UTC+1), USA noch Sommerzeit (UTC-4) -> 5 Std. Unterschied
        z = news_text.deutsche_zeiten("Fed decision 2:00 p.m. ET, press conference at 2:30 pm ET.", MONTAG)
        self.assertEqual(z, ["2:00 p.m. ET = 19:00 Uhr deutsche Zeit", "2:30 pm ET = 19:30 Uhr deutsche Zeit"])
        self.assertEqual(news_text.deutsche_zeiten("08:00 UTC", MONTAG), ["08:00 UTC = 9:00 Uhr deutsche Zeit"])
        self.assertEqual(news_text.deutsche_zeiten("Top 2 ET funds", MONTAG), [])
        self.assertEqual(news_text.heute_text(MONTAG), "Montag, 26.10.2026")

    def test_umgerechnete_zeit_besteht_pruefung(self):
        quelle = "Fed decision at 2:00 p.m. ET on Wednesday, October 28."
        fakten = quelle + " " + " ".join(news_text.deutsche_zeiten(quelle, MONTAG))
        f = pruefung.pruefen(["Die Fed entscheidet am 28. Oktober um 19:00 Uhr."], {"fakten": fakten, "szenen": [0]},
                             CFG, set(), erlaubt_fusszeile=True)
        self.assertEqual(f, [])


class LangerTelegramTextTest(unittest.TestCase):
    def test_kurz_bleibt_ganz(self):
        self.assertEqual(telegram.teilen("<b>Kopf</b>\n\nText"), ("<b>Kopf</b>\n\nText", None))

    def test_lang_wird_geteilt_ohne_abschneiden(self):
        t = "📰 <b>Schlagzeile</b>\n\n" + "\n".join(f"• Punkt {i} " + "x" * 80 for i in range(15))
        kopf, rest = telegram.teilen(t)
        self.assertEqual(kopf, "📰 <b>Schlagzeile</b>")
        self.assertEqual(kopf + "\n\n" + rest, t)

    def test_html_zaehlt_nicht(self):
        self.assertEqual(telegram.sichtbar('<a href="https://x.y/?a=1&amp;b=2">Link</a> &amp;'), 6)


if __name__ == "__main__":
    unittest.main()
