"""Folge-Liste (Wunsch Tobias 31.10.2026): X per Knopf ueber die Schnittstelle, andere Plattformen per Link."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from social import folgen

HIER = Path(__file__).resolve().parent.parent
G = {"x_api_key": "a", "x_api_secret": "b", "x_access_token": "c", "x_access_secret": "d"}
KONTEN = [{"plattform": "x", "name": "glassnode", "warum": "On-Chain"},
          {"plattform": "x", "name": "gibtsnicht123", "warum": "?"},
          {"plattform": "x", "name": "CoinDesk", "warum": "News"},
          {"plattform": "instagram", "name": "watcher.guru", "warum": "Eil"},
          {"plattform": "youtube", "name": "benjaminjcowen", "warum": "Zyklen"}]


class Antwort:
    def __init__(self, j, code=200):
        self._j, self.status_code, self.content, self.text = j, code, b"x", json.dumps(j)

    def json(self):
        return self._j


class FolgenTest(unittest.TestCase):
    def test_liste_im_repo_ist_gueltig(self):
        k = folgen.liste()
        self.assertGreaterEqual(len([x for x in k if x["plattform"] == "x"]), 10)
        schon = {"kobeissiletter", "watcherguru", "whale_alert", "lookonchain"}   # schon von Hand gefolgt
        self.assertFalse(schon & {x["name"].lower() for x in k if x["plattform"] == "x"})
        self.assertEqual(len({(x["plattform"], x["name"].lower()) for x in k}), len(k))   # keine Doppelten

    def test_auswahl_ueberspringt_erledigte(self):
        a = folgen.auswahl(KONTEN, {"erledigt": {"x:glassnode": 1}}, n_x=1, n_andere=5)
        self.assertEqual([k["name"] for k in a["x"]], ["gibtsnicht123"])
        self.assertEqual([k["plattform"] for k in a["andere"]], ["instagram", "youtube"])

    def test_nachricht_mit_knoepfen_und_links(self):
        a = folgen.auswahl(KONTEN, {}, n_x=3)
        text, k = folgen.nachricht(a, "2026-10-31")
        self.assertIn('href="https://x.com/glassnode"', text)
        self.assertIn('href="https://www.instagram.com/watcher.guru/"', text)
        self.assertIn('href="https://www.youtube.com/@benjaminjcowen"', text)
        daten = [b["callback_data"] for b in k["inline_keyboard"][0]]
        self.assertEqual(daten, ["f|x|2026-10-31", "f|ok|2026-10-31"])
        self.assertTrue(all(len(d) <= 64 for d in daten))
        t, k = folgen.nachricht({"x": [], "andere": []}, "2026-10-31")
        self.assertIsNone(k)

    def test_x_folgen(self):
        aufrufe = []

        def anfrage(methode, url, json=None, timeout=None, headers=None):
            aufrufe.append((methode, url, json))
            self.assertTrue(headers["Authorization"].startswith("OAuth "))
            if url.endswith("/users/me"):
                return Antwort({"data": {"id": "999"}})
            if "/users/by?" in url:
                return Antwort({"data": [{"id": "1", "username": "glassnode"}, {"id": "3", "username": "CoinDesk"}]})
            if url.endswith("/users/999/following"):
                if json["target_user_id"] == "3":
                    return Antwort({"title": "Too Many Requests"}, 429)
                return Antwort({"data": {"following": True, "pending_follow": False}})
            return Antwort({}, 404)
        stand = {}
        z = folgen.x_folgen(G, ["glassnode", "gibtsnicht123", "CoinDesk"], stand, anfrage=anfrage,
                            warten=lambda s: None)
        self.assertEqual(stand["x_eigene_id"], "999")
        q = parse_qs(urlparse(next(u for m, u, j in aufrufe if "/users/by?" in u)).query)
        self.assertEqual(q["usernames"], ["glassnode,gibtsnicht123,CoinDesk"])
        self.assertEqual(z[0], "✅ @glassnode")
        self.assertIn("nicht gefunden", z[1])
        self.assertTrue(z[2].startswith("❌ @CoinDesk: 429"))
        self.assertIn("morgen", z[3])
        self.assertIn("x:glassnode", stand["erledigt"])
        self.assertNotIn("x:coindesk", stand["erledigt"])   # Limit: bleibt fuer morgen offen
        folgen.x_folgen(G, ["glassnode"], stand, anfrage=anfrage, warten=lambda s: None)
        self.assertEqual(sum(1 for m, u, j in aufrufe if u.endswith("/users/me")), 1)   # eigene ID gemerkt

    def test_ohne_x_schluessel(self):
        with self.assertRaises(folgen.FolgenFehler):
            folgen.x_folgen({}, ["a"], {})


class KnopfTest(unittest.TestCase):
    def test_taegliche_liste_und_knopf_andere_erledigt(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["SOCIAL_AUSGABE"] = d
            os.environ["SOCIAL_GEHEIM"] = d
            try:
                import importlib
                import sys
                sys.path.insert(0, str(HIER / "tools"))
                import folgen as werkzeug
                import freigabe
                importlib.reload(werkzeug)
                importlib.reload(freigabe)
                gesendet = []
                (Path(d) / "secrets.yaml").write_text(yaml.safe_dump({"telegram_token": "t", "telegram_chat_id": 1}))
                werkzeug.main(senden=lambda url, data=None, timeout=None: gesendet.append(data))
                self.assertIn("reply_markup", gesendet[0])
                datum = folgen.heute()
                stand = folgen.stand_laden(Path(d) / "folgen_stand.json")
                self.assertEqual(len(stand["heute"][datum]["x"]), 10)
                self.assertIn("erledigt", freigabe.folge_knopf({}, "ok", datum))
                stand = folgen.stand_laden(Path(d) / "folgen_stand.json")
                self.assertEqual(len(stand["erledigt"]), 5)
                self.assertIn("X-Schlüssel fehlen", freigabe.folge_knopf({}, "x", datum))
                self.assertIn("zu alt", freigabe.folge_knopf({}, "x", "2020-01-01"))
            finally:
                os.environ.pop("SOCIAL_AUSGABE")
                os.environ.pop("SOCIAL_GEHEIM")


if __name__ == "__main__":
    unittest.main()


class AnTobiasTest(unittest.TestCase):
    """Fehler 02.11.2026: Folge-Liste kam nie an, niemand merkte es. Jetzt: Antwort pruefen, ohne HTML nochmal."""

    def test_html_abgelehnt_dann_ohne_formatierung(self):
        from social import telegram
        gesehen = []

        class A:
            def __init__(self, j):
                self.j = j

            def json(self):
                return self.j

        def post(url, data=None, timeout=None):
            gesehen.append(data)
            return A({"ok": False, "description": "can't parse entities"} if "parse_mode" in data else {"ok": True})
        g = {"telegram_token": "t", "telegram_chat_id": 1}
        self.assertEqual(telegram.an_tobias(g, "<b>Folge-Liste</b> <x>", post=post), "ok")
        self.assertEqual(len(gesehen), 2)
        self.assertEqual(gesehen[1]["text"], "Folge-Liste ")
        self.assertIn("fehlt", telegram.an_tobias({}, "x", post=post))
