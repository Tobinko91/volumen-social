import unittest
import yaml
from pathlib import Path
from social import daten, formate, pruefung, texte

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
D = daten.laden(HIER / "beispieldaten")


class PruefungTest(unittest.TestCase):
    def test_vorlage_besteht(self):
        b = formate.markt_30s(D, set())
        assert pruefung.pruefen(texte.vorlage(b), b, CFG, set()) == []

    def test_erfundene_zahl_faellt_durch(self):
        b = formate.markt_30s(D, set())
        z = texte.vorlage(b); z[1] = "The median coin moved 99.9 percent."
        assert any("99.9" in f for f in pruefung.pruefen(z, b, CFG, set()))

    def test_verbotene_wendung(self):
        b = formate.markt_30s(D, set())
        z = texte.vorlage(b); z[-1] = "Buy now before it is too late."
        assert any("buy now" in f for f in pruefung.pruefen(z, b, CFG, set()))

    def test_sperrliste_wird_uebersprungen(self):
        b = formate.markt_30s(D, {"BAT"})
        assert all(m["base"] != "BAT" for m in b["fakten"]["mover"])


if __name__ == "__main__":
    unittest.main()
