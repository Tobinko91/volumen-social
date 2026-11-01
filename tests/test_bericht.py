"""Punkt E (01.11.2026): Wochenbericht – Protokoll, Zahlen, Empfehlung."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from social import bericht

HIER = Path(__file__).resolve().parent.parent
JETZT = 1793548800   # So 01.11.2026


class Antwort:
    def __init__(self, j, code=200):
        self._j, self.status_code = j, code

    def json(self):
        return self._j


class BerichtTest(unittest.TestCase):
    def test_format_aus_ordner(self):
        self.assertEqual(bericht.format_aus_ordner("20261101-1430_markt_30s_video"), "markt_video")
        self.assertEqual(bericht.format_aus_ordner("20261101-1430_markt_30s"), "markt")
        self.assertEqual(bericht.format_aus_ordner("20261101-1900_wal_BAT"), "wal")
        self.assertEqual(bericht.format_aus_ordner("20261101-1900_wal_BAT_video"), "wal_video")
        self.assertEqual(bericht.format_aus_ordner("20261101-1500_news"), "news")
        self.assertEqual(bericht.format_aus_ordner("chat_20261030-binance-hack"), "redaktion")

    def test_protokoll_und_auswertung(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "protokoll.jsonl"
            for i in range(3):
                bericht.protokollieren(p, f"2026103{i}-1430_markt_30s_video", "gepostet", "x",
                                       f"https://x.com/i/web/status/{i}", jetzt=JETZT - 1000)
                bericht.protokollieren(p, f"2026103{i}-1500_news", "gepostet", "x",
                                       f"https://x.com/i/web/status/1{i}", jetzt=JETZT - 1000)
            bericht.protokollieren(p, "20261031-1600_coincheck", "verworfen", jetzt=JETZT - 1000)
            bericht.protokollieren(p, "20261001-1600_coincheck", "gepostet", "x", "alt", jetzt=JETZT - 30 * 86400)
            prot = bericht.protokoll_laden(p, seit=JETZT - bericht.WOCHE)
            self.assertEqual(len(prot), 7)   # der alte Eintrag zaehlt nicht
            x = {f"https://x.com/i/web/status/{i}": {"aufrufe": 900 + i} for i in range(3)}
            x.update({f"https://x.com/i/web/status/1{i}": {"aufrufe": 100} for i in range(3)})
            f = bericht.auswerten(prot, x, {})
            self.assertEqual(f["markt_video"]["x_mittel"], 901)
            self.assertEqual(f["news"]["beitraege"], 3)
            self.assertEqual(f["coincheck"]["verworfen"], 1)
            e = bericht.empfehlung(f)
            self.assertTrue(e[0].startswith("📈 Ausbauen: Markt (Video)"))
            self.assertTrue(any("Prüfen: News" in z for z in e))
            t = bericht.text(f, {"telegram": 120, "x": 300}, {"telegram": 100}, bericht.top_beitraege(prot, x, {}),
                             JETZT)
            self.assertIn("Telegram: 120 (+20)", t)
            self.assertIn("Top-Beiträge", t)
            self.assertNotIn("percent", t)

    def test_x_zahlen_ein_abruf(self):
        aufrufe = []

        def get(methode, url, headers=None, timeout=None):
            aufrufe.append(url)
            if "/2/tweets?" in url:
                return Antwort({"data": [{"id": "5", "public_metrics": {"impression_count": 1234, "like_count": 9}}]})
            return Antwort({"data": {"public_metrics": {"followers_count": 321}}})
        g = {"x_api_key": "a", "x_api_secret": "b", "x_access_token": "c", "x_access_secret": "d"}
        x, f = bericht.x_zahlen(g, ["https://x.com/i/web/status/5", "kein-link"], get=get)
        self.assertEqual(x["https://x.com/i/web/status/5"]["aufrufe"], 1234)
        self.assertEqual(f, 321)
        self.assertEqual(sum("/2/tweets?" in u for u in aufrufe), 1)

    def test_instagram_zahlen(self):
        def ig(methode, pfad, token, **params):
            if pfad == "me":
                return {"user_id": "17", "followers_count": 55}
            if pfad.endswith("/media"):
                return {"data": [{"id": "m1", "permalink": "https://www.instagram.com/p/a/", "like_count": 4}]}
            return {"data": [{"name": "views", "values": [{"value": 800}]}, {"name": "saved", "values": [{"value": 7}]}]}
        z, f = bericht.instagram_zahlen({"instagram_token": "t"}, ig=ig)
        self.assertEqual(f, 55)
        self.assertEqual(z["https://www.instagram.com/p/a/"]["aufrufe"], 800)
        self.assertEqual(z["https://www.instagram.com/p/a/"]["gespeichert"], 7)

    def test_werkzeug_und_freigabe_protokolliert(self):
        import importlib
        with tempfile.TemporaryDirectory() as d:
            os.environ["SOCIAL_AUSGABE"] = d
            os.environ["SOCIAL_GEHEIM"] = d
            try:
                sys.path.insert(0, str(HIER / "tools"))
                import freigabe
                import wochenbericht
                importlib.reload(freigabe)
                importlib.reload(wochenbericht)
                o = Path(d) / "20261101-1430_markt_30s"
                o.mkdir()
                (o / "post.png").write_bytes(b"x")
                (o / "post_telegram.txt").write_text("t")
                (o / "post_x.txt").write_text("x")
                freigabe.posten({}, o.name, "nein")
                prot = bericht.protokoll_laden(Path(d) / "protokoll.jsonl")
                self.assertEqual(prot[0]["ereignis"], "verworfen")
                gesendet = []
                t = wochenbericht.main(jetzt=prot[0]["ts"] + 10, x_holen=lambda: ({}, 10), ig_holen=lambda: ({}, 20),
                                       tg_holen=lambda: 30, senden=lambda g, text: gesendet.append(text))
                self.assertIn("Wochenbericht", t)
                self.assertEqual(gesendet, [t])
                stand = json.loads((Path(d) / "bericht_stand.json").read_text())
                self.assertEqual(stand["follower"]["telegram"], 30)
            finally:
                os.environ.pop("SOCIAL_AUSGABE")
                os.environ.pop("SOCIAL_GEHEIM")

    def test_plan_sonntags(self):
        plan = (HIER / "tools/plan.sh").read_text()
        self.assertIn('[ "$SLOT" = "18:30" ] && [ "$(date +%u)" = "7" ]', plan)


if __name__ == "__main__":
    unittest.main()
