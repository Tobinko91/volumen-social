"""S18 News-Radar (Telegram-Vorschau, X-Konten, zweite Quelle) und S19 Krypto-Zeile unter Makro-News."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

import main
from social import news, news_post, pruefung

HIER = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((HIER / "config.yaml").read_text())
TG = (HIER / "tests/feeds/telegram.html").read_text()
JETZT = 1793210000  # 28.10.2026 ca. 19:13 UTC
WG = {"name": "Watcher Guru", "art": "telegram", "radar": True, "filter": "markt", "gewicht": 0.8}
WA = {"name": "Whale Alert", "art": "telegram", "radar": True, "filter": "krypto", "primaer_ab_usd": 100_000_000}
MARKT = {"median_24h": -0.8, "anteil_plus": 41, "anzahl": 312, "quelle": "bot", "btc_24h": 1.2}


def wal_html(n, usd):
    return (f'<div data-post="whale_alert_io/{n}"><div class="tgme_widget_message_text js-message_text">'
            f'🚨 2,000 #BTC ({usd} USD) transferred from unknown wallet to #Coinbase</div>'
            f'<time datetime="2026-10-28T18:00:00+00:00"></time></div>')


def meldung(quelle, titel, radar=False, **k):
    return dict({"quelle": quelle, "titel": titel, "kurz": "", "link": f"https://x/{quelle}/{titel[:9]}",
                 "ts": JETZT, "gewicht": 1.0, "radar": radar}, **k)


class TelegramTest(unittest.TestCase):
    def test_vorschau_wird_gelesen_und_klatsch_gefiltert(self):
        m = news.parse_telegram(TG, WG)
        self.assertEqual(len(m), 1)   # Klatsch weg (kein Markt-Thema), Bild ohne Text weg
        self.assertEqual(m[0]["link"], "https://t.me/WatcherGuru/9001")
        self.assertIn("Fed holds interest rates", m[0]["titel"])
        self.assertIn("2:30 pm ET", m[0]["kurz"])
        self.assertTrue(m[0]["radar"])
        self.assertAlmostEqual(m[0]["ts"], 1793210460, delta=1)

    def test_whale_alert_primaer_erst_ab_100_mio(self):
        gross = news.parse_telegram(wal_html(1, "160,000,000"), WA)[0]
        klein = news.parse_telegram(wal_html(2, "16,000,000"), WA)[0]
        self.assertTrue(gross["primaer"])
        self.assertFalse(klein["primaer"])


class BestaetigungTest(unittest.TestCase):
    def test_radar_allein_reicht_nicht(self):
        g = news.buendeln([meldung("Watcher Guru", "Fed holds interest rates steady at 3.75%", radar=True)])
        self.assertFalse(g[0]["bestaetigt"])

    def test_radar_plus_zweite_quelle(self):
        g = news.buendeln([meldung("Watcher Guru", "Fed holds interest rates steady", radar=True),
                           meldung("CoinDesk", "Fed holds interest rates steady, bitcoin flat")])
        self.assertEqual(len(g), 1)
        self.assertTrue(g[0]["bestaetigt"])
        self.assertTrue(g[0]["makro"])

    def test_zwei_radar_konten_oder_primaerdaten(self):
        g = news.buendeln([meldung("Watcher Guru", "Fed holds interest rates steady", radar=True),
                           meldung("Walter Bloomberg", "Fed holds interest rates steady", radar=True)])
        self.assertTrue(g[0]["bestaetigt"])
        g = news.buendeln([meldung("Whale Alert", "2,000 BTC transferred", radar=True, primaer=True)])
        self.assertTrue(g[0]["bestaetigt"])

    def test_news_lauf_postet_radar_allein_nicht(self):
        def laden(url):
            if "WatcherGuru" in url:
                return TG
            raise OSError("offline")
        aufrufe = []
        with tempfile.TemporaryDirectory() as d:
            orig = news.einsammeln
            news.einsammeln = lambda laden=None, **k: orig(jetzt=JETZT, laden=laden, **k)
            try:
                args = types.SimpleNamespace(out=d, eil=False, senden=False, daten=None)
                r = main.news_beitrag(args, CFG, {}, set(), laden=laden, schreiber=lambda g: aufrufe.append(g))
            finally:
                news.einsammeln = orig
        self.assertEqual(r, 0)
        self.assertEqual(aufrufe, [])   # Claude wurde gar nicht erst gefragt


class XRadarTest(unittest.TestCase):
    KONTEN = [{"name": "The Kobeissi Letter", "x": "KobeissiLetter", "radar": True, "filter": "markt"},
              {"name": "Lookonchain", "x": "lookonchain", "radar": True, "filter": "krypto"}]
    G = {"x_api_key": "a", "x_api_secret": "b", "x_access_token": "c", "x_access_secret": "d"}

    def test_eine_suche_fuer_alle_konten(self):
        gesehen = []

        class A:
            status_code = 200

            def json(self):
                return {"data": [
                    {"id": "1", "author_id": "11", "created_at": "2026-10-28T17:00:00.000Z",
                     "text": "BREAKING: The Fed is set to hold rates at 3.75%-4.00% today.\nhttps://t.co/abc"},
                    {"id": "2", "author_id": "11", "created_at": "2026-10-28T16:00:00.000Z",
                     "text": "Boeing stock falls 10% after earnings."},
                    {"id": "3", "author_id": "22", "created_at": "2026-10-28T15:00:00.000Z",
                     "text": "A whale bought 5,000 ETH ($19.5M) in the last hour."}],
                    "includes": {"users": [{"id": "11", "username": "KobeissiLetter"},
                                           {"id": "22", "username": "lookonchain"}]}}

        def get(url, timeout=None, headers=None):
            gesehen.append((url, headers))
            return A()
        m = news.x_radar(self.KONTEN, self.G, jetzt=JETZT, get=get)
        self.assertEqual(len(gesehen), 1)
        q = parse_qs(urlparse(gesehen[0][0]).query)
        self.assertIn("from:KobeissiLetter OR from:lookonchain", q["query"][0])
        self.assertIn("-is:retweet", q["query"][0])
        self.assertTrue(gesehen[0][1]["Authorization"].startswith("OAuth "))
        self.assertEqual([x["quelle"] for x in m], ["The Kobeissi Letter", "Lookonchain"])   # Boeing: kein Markt-Thema
        self.assertEqual(m[0]["link"], "https://x.com/KobeissiLetter/status/1")
        self.assertNotIn("t.co", m[0]["titel"] + m[0]["kurz"])

    def test_x_aus_kostet_nichts(self):
        self.assertFalse(CFG["radar"]["x_lesen"])
        _, status = news.einsammeln(jetzt=JETZT, laden=lambda u: (_ for _ in ()).throw(OSError()))
        self.assertTrue(any(k.startswith("X-Radar") and v.startswith("aus") for k, v in status.items()))


class KryptoZeileTest(unittest.TestCase):
    D = {"geeignet": True, "rubrik": "Macro", "schlagzeile": "Fed holds rates at 3.75% to 4.00%",
         "kernsatz": "The Fed kept its target range at 3.75% to 4.00% on Wednesday, October 28.",
         "punkte": ["Chair Kevin Warsh speaks at 2:30 p.m. ET.", "The next meeting is on December 8 and 9."],
         "x": "The Fed kept rates at 3.75% to 4.00% on Oct 28. Warsh speaks at 2:30 p.m. ET.", "coins": []}

    def test_zeile_nur_aus_bot_daten(self):
        k = news_post.krypto_zeile(MARKT, "en")
        self.assertEqual(k["lang"], "In the small caps we track (312 coins), 41% are up over 24h, median -0.8%. "
                                    "Bitcoin: +1.2% in 24h.")
        self.assertIsNone(news_post.krypto_zeile(None, "en"))
        self.assertIsNone(news_post.krypto_zeile({"median_24h": None, "anteil_plus": 3}, "en"))
        self.assertIn("41 %", news_post.krypto_zeile(MARKT, "de")["lang"])

    def test_makro_erkennung(self):
        self.assertTrue(news_post.ist_makro(self.D, {}))
        self.assertFalse(news_post.ist_makro(dict(self.D, rubrik="ETF", coins=["BTC"]), {"makro": True}))

    def test_texte_und_bild(self):
        d = dict(self.D, krypto=news_post.krypto_zeile(MARKT, "en"))
        t = news_post.texte(d, {}, CFG)
        self.assertIn("📊 <b>What it means for crypto:</b> In the small caps", t["telegram"])
        self.assertTrue(t["telegram"].rstrip().endswith("</i>"))
        self.assertLessEqual(len(t["x"]), 280)
        self.assertIn("Crypto now: 41% of small caps up in 24h.", t["x"])
        self.assertTrue(t["x"].endswith("Not financial advice."))
        with tempfile.TemporaryDirectory() as tmp:
            for layout in news_post.LAYOUTS:
                b = news_post.bild(d, {}, CFG, Path(tmp) / layout / "post.png", layout=layout,
                                   kurs=[(i, 100 + i) for i in range(20)])
                self.assertTrue(b.exists())

    def test_news_lauf_mit_krypto_zeile_besteht_pruefung(self):
        rss = """<rss><channel><item><title>Fed holds interest rates at 3.75% to 4.00%</title>
        <link>https://example.com/fed</link><description>Fed Chair Kevin Warsh speaks at 2:30 p.m. ET. Next meeting
        December 8 and 9. Decision on Wednesday, October 28.</description>
        <pubDate>Wed, 28 Oct 2026 18:05:00 GMT</pubDate></item></channel></rss>"""

        def laden(url):
            if "coindesk" in url:
                return rss
            raise OSError("offline")
        with tempfile.TemporaryDirectory() as d:
            orig = news.einsammeln
            news.einsammeln = lambda laden=None, **k: orig(jetzt=JETZT, laden=laden, **k)
            try:
                args = types.SimpleNamespace(out=d, eil=False, senden=False, daten=None)
                r = main.news_beitrag(args, CFG, {}, set(), laden=laden, schreiber=lambda g: dict(self.D),
                                      kurs_holen=None, markt=MARKT)
            finally:
                news.einsammeln = orig
            self.assertEqual(r, 0)   # Pruefung bestanden: Zahlen der Zeile kommen aus den Bot-Daten
            tg = next(Path(d).glob("*_news/post_telegram.txt")).read_text()
            self.assertIn("What it means for crypto", tg)

    def test_fremde_zahl_in_zeile_faellt_auf(self):
        f = pruefung.pruefen(["In the small caps we track, 77% are up."], {"fakten": "41 -0.8", "szenen": [0]},
                             CFG, set())
        self.assertTrue(any("77" in x for x in f))


if __name__ == "__main__":
    unittest.main()
