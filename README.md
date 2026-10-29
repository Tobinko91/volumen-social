# volumen-social – WhaleSqueeze Redaktion

Baut gesichtslose Kurzvideos (9:16, TikTok/Reels/Shorts) automatisch aus den Daten des Volumen-Bots.
Liest nur `/opt/volumen-bot/web/*.json`, schreibt nie in den Bot.

## Ablauf
Bot-Daten → Format waehlt Fakten und Szenen → Sprechtext (Claude-API, sonst feste Vorlage) →
automatische Pruefung (jede Zahl muss in den Daten stehen, verbotene Wendungen, Sperrliste, Laenge) →
Bilder je Szene → KI-Stimme (ElevenLabs, sonst Stille fuer Proben) → Video mit ffmpeg → `meta.json`
mit Titel, Beschreibung, Pruefergebnis. Freigabe per Telegram und Posten folgen in Phase 2.

## Probe
```bash
python main.py markt --daten beispieldaten
```

## Dateien
| Datei | Zweck |
|---|---|
| `config.yaml` | Farben, Laenge, Hinweise, verbotene Woerter |
| `social/daten.py` | liest die Bot-Dateien; Marktlage aus `markt.json` (sonst Ersatzrechnung aus `coins/`), Auswahl „Wal des Tages“ |
| `social/wal.py` | Wal des Tages: groesste Wal-Veraenderung 7 Tage (`wale_7d`, `holder`, `wale_verlauf`), Bild + Text; `python main.py wal` |
| `social/formate.py` | Formate (bisher: Krypto-Markt in 30 Sekunden) |
| `social/sprache.py` | alle Texte je Sprache (Start: Deutsch, Englisch vorbereitet) |
| `social/texte.py` | Sprechtext ueber Claude-API, nur aus Fakten |
| `social/pruefung.py` | automatische Pruefung |
| `social/design.py`, `social/grafik.py` | Corporate Design Nachtleuchten: Farben, Schrift, Logo, 5 Hintergruende, Grafiken |
| `social/bilder.py` | Videobilder 1080x1920 |
| `social/stimme.py` | ElevenLabs oder Stille |
| `social/video.py` | ffmpeg-Zusammenbau |
| `social/post.py` | Bild (4:5) + Text fuer Telegram und X (dort Hauptformat) |
| `social/wissen.py`, `inhalte/wissen.yaml` | Lern-Beitraege: 10 Themen, jede Zahl nachgerechnet |
| `social/coincheck.py` | Coin-Check: Kurs 7 Tage + Volumenprofil, OI, Funding, Wale (taeglich 11 Uhr, im Bot: /check AKE) |
| `secrets.example.yaml` | Vorlage fuer Schluessel (echte Datei nur auf dem Server) |
| `sperrliste.example.txt` | Vorlage: Coins mit eigener Position |

## Sprache (S1, vorbereitet)
`python main.py markt --sprache en --daten beispieldaten` erzeugt den Markt-Beitrag auf Englisch (Text, Post, Video-Sprechtext),
`python main.py wal --sprache en` den Wal des Tages. Englisch wird **nie gesendet** (`--senden` wird bei `--sprache en`
abgeschaltet), bis Tobias den Start freigibt. Noch Deutsch: Bild-Beschriftungen in `post.markt_bild`, Fusszeile im Video,
Lern-/News-/Coin-Check-Texte, Stimme (englische ElevenLabs-Stimme fehlt). Startkriterium: `plan-englisch` (Projekt-Dokument).

## News-Radar (S18) und Krypto-Zeile (S19), seit 29.10.2026
- Neben den News-Seiten (CoinDesk, The Block …) liest der News-Lauf grosse News-Konten mit (`inhalte/quellen.yaml`,
  `radar: true`): Watcher Guru, Wu Blockchain und Whale Alert ueber ihre oeffentliche Telegram-Vorschau (kostenlos).
- X-Konten (The Kobeissi Letter, Walter Bloomberg, Lookonchain, Santiment) nur mit `radar.x_lesen: true` in
  `config.yaml`: eine Suchanfrage je News-Slot (14/19/21 Uhr), nie im stuendlichen Eil-Lauf. X berechnet jeden Abruf.
- Radar-Konten sind nur Hinweisgeber: gepostet wird erst mit zweiter Quelle (oder ein Whale-Alert-Transfer ab 100 Mio. $).
  Nur Krypto- und Makro-Themen, kein Klatsch. Claude schreibt immer eigene Worte, Quellen nur im Freigabe-Hinweis.
- Makro-News (Fed, Inflation, Zinsen …) bekommen unten die Karte „What it means for crypto“ mit unseren Bot-Daten
  (Anteil der Small Caps im Plus, Median 24 h, Bitcoin 24 h). Fehlen frische Daten, entfaellt die Karte.
- Pruefen auf dem Server: `python3 tools/quellen_test.py`

## Schutzregeln (fest eingebaut)
Ueberall nur „Keine Anlageberatung“ (kein KI-, Totalverlust- oder Betreiber-Hinweis), keine Einstiegskurse,
keine Kauf-/Verkaufsaufforderung, keine Zahl ohne Datenquelle, keine Coins von der Sperrliste.

## Server
Einmalig als root: `bash einrichten.sh` (aus `tools/`). Legt `/opt/volumen-social` an:
`app/` (Code, root), `secrets.yaml` und `sperrliste.txt` (nur Benutzer `redaktion`), `ausgabe/` (Videos, nach 3 Tagen geloescht).
Schluessel eintragen: `python3 /opt/volumen-social/app/tools/schluessel.py` (Eingabe unsichtbar).
Probevideo an Telegram: `bash /opt/volumen-social/app/tools/probe.sh`.
Updates: cron alle 15 Minuten, nur nach gruenen Tests.
News: `python3 main.py news` (Quellen in `inhalte/quellen.yaml`, Test: `python3 tools/quellen_test.py`).
Tagesplan: `tools/plan.sh` per cron (`deploy/plan.cron`), deutsche Zeit fuer US-Publikum: 13:30 Markt, 14/19/21 Uhr News,
15 Uhr Coin-Check, 18 Uhr Wal des Tages, 21:30 Lernen,
stuendlich Eilmeldungen, Ruhe 22–7 Uhr. Pause: `touch /opt/volumen-social/pause` (weiter: Datei loeschen).

## Kanaele und Freigabe
- `tools/freigabe.py` laeuft dauerhaft (`deploy/volumen-social-freigabe.service`, wird per Update eingespielt).
  Jeder Vorschlag kommt im Redaktions-Bot mit Knoepfen: Telegram-Kanal, X, beide, verwerfen.
  Befehle im Bot: /status, /sperre BTC, /entsperre BTC, /pause, /weiter.
- `social/kanaele.py`: Telegram-Kanal (Bot ist Admin), X (API v2, OAuth 1.0a) und Instagram (Instagram-Login-API).
  Instagram holt das Bild als JPEG aus `/opt/volumen-social/oeffentlich` = `https://whalesqueeze.com/medien/` (Caddy der Website),
  danach wird es sofort geloescht. Token: `schluessel.py` Punkt 9, Verlaengerung taeglich 04:00 (`tools/instagram_token.py`). TikTok folgt.
- Beitraege aus dem Redaktions-Chat: Ordner `warteschlange/<name>/` mit `post.png`, `post_x.txt`,
  `post_telegram.txt` auf den Branch `warteschlange`. `plan.sh` holt ihn alle 30 Minuten, `tools/eingang.py`
  prueft und schickt den Vorschlag. Gepostet wird nur per Knopf.
- `social/kurse.py`: Kursverlaeufe direkt von Bitunix (sonst Binance), ohne den Bot anzufassen.
