"""„First on Telegram“ (Wunsch Tobias 31.10.2026): Hinweis auf den Telegram-Kanal auf X, Instagram und TikTok."""
import unittest

from social import kanaele, tiktok

G = {"telegram_kanal": "@whalesqueeze"}
TG = "📰 <b>Fed holds rates</b>\n\n• Point one\n\n<i>Not financial advice.</i>"


class TelegramFirstTest(unittest.TestCase):
    def test_instagram_und_tiktok_immer(self):
        t = kanaele.telegram_hinweis(TG, "instagram", G)
        self.assertIn("⚡ Live alerts first on Telegram: t.me/whalesqueeze", t)
        self.assertTrue(t.endswith("<i>Not financial advice.</i>"))   # Pflicht-Hinweis bleibt letzte Zeile
        self.assertIn("t.me/whalesqueeze", kanaele.instagram_text(t))
        self.assertIn("t.me/whalesqueeze", tiktok.titel_und_text(kanaele.telegram_hinweis(TG, "tiktok", G))[1])
        self.assertEqual(kanaele.telegram_hinweis(t, "instagram", G), t)   # nie doppelt

    def test_x_nur_bei_eilmeldung_ohne_link(self):
        normal = "Fed holds rates.\nNot financial advice."
        self.assertEqual(kanaele.telegram_hinweis(normal, "x", G), normal)
        eil = "🚨 BREAKING: Binance hacked.\nNot financial advice."
        t = kanaele.telegram_hinweis(eil, "x", G)
        self.assertEqual(t, "🚨 BREAKING: Binance hacked.\n⚡ Live alerts first on Telegram (link in bio)\n"
                            "Not financial advice.")
        self.assertNotIn("t.me", t)
        lang = "🚨 " + "x" * 250 + "\nNot financial advice."
        self.assertEqual(kanaele.telegram_hinweis(lang, "x", G), lang)   # passt nicht -> unveraendert

    def test_telegram_selbst_unveraendert_und_ohne_kanalname(self):
        self.assertEqual(kanaele.telegram_hinweis(TG, "telegram", G), TG)
        t = kanaele.telegram_hinweis(TG, "instagram", {"telegram_kanal": "-1001234"})
        self.assertIn("⚡ Live alerts first on Telegram\n", t)
        self.assertNotIn("t.me", t)


if __name__ == "__main__":
    unittest.main()


class VorschlagZustellungTest(unittest.TestCase):
    """03.11.2026: Vorschlag aus der Warteschlange kam nicht an. Jetzt: jede Antwort pruefen, sonst False."""

    def test_abgelehnt_gibt_false(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        from social import telegram

        class A:
            ok = True

            def __init__(self, j):
                self.j = j

            def json(self):
                return self.j
        with tempfile.TemporaryDirectory() as d:
            o = Path(d)
            (o / "post.png").write_bytes(b"x")
            (o / "post_telegram.txt").write_text("<b>T</b>")
            (o / "post_x.txt").write_text("T")
            with mock.patch.object(telegram.requests, "post",
                                   return_value=A({"ok": False, "description": "can't parse entities"})):
                self.assertFalse(telegram.vorschlag_senden({"telegram_token": "t", "telegram_chat_id": 1}, o))
            with mock.patch.object(telegram.requests, "post", return_value=A({"ok": True})):
                self.assertTrue(telegram.vorschlag_senden({"telegram_token": "t", "telegram_chat_id": 1}, o))
