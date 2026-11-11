"""S27 Formation des Tages (Wunsch Tobias 09.11.2026)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image

from social import formation

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text(encoding="utf-8"))


class FormationTest(unittest.TestCase):
    def setUp(self):
        self.d = formation.laden(HIER / "beispieldaten")

    def test_texte_ehrlich(self):
        tx = formation.texte(self.d)
        self.assertEqual(len(tx["zeilen"]), 7)
        self.assertTrue(tx["zeilen"][0].startswith("Watch ZK"))       # erst die Bewegung
        self.assertIn("Buy or sell?", tx["zeilen"][1])                # dann die Frage
        self.assertIn("−8.7%", tx["zeilen"][4])
        self.assertIn("The textbook was right.", tx["zeilen"][4])
        self.assertIn("58%", tx["zeilen"][5])
        self.assertIn("Without any pattern: 61%", tx["zeilen"][5])
        self.assertIn("No real edge.", tx["zeilen"][5])        # 58 % gegen Zufall 61 %
        self.assertLessEqual(len(tx["x"]), 280)
        self.assertTrue(tx["x"].endswith("Not financial advice."))
        for z in tx["zeilen"]:
            self.assertNotIn("(", z)
            for w in ("buy now", "sell now", "target", "guarant"):
                self.assertNotIn(w, z.lower())

    def test_ohne_statistik_faellt_nur_der_haken_weg(self):
        d = dict(self.d, statistik=None)
        self.assertEqual(len(formation.texte(d)["zeilen"]), 6)
        d2 = dict(self.d, ergebnis=dict(self.d["ergebnis"], r6=5.1, lehrbuch_stimmt=False))
        tx = formation.texte(d2)
        self.assertEqual(tx["titel_erg"], "The textbook was wrong")
        self.assertIn("+5.1%", tx["zeilen"][4])

    def test_unvollstaendige_daten(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "muster_des_tages.json").write_text(json.dumps(dict(self.d, kerzen_nachher=[[1, 1, 1, 1, 1]])))
            self.assertIsNone(formation.laden(t))
            self.assertIsNone(formation.laden(Path(t) / "fehlt"))

    def test_szenen_und_video(self):
        o = Path(tempfile.mkdtemp())
        try:
            folgen, tx = formation.szenen(self.d, o / "b")
            self.assertEqual([len(f) for f in folgen], [24, 2, 5, 6, 1, 1, 1])   # Aufbau, Frage, Countdown, ...
            self.assertEqual(Image.open(folgen[2][0][0]).size, (1080, 1920))
            self.assertAlmostEqual(sum(s for _, s in folgen[2]), 5.0)

            def sprechen(zeilen, ordner, cfg, key):
                ordner.mkdir(parents=True, exist_ok=True)
                toene = []
                for i, _ in enumerate(zeilen):
                    p = ordner / f"z{i}.mp3"
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                                    "-t", "1", "-c:a", "libmp3lame", str(p)], check=True)
                    toene.append(p)
                return toene, [1.0] * len(zeilen), "probe"
            v, q, _ = formation.video(self.d, o, CFG, {}, sprechen=sprechen)
            dauer = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                          "csv=p=0", str(v)], capture_output=True, text=True).stdout)
            self.assertGreater(dauer, 18)          # Countdown + Aufloesung haben Mindestdauern
            self.assertTrue((o / "ton" / "countdown_tick.mp3").exists())
        finally:
            shutil.rmtree(o)

    def test_aufbau_verraet_nichts(self):
        """Erstes Bild: nur 3 Kerzen, keine Markierung; die Skala haengt nur an sichtbaren Kerzen."""
        a = formation.bild(self.d, 0, "Watch the chart", markieren=False, n_vor=3)
        b = formation.bild(self.d, 0, "Watch the chart", markieren=False, n_vor=10)
        self.assertNotEqual(a.tobytes(), b.tobytes())

    def test_muster_kerzen_als_zahl(self):
        """Bot 9.36 liefert muster_kerzen als Anzahl (int)."""
        formation.bild(dict(self.d, muster_kerzen=2), 0, "BUY or SELL?")

    def test_format_name(self):
        from social import bericht
        self.assertEqual(bericht.format_aus_ordner("20261109-2130_formation_ZK_video"), "formation_video")
        self.assertIn("formation_video", bericht.NAMEN)


class CliffhangerTest(unittest.TestCase):
    """Entscheidung Tobias 10.11.2026: Aufloesung erst im naechsten Video, mit Community-Tipp."""

    def setUp(self):
        self.d = formation.laden(HIER / "beispieldaten")
        self.o = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.o, ignore_errors=True)

    def test_heute_ohne_aufloesung(self):
        folgen, tx = formation.szenen(self.d, self.o, "morgen")
        self.assertEqual(len(folgen), len(tx["zeilen"]))
        self.assertEqual(len(folgen), 4)   # Aufbau, Frage, Countdown, „Answer tomorrow“
        alles = " ".join(tx["zeilen"]) + tx["x"]
        self.assertIn("tomorrow", alles)
        self.assertNotIn("−8.7%", alles)        # Ergebnis wird heute nicht verraten
        self.assertNotIn("textbook was", alles.lower())
        self.assertTrue(tx["x"].endswith("Not financial advice."))

    def test_vorspann_mit_community(self):
        folgen, zeilen = formation.vorspann(self.d, self.o, {"n": 38, "mehrheit": "sell", "pct": 64})
        self.assertEqual(len(folgen), len(zeilen))
        self.assertEqual(len(folgen[0]), 7)      # Start + 6 Kerzen nacheinander
        self.assertIn("64% of 38 of you said SELL. You were right.", zeilen[1])   # ZK fiel −8.7 %
        self.assertIn("Without any pattern: 61%", zeilen[2])                     # Haken bleibt
        _, z2 = formation.vorspann(self.d, self.o, {"n": 25, "mehrheit": "buy", "pct": 56})
        self.assertIn("The chart said otherwise.", z2[1])
        _, z3 = formation.vorspann(self.d, self.o, None)       # unter der Mindestzahl: keine Prozentzahl
        self.assertNotIn("%  of", z3[1])
        self.assertNotIn("of you", z3[1])

    def test_video_mit_vorspann_tickt_am_richtigen_platz(self):
        gerufen = {}

        def sprechen(zeilen, ordner, cfg, key):
            gerufen["zeilen"] = zeilen
            return [self.o / f"t{i}.mp3" for i in range(len(zeilen))], [1.0] * len(zeilen), "probe"

        def schneiden(folgen, toene, dauern, ziel, cfg, texte=None, untertitel_y=None):
            gerufen["n"] = len(folgen)
            gerufen["toene"] = toene

        formation.video(self.d, self.o, CFG, {}, sprechen, schneiden, modus="morgen", gestern=self.d,
                        community={"n": 30, "mehrheit": "sell", "pct": 70})
        self.assertEqual(gerufen["n"], len(gerufen["zeilen"]))
        self.assertTrue(gerufen["zeilen"][3].startswith("Now today's pattern."))
        # Countdown = 3 Vorspann-Szenen + 2 -> Index 5 (Ticken scheitert hier an der Attrappe, darf nicht abbrechen)
        self.assertEqual(gerufen["zeilen"][5], "Comment your answer now.")

    def test_einstieg_wechselt(self):
        saetze = {formation.einstieg(dict(self.d, datum=f"2026-11-{t:02d}")) for t in range(1, 15)}
        self.assertGreater(len(saetze), 2)
        self.assertNotEqual(formation.saat(dict(self.d, datum="2026-11-11")),
                            formation.saat(dict(self.d, datum="2026-11-12")))


class GesternStandTest(unittest.TestCase):
    def test_aufloesung_nur_einmal(self):
        import types
        import main
        with tempfile.TemporaryDirectory() as t:
            alt = Path(t) / "20261110-2130_formation_ZK_video"
            alt.mkdir()
            d = formation.laden(HIER / "beispieldaten")
            (alt / "daten.json").write_text(json.dumps(d))
            schon = {"tag": "2026-11-10", "ordner": str(alt), "aufgeloest": False}
            (Path(t) / "formation_stand.json").write_text(json.dumps(schon))
            args = types.SimpleNamespace(out=t, daten=None)
            g, erg, hinweis = main._formation_gestern(args, CFG, {}, schon)
            self.assertEqual(g["coin"], "ZK")
            self.assertIsNone(erg)                         # nicht gepostet -> keine Prozentzahl
            self.assertIn("nicht gepostet", hinweis)
            neu = json.loads((Path(t) / "formation_stand.json").read_text())
            self.assertTrue(neu["aufgeloest"])
            self.assertIsNone(main._formation_gestern(args, CFG, {}, neu)[0])   # Freitag nicht noch einmal
