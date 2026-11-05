"""Umfragen unter Hot Topics (Wunsch Tobias 05.11.2026)."""
import json
import tempfile
import unittest
from pathlib import Path

from social import umfrage


class A:
    def __init__(self, j, code=200):
        self._j, self.status_code, self.text = j, code, json.dumps(j)

    def json(self):
        return self._j


class UmfrageTest(unittest.TestCase):
    def test_laden_kuerzt_fuer_x(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(umfrage.laden(Path(d)))
            (Path(d) / "umfrage.json").write_text(json.dumps({"frage": "Deal or more strikes?",
                                                             "optionen": ["Deal", "More strikes", "x" * 40]}))
            u = umfrage.laden(Path(d))
        self.assertEqual(u["optionen"][2], "x" * 25)
        self.assertEqual(u["stunden"], 24)

    def test_telegram_und_x_antwort(self):
        g = {"telegram_token": "t", "telegram_kanal": "@whalesqueeze",
             **{k: "v" for k in ("x_api_key", "x_api_secret", "x_access_token", "x_access_secret")}}
        u = {"frage": "Deal or more strikes?", "optionen": ["Deal", "More strikes"], "stunden": 24}
        gesehen = {}

        def tg(url, data=None, timeout=None):
            gesehen["tg"] = (url.rsplit("/", 1)[-1], data)
            return A({"ok": True, "result": {"message_id": 9}})
        self.assertEqual(umfrage.telegram(g, u, post=tg), "https://t.me/whalesqueeze/9")
        self.assertEqual(gesehen["tg"][0], "sendPoll")

        def xp(url, headers=None, json=None, timeout=None):
            gesehen["x"] = json
            return A({"data": {"id": "77"}})
        link = umfrage.x(g, u, "https://x.com/i/web/status/12345", post=xp)
        self.assertEqual(gesehen["x"]["reply"]["in_reply_to_tweet_id"], "12345")
        self.assertEqual(gesehen["x"]["poll"]["duration_minutes"], 1440)
        self.assertIn("77", link)


if __name__ == "__main__":
    unittest.main()
