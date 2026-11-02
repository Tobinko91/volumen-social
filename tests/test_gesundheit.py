"""Taeglicher Gesundheits-Check (Wunsch Tobias 02.11.2026): Protokoll lesen, Fehler und Luecken finden."""
import json
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER / "tools"))
import gesundheit as gh  # noqa: E402

LOG = """2026-11-01 21:30:04 Plan 21:30 erledigt
Quellen: CoinDesk: Fehler: ParseError, Cointelegraph: ok (15 neu), Cointelegraph Deutschland: Fehler: ParseError, X-Radar (@a): aus (config)
News: Fed holds | Pruefung: bestanden
2026-11-02 15:00:09 Plan 15:00 erledigt
Claude-Fehler: Expecting value: line 1 column 1 (char 0)
2026-11-02 15:30:12 Plan 15:30 erledigt
Quellen: CoinDesk: Fehler: ParseError, Cointelegraph: ok (2 neu), Cointelegraph Deutschland: Fehler: ParseError
2026-11-02 20:00:05 Plan 20:00 erledigt
2026-11-02 14:30:20 Plan 14:30 erledigt
"""


class GesundheitTest(unittest.TestCase):
    def test_abschnitte_und_fehler(self):
        a = gh.plan_abschnitte(LOG, "2026-11-02")
        self.assertEqual(sorted(a), ["14:30", "15:00", "15:30", "20:00"])
        self.assertIn("News: Fed holds | Pruefung: bestanden", a["15:00"])   # Ausgabe steht VOR dem Marker
        arten, quellen, laeufe = gh.fehler_zaehlen(a)
        self.assertEqual(arten["Claude-Antwort unlesbar (Kommentare)"], 1)
        self.assertEqual(laeufe, 2)
        self.assertEqual(quellen["CoinDesk"], 2)
        self.assertEqual(quellen["Cointelegraph Deutschland"], 2)
        self.assertNotIn("Cointelegraph", quellen)

    def test_bericht_meldet_luecken(self):
        a = gh.plan_abschnitte(LOG, "2026-11-02")
        arten, quellen, laeufe = gh.fehler_zaehlen(a)
        vs = {"je": Counter({"markt": 1, "news": 2}), "status": Counter({"gepostet": 2, "offen": 1})}
        text, warn = gh.bericht_text("2026-11-02", a, vs, arten, quellen, laeufe, [], ("2026-11-02 18:45:41 Update auf 4b1696a", False),
                                     12, 60, False, False)
        self.assertIn("4/10 Termine", text)
        self.assertIn("Folge-Liste", text)
        self.assertIn("CoinDesk", text)
        self.assertIn("Claude-Antwort unlesbar (Kommentare) 1×", text)
        self.assertIn("Stimme: noch nicht", text)
        self.assertGreaterEqual(warn, 3)

    def test_alles_gut(self):
        a = {s: [] for s in gh.TERMINE}
        vs = {"je": Counter({"news": 3}), "status": Counter({"gepostet": 3})}
        text, warn = gh.bericht_text("2026-11-02", a, vs, Counter(), Counter(), 3, [], ("x Update auf abc", False),
                                     5, 70, True, False)
        self.assertEqual(warn, 0)
        self.assertIn("Alles in Ordnung", text)

    def test_vorschlaege_und_haengend(self):
        d = Path(tempfile.mkdtemp())
        try:
            for name, st in (("20261102-1430_markt_30s", {"telegram": "l"}),
                             ("20261102-1430_markt_30s_video", {"telegram": "l", "geplant": {"instagram": 100}}),
                             ("20261102-1900_wal_BAT", {"verworfen": 1}), ("20261102-2130_wissen_hebel", None),
                             ("20261101-2130_wissen_x", None)):
                (d / name).mkdir()
                if st:
                    (d / name / "gepostet.json").write_text(json.dumps(st))
            v = gh.vorschlaege(d, "2026-11-02")
            self.assertEqual(sum(v["je"].values()), 4)
            self.assertEqual(v["status"], Counter({"gepostet": 2, "verworfen": 1, "offen": 1}))
            self.assertEqual(gh.haengend(d, 10_000), ["20261102-1430_markt_30s_video → instagram"])
        finally:
            shutil.rmtree(d)

    def test_update_fehlgeschlagen(self):
        self.assertTrue(gh.update_stand("a Update auf 1\nb Tests fehlgeschlagen, bleibe auf 1")[1])

    def test_im_plan(self):
        self.assertIn('[ "$SLOT" = "09:00" ] && sudo -u redaktion env $UMGEBUNG python3 tools/gesundheit.py --senden',
                      (HIER / "tools/plan.sh").read_text())


if __name__ == "__main__":
    unittest.main()
