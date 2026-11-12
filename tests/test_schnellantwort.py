"""Schnell-Antworten unter grossen Posts (Wunsch Tobias 12.11.2026)."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER / "tools"))


class SchnellTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        import schnellantwort
        self.s = schnellantwort
        self.s.AUSGABE = Path(self.t.name)
        self.s.BASIS = Path(self.t.name)
        (Path(self.t.name) / "secrets.yaml").write_text("telegram_token: t\ntelegram_chat_id: '1'\n")
        # 15:00 deutscher Zeit am 12.11.2026
        os.environ["TZ"] = "Europe/Berlin"
        time.tzset()
        self.jetzt = time.mktime((2026, 11, 12, 15, 0, 0, 0, 0, -1))

    def tearDown(self):
        self.t.cleanup()

    def post(self, i, konto="KobeissiLetter"):
        return {"id": str(i), "konto": konto, "text": f"BREAKING: MSCI removes Strategy {i}", "likes": 900,
                "punkte": 1000, "zeit": "2026-11-12T13:55:00Z", "link": f"https://x.com/{konto}/status/{i}"}

    def test_sendet_und_merkt(self):
        gesendet = []

        class R:
            def json(self):
                return {"ok": True}

        def senden(url, data=None, timeout=None, **kw):
            gesendet.append(data)
            return R()

        schreiber = lambda ps: [{"id": p["id"], "text": "Index funds selling into the close is the part to watch. "
                                 "Do you expect the pressure before the deadline?", "deutsch": "…"} for p in ps]
        self.assertEqual(self.s.main(lambda: [self.post(1), self.post(2, "WatcherGuru")], schreiber, None, senden,
                                     self.jetzt), 0)
        self.assertEqual(len(gesendet), 2)
        self.assertIn("Schnell-Antwort", gesendet[0]["text"])
        self.assertIn("5 Min. alt", gesendet[0]["text"])
        # gleicher Post kommt nie zweimal (gemeinsamer Stand mit dem Kommentar-Assistenten)
        self.s.main(lambda: [self.post(1)], schreiber, None, senden, self.jetzt + 600)
        self.assertEqual(len(gesendet), 2)
        ids = json.loads((Path(self.t.name) / "kommentare_stand.json").read_text())["ids"]
        self.assertEqual(ids, ["1", "2"])

    def test_ruhezeit_und_tageslimit(self):
        nachts = time.mktime((2026, 11, 12, 23, 30, 0, 0, 0, -1))
        geholt = []
        self.s.main(lambda: geholt.append(1) or [], None, None, None, nachts)
        self.assertEqual(geholt, [])   # nachts keine X-Abfrage (kostet Geld)
        (Path(self.t.name) / "schnellantwort_stand.json").write_text(json.dumps({"anzahl": {"2026-11-12": 12}}))
        self.s.main(lambda: geholt.append(1) or [], None, None, None, self.jetzt)
        self.assertEqual(geholt, [])

    def test_pruefung_verwirft_links_und_erfundene_zahlen(self):
        gesendet = []
        schreiber = lambda ps: [{"id": "1", "text": "Check our channel https://whalesqueeze.com"}]
        self.s.main(lambda: [self.post(1)], schreiber, None, lambda *a, **k: gesendet.append(1), self.jetzt)
        self.assertEqual(gesendet, [])


if __name__ == "__main__":
    unittest.main()
