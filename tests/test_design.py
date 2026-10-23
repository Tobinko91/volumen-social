import unittest

from social import design


class DesignTest(unittest.TestCase):
    def test_schrift_und_logo_vorhanden(self):
        for g in ("Regular", "Medium", "SemiBold", "Bold"):
            self.assertGreater(design.font(g, 30).getlength("Größe −50 % 1.000 €"), 50)
        self.assertEqual(design.logo(64).size, (64, 64))

    def test_hintergruende_wechseln(self):
        tage = [f"2026-11-{t:02d}" for t in range(1, 15)]
        themen = {design.thema_waehlen("wissen", f"{t}:risiko").name for t in tage}
        self.assertGreaterEqual(len(themen), 3)

    def test_markt_nie_auf_heller_minze(self):
        for t in range(60):
            self.assertNotEqual(design.thema_waehlen("markt", str(t)).name, "minze")

    def test_zahl_und_einheit_bleiben_zusammen(self):
        from PIL import Image, ImageDraw
        d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        z = design.umbruch(d, "Warum −50 % ganze +100 % brauchen", design.font("Bold", 66), 420)
        self.assertFalse(any(x.startswith("%") for x in z))


    def test_ueberall_nur_keine_anlageberatung(self):
        import yaml
        from pathlib import Path
        cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text())
        alles = " ".join(str(v) for v in cfg["hinweise"].values())
        for weg in ("KI-erstellt", "Totalverlust", "Betreiber"):
            self.assertNotIn(weg, alles)


if __name__ == "__main__":
    unittest.main()
