"""Eigene Stimme von Tobias (Test, Entscheidung 11.11.2026)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from social import eigenstimme, bericht

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))
ZEILEN = ["Watch ZK on the 4 hour chart.", "A Hammer. Buy or sell?", "Comment your answer now."]


def woerter(zeilen, pause=0.6):
    out, t = [], 0.3
    for z in zeilen:
        for w in z.split():
            out.append({"w": w, "a": round(t, 2), "e": round(t + 0.25, 2)})
            t += 0.3
        t += pause
    return out


class EigenstimmeTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.o, ignore_errors=True)

    def test_skript_und_warten(self):
        self.assertFalse(eigenstimme.wartet(self.o, "2026-11-11"))
        eigenstimme.skript_speichern(self.o, ZEILEN, {"n": 30, "mehrheit": "sell", "pct": 70}, None, "2026-11-11")
        self.assertTrue(eigenstimme.wartet(self.o, "2026-11-11"))
        eigenstimme.speichern(self.o, b"x" * 2000, "2026-11-11")
        self.assertFalse(eigenstimme.wartet(self.o, "2026-11-11"))
        self.assertEqual(eigenstimme.skript_laden(self.o, "2026-11-11")["community"]["pct"], 70)
        t = eigenstimme.skript_text(["ZK moved −8.7% in 24 hours."])
        self.assertIn("minus eight point seven percent", t)   # Zahlen ausgeschrieben zum Vorlesen
        self.assertIn("Mikrofon", t)

    def test_grenzen_in_den_pausen(self):
        w = woerter(ZEILEN)
        g = eigenstimme.grenzen(ZEILEN, w)
        self.assertEqual(len(g), 3)
        ende_satz1 = w[5]["e"]          # „Watch ZK on the 4 hour chart.“ = 7 gesprochene Woerter? -> pruefen ueber Pause
        self.assertGreater(g[0][1], w[0]["a"])
        for (a, e), (a2, _) in zip(g, g[1:]):
            self.assertAlmostEqual(e, a2)
        # Schnitt liegt zwischen zwei Woertern, nicht mitten in einem
        for _, e in g[:-1]:
            self.assertFalse(any(x["a"] < e < x["e"] for x in w))
        self.assertTrue(ende_satz1 > 0)

    def test_falsche_aufnahme_wird_abgelehnt(self):
        with self.assertRaises(ValueError):
            eigenstimme.grenzen(ZEILEN, woerter(["hello"]))
        with self.assertRaises(ValueError):
            eigenstimme.grenzen(ZEILEN, [])

    def test_sprecher_schneidet_echte_datei(self):
        rec = self.o / "rec.ogg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=6",
                        "-c:a", "libopus", str(rec)], check=True)
        w = woerter(ZEILEN, pause=0.4)

        class R:
            status_code = 200

            def json(self):
                return {"words": [{"text": x["w"], "start": x["a"], "end": x["e"], "type": "word"} for x in w]
                        + [{"text": " ", "start": 0, "end": 0, "type": "spacing"}]}

        sp = eigenstimme.sprecher(rec, "k", ZEILEN, post=lambda *a, **k: R())
        dateien, dauern, quelle = sp(ZEILEN, self.o / "ton", CFG, None)
        self.assertEqual(quelle, "Stimme Tobias")
        self.assertEqual(len(dateien), 3)
        for f in dateien:
            self.assertEqual(f.suffix, ".mp3")
            self.assertTrue(f.exists())
            self.assertTrue(json.loads(f.with_suffix(".json").read_text()))   # Wort-Zeitmarken je Satz
        with self.assertRaises(ValueError):   # Daten geaendert -> Brian
            sp(ZEILEN[:2], self.o / "ton2", CFG, None)

    def test_eigenes_format_im_wochenbericht(self):
        self.assertEqual(bericht.format_aus_ordner("20261111-2130_formationich_ZK_video"), "formationich_video")
        self.assertIn("formationich_video", bericht.NAMEN)


if __name__ == "__main__":
    unittest.main()
