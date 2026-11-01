"""Freigabe-Tor (Entscheidung Tobias 01.11.2026): Routine-Formate erst nach 14 sauberen Tagen automatisch."""
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

import yaml

from social import autopost, bericht

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
JETZT = 1795000000
TAG = 86400


def prot(format="markt", tage=15, freigaben=12, verworfen=0, ordner_vorsilbe="20261101-1430_markt_30s"):
    p = [{"ts": JETZT - tage * TAG, "ordner": "start", "format": "news", "ereignis": "gepostet"}]
    p += [{"ts": JETZT - i * TAG // 2, "ordner": f"{ordner_vorsilbe}{i}", "format": format, "ereignis": "gepostet",
           "kanal": "x"} for i in range(freigaben)]
    p += [{"ts": JETZT - TAG, "ordner": "v", "format": format, "ereignis": "verworfen"} for _ in range(verworfen)]
    return p


class TorTest(unittest.TestCase):
    def test_einstellungen(self):
        a = CFG["autopost"]
        self.assertEqual((a["saubere_tage"], a["min_freigaben"]), (14, 10))
        self.assertNotIn("news", a["formate"])
        self.assertNotIn("redaktion", a["formate"])

    def test_regeln(self):
        self.assertTrue(autopost.erlaubt("markt", prot(), CFG, jetzt=JETZT)[0])
        self.assertFalse(autopost.erlaubt("news", prot("news"), CFG, jetzt=JETZT)[0])
        self.assertIn("jünger", autopost.erlaubt("markt", prot(tage=10), CFG, jetzt=JETZT)[1])
        self.assertIn("verworfen", autopost.erlaubt("markt", prot(verworfen=1), CFG, jetzt=JETZT)[1])
        self.assertIn("erst 5 Freigaben", autopost.erlaubt("markt", prot(freigaben=5), CFG, jetzt=JETZT)[1])
        self.assertFalse(autopost.erlaubt("markt", prot(), CFG, aus=True, jetzt=JETZT)[0])
        self.assertFalse(autopost.erlaubt("markt", prot(), dict(CFG, autopost={"aktiv": False}), jetzt=JETZT)[0])

    def test_status_text(self):
        t = autopost.status(prot(), CFG, jetzt=JETZT)
        self.assertIn("✅ Markt (Bild)", t)
        self.assertIn("⏳ Coin-Check", t)
        self.assertIn("/auto aus", t)

    def test_main_postet_automatisch_oder_schlaegt_vor(self):
        import main
        with tempfile.TemporaryDirectory() as d:
            ordner = Path(d) / "20261101-1430_markt_30s"
            ordner.mkdir()
            args = types.SimpleNamespace(out=d, coin=None)
            gepostet, vorgeschlagen, nachrichten = [], [], []
            alt = (main.telegram.vorschlag_senden, main.telegram.text_senden)
            main.telegram.vorschlag_senden = lambda g, o, h="": vorgeschlagen.append(o.name) or True
            main.telegram.text_senden = lambda g, t: nachrichten.append(t) or True
            sys.path.insert(0, str(HIER / "tools"))
            import freigabe
            alt_posten = freigabe.posten
            freigabe.posten = lambda g, name, ziel: gepostet.append((name, ziel)) or "✅ telegram: ok"
            alt_laden = bericht.protokoll_laden
            try:
                bericht.protokoll_laden = lambda p, seit=0: prot()
                import time
                alt_zeit = time.time
                time.time = lambda: JETZT
                try:
                    main.vorschlag(args, {}, CFG, ordner)
                    self.assertEqual(gepostet, [(ordner.name, "alle")])
                    self.assertIn("Automatisch gepostet", nachrichten[0])
                    main.vorschlag(args, {}, CFG, ordner, "⚠️ x", ["Zahl 9 steht nicht in den Daten"])
                    self.assertEqual(vorgeschlagen, [ordner.name])   # Pruefungsfehler -> doch Vorschlag
                    main.vorschlag(types.SimpleNamespace(out=d, coin="BTC"), {}, CFG, ordner)
                    self.assertEqual(len(vorgeschlagen), 2)   # /check bleibt Vorschlag
                    (Path(d) / ".autopost_aus").touch()
                    main.vorschlag(args, {}, CFG, ordner)
                    self.assertEqual(len(vorgeschlagen), 3)   # /auto aus
                finally:
                    time.time = alt_zeit
            finally:
                bericht.protokoll_laden = alt_laden
                freigabe.posten = alt_posten
                main.telegram.vorschlag_senden, main.telegram.text_senden = alt


if __name__ == "__main__":
    unittest.main()
