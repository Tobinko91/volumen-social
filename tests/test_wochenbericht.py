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


if __name__ == "__main__":
    unittest.main()
