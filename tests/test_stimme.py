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



class GoogleStimmeTest(unittest.TestCase):
    """Chirp 3 HD (Wunsch Tobias 01.11.2026): Anfrage, Schluessel, Rueckfall auf Stille bei Fehler."""
    CFG = {"stimme": {"aktiv": True, "anbieter": "google", "google_stimme": "en-US-Chirp3-HD-Charon", "tempo": 1.08},
           "video": {"min_szene_s": 1.5, "woerter_pro_sekunde": 2.6}}

    def test_schluessel_je_anbieter(self):
        g = {"google_tts_key": "gk", "elevenlabs_api_key": "ek"}
        self.assertEqual(stimme.schluessel(self.CFG, g), "gk")
        self.assertEqual(stimme.schluessel({"stimme": {"anbieter": "elevenlabs"}}, g), "ek")

    def test_anfrage(self):
        import base64
        import tempfile
        from pathlib import Path
        gesehen = {}

        class R:
            status_code = 200

            def json(self):
                return {"audioContent": base64.b64encode(b"ID3mp3").decode()}

        def post(url, params=None, json=None, timeout=None):
            gesehen.update(url=url, params=params, json=json)
            return R()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.mp3"
            stimme._google("Bitcoin is up +2.1%.", f, self.CFG, "gk", post=post)
            self.assertEqual(f.read_bytes(), b"ID3mp3")
        self.assertEqual(gesehen["params"], {"key": "gk"})
        self.assertEqual(gesehen["json"]["voice"], {"languageCode": "en-US", "name": "en-US-Chirp3-HD-Charon"})
        self.assertEqual(gesehen["json"]["audioConfig"]["speakingRate"], 1.08)

    def test_fehler_gibt_stille_statt_abbruch(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(stimme, "_google", side_effect=stimme.StimmeFehlt("403 API not enabled")):
            dateien, dauern, quelle = stimme.sprechen(["One two three."], Path(d), self.CFG, "gk")
            self.assertTrue(quelle.startswith("stille (Stimme fehlgeschlagen"))
            self.assertEqual(dateien[0].suffix, ".m4a")

    def test_ohne_schluessel_still(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(stimme.sprechen(["a b"], Path(d), self.CFG, None)[2], "stille")


class OpenAIStimmeTest(unittest.TestCase):
    """Entscheidung Tobias 03.11.2026: Stimme von OpenAI."""

    def test_anfrage_und_schluessel(self):
        import tempfile
        from pathlib import Path
        cfg = {"stimme": {"aktiv": True, "anbieter": "openai", "openai_stimme": "cedar", "openai_modell": "gpt-4o-mini-tts"}}
        self.assertEqual(stimme.schluessel(cfg, {"openai_api_key": "ok", "google_tts_key": "g"}), "ok")
        gesehen = {}

        class R:
            status_code = 200
            content = b"ID3mp3"

        def post(url, headers=None, json=None, timeout=None):
            gesehen.update(url=url, headers=headers, json=json)
            return R()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.mp3"
            stimme._openai("Bitcoin is up +2.1%.", f, cfg, "ok", post=post)
            self.assertEqual(f.read_bytes(), b"ID3mp3")
        self.assertEqual(gesehen["url"], stimme.OPENAI_TTS)
        self.assertEqual(gesehen["headers"]["Authorization"], "Bearer ok")
        self.assertEqual((gesehen["json"]["voice"], gesehen["json"]["model"]), ("cedar", "gpt-4o-mini-tts"))
        self.assertIn("instructions", gesehen["json"])

    def test_konfiguration(self):
        import yaml
        from pathlib import Path
        cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(cfg["stimme"]["anbieter"], "openai")


if __name__ == "__main__":
    unittest.main()
