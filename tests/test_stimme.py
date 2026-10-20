import unittest
from unittest import mock

from social import stimme


class Antwort:
    def __init__(self, daten):
        self.daten = daten

    def raise_for_status(self):
        pass

    def json(self):
        return self.daten


class StimmeTest(unittest.TestCase):
    def test_findet_stimme_per_name(self):
        cfg = {"stimme": {"voice_name": "WhaleSqueeze DE", "voice_id": None}}
        liste = {"voices": [{"name": "Bill", "voice_id": "a1"}, {"name": "WhaleSqueeze DE", "voice_id": "b2"}]}
        with mock.patch.object(stimme.requests, "get", return_value=Antwort(liste)):
            self.assertEqual(stimme.voice_id(cfg, "k"), "b2")

    def test_fehlende_stimme_meldet_fehler(self):
        cfg = {"stimme": {"voice_name": "WhaleSqueeze DE", "voice_id": None}}
        with mock.patch.object(stimme.requests, "get", return_value=Antwort({"voices": []})):
            with self.assertRaises(stimme.StimmeFehlt):
                stimme.voice_id(cfg, "k")

    def test_feste_id_hat_vorrang(self):
        cfg = {"stimme": {"voice_name": "egal", "voice_id": "fest"}}
        self.assertEqual(stimme.voice_id(cfg, "k"), "fest")


if __name__ == "__main__":
    unittest.main()
