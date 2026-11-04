"""Wochenbericht: Haltequote der Reels (04.11.2026)."""
import unittest


class HaltequoteTest(unittest.TestCase):
    """04.11.2026: Haltequote Instagram-Reels mit Wort-Untertiteln gegen vorher."""
    def test_protokoll_merkt_video_und_quote(self):
        import json as _json
        import tempfile as _tf
        from pathlib import Path as _P
        from social import bericht as b
        with _tf.TemporaryDirectory() as d:
            o = _P(d) / "20261105-1430_markt_30s_video"
            o.mkdir()
            (o / "video_info.json").write_text(_json.dumps({"dauer": 20.0, "untertitel": "wort"}))
            prot = _P(d) / "protokoll.jsonl"
            b.protokollieren(prot, o.name, "gepostet", "instagram", "L1")
            b.protokollieren(prot, "20261101-1430_markt_30s_video", "gepostet", "instagram", "L2")
            p = b.protokoll_laden(prot)
        self.assertEqual(p[0]["video"], {"dauer": 20.0, "untertitel": "wort"})
        p[1]["video"] = {"dauer": 25.0}
        h = b.haltequote(p, {"L1": {"schnitt_ms": 14000}, "L2": {"schnitt_ms": 10000}})
        self.assertEqual(h, {"wort": [0.7], "vorher": [0.4]})
        t = "\n".join(b.haltequote_text(h))
        self.assertIn("Wort-Untertitel: 70 % (n = 1)", t)
        self.assertIn("zu wenige", t)
        t3 = "\n".join(b.haltequote_text({"wort": [0.7] * 3, "vorher": [0.4] * 3}))
        self.assertIn("+30 Prozentpunkte", t3)


class HakenTestTest(unittest.TestCase):
    def test_tage_wechseln_und_abschaltbar(self):
        import datetime as dt
        from social import sprache
        a, b = sprache.haken_art(dt.date(2026, 11, 5), True), sprache.haken_art(dt.date(2026, 11, 6), True)
        self.assertEqual({a, b}, {"frage", "zahl"})
        self.assertEqual(sprache.haken_art(dt.date(2026, 11, 6), False), "frage")

    def test_wal_und_lernen_beide_varianten(self):
        from unittest import mock
        from social import sprache, wal, wissen
        w = {"base": "ABC", "wal": 12.5, "wal_7d": 2.4}
        with mock.patch.object(sprache, "haken_art", lambda tag=None: "zahl"):
            z = wal.video_szenen(w, "en")["szenen"][0]
            t = wissen.themen()[0]
            lz = wissen.video_szenen(t, "en")["szenen"][0]
        self.assertTrue(z["vorlage"].startswith("Whales raised their share of ABC"))
        self.assertEqual(lz["vorlage"], t["titel"].rstrip(".") + ".")
        with mock.patch.object(sprache, "haken_art", lambda tag=None: "frage"):
            f = wal.video_szenen(w, "en")["szenen"][0]
            lf = wissen.video_szenen(t, "en")["szenen"][0]
        self.assertEqual((f["haken"], f["daten"]["_frage"]), ("frage", "WHAT ARE WHALES DOING?"))
        self.assertEqual(lf["vorlage"], t["haken"])

    def test_bericht_nach_haken(self):
        from social import bericht as b
        p = [{"ereignis": "gepostet", "kanal": "instagram", "link": "L1", "video": {"dauer": 20, "haken": "frage"}},
             {"ereignis": "gepostet", "kanal": "instagram", "link": "L2", "video": {"dauer": 20, "haken": "zahl"}},
             {"ereignis": "gepostet", "kanal": "instagram", "link": "L3", "video": {"dauer": 20}}]
        ig = {k: {"schnitt_ms": 10000} for k in ("L1", "L2", "L3")}
        self.assertEqual(b.haltequote(p, ig, "haken"), {"frage": [0.5], "zahl": [0.5]})
        self.assertIn("Einstieg Frage: 50 %", "\n".join(b.haltequote_text(b.haltequote(p, ig, "haken"))))


class FrageUndKommentarTest(unittest.TestCase):
    def test_x_beginnt_mit_frage_nur_am_frage_tag(self):
        from social import post
        b = {"szenen": [{"haken": "frage", "vorlage": "Why did BAT jump +52.8% in 24 hours? Here is what moved."}]}
        self.assertEqual(post.frage_vorne("Crypto market\nNot financial advice.", b),
                         "Why did BAT jump +52.8% in 24 hours?\nCrypto market\nNot financial advice.")
        b["szenen"][0]["haken"] = "zahl"
        self.assertEqual(post.frage_vorne("X", b), "X")
        b["szenen"][0]["haken"] = "frage"
        self.assertEqual(post.frage_vorne("x" * 270, b), "x" * 270)   # passt nicht -> unveraendert

    def test_claude_laesst_haken_und_kommentar_frage(self):
        from unittest import mock
        from social import texte
        b = {"sprache": "en", "fakten": {}, "szenen": [{"typ": "haken", "daten": {}, "vorlage": "Why did X jump?"},
                                                       {"typ": "mover", "daten": {}, "vorlage": "mitte"},
                                                       {"typ": "outro", "daten": {}, "vorlage": "Comment below."}]}

        class R:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"content": [{"type": "text", "text": '{"zeilen": ["A", "B", "C"]}'}], "stop_reason": "end_turn"}
        cfg = {"text": {"modell": "m", "max_woerter": 80}, "video": {}}
        with mock.patch.object(texte.requests, "post", return_value=R()):
            z, q = texte.schreiben(b, cfg, "k")
        self.assertEqual((q, z), ("claude", ["Why did X jump?", "B", "Comment below."]))


if __name__ == "__main__":
    unittest.main()
