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

## Live-Eilmeldungen (seit 30.10.2026)
- `tools/live.sh` laeuft alle 10 Minuten rund um die Uhr (`deploy/plan.cron`, :05/:15/…), auch nachts.
- Eilmeldung = Eil-Thema (Hack, Exploit, Auszahlungsstopp, Depeg, ETF-Zulassung, Verbot …) mit mindestens
  2 Quellen; Radar-Konten (Watcher Guru, Wu Blockchain, Whale Alert) zaehlen mit. Hoechstens 5 am Tag (`eil.max_pro_tag`).
- Der Vorschlag kommt mit „🚨 EILMELDUNG – bitte schnell freigeben“. Gepostet wird erst nach Knopfdruck. `/pause` stoppt auch das.
- Anlass: Binance-Hack 29.10. um 21:05 deutscher Zeit; der alte Stunden-Check (7–21 Uhr, 3 Quellen) hat ihn verpasst.

## Folge-Liste (seit 31.10.2026)
- Taeglich 16:30 kommt im Redaktions-Bot die Folge-Liste (`tools/folgen.py`, Konten in `inhalte/folgen.yaml`).
- X: Knopf „✅ X: allen folgen“ -> der Bot folgt ueber die offizielle Schnittstelle (10 am Tag, `folgen.x_pro_tag`,
  ca. 0,025 $ je Konto). Ausgeloest immer von Tobias, nie automatisch (X verbietet massenhaftes Folgen).
- Instagram/TikTok/YouTube: keine Schnittstelle, Fernsteuerung verboten -> Links zum Selbst-Antippen, danach „☑️ Andere erledigt“.
- Neue Konten traegt der Redaktions-Chat in `inhalte/folgen.yaml` ein.

## Videos: Reels, TikTok, X, Telegram (seit 01.11.2026)
- Taeglich 14:30 kommt „Markt in 30 Sekunden“ zweimal: als Bild-Beitrag und als Video-Vorschlag (9:16, 30 s).
- Ohne Stimme (`stimme.aktiv: false`, keine ElevenLabs-Kosten): Untertitel erzaehlen, darunter eigene, lizenzfreie
  Musik (`social/musik.py`, mit ffmpeg erzeugt, `video.musik: generiert`).
- Knoepfe wie bei Bildern: Telegram (Video), X (Video-Upload in Teilen), Instagram (Reel), TikTok (Video-Entwurf
  in der App: dort Sound waehlen und den mitgeschickten Text einfuegen), Alle Kanaele.
- Instagram und TikTok holen das Video unter `https://whalesqueeze.com/medien/<zufall>.mp4` ab (nur Minuten oeffentlich).
- YouTube Shorts: Knopf ▶️ YouTube (nur Videos). Bis Google die App geprueft hat, laedt sie privat hoch
  (`youtube.sichtbarkeit: private`); Tobias stellt das Video in der YouTube-Studio-App auf „Oeffentlich“.
  Einmal verbinden: `schluessel.py` 12 + 13, dann `tools/youtube_verbinden.py`.

## Story, Wochenbericht, Kommentar-Assistent, Freigabe-Tor (seit 01.11.2026)
- **Instagram-Story:** jeder Instagram-Beitrag wird automatisch auch als Story geteilt (`instagram.story`).
- **Wochenbericht:** sonntags 18:30 an Tobias. Follower (Telegram, X, Instagram), Aufrufe je Format, Top-Beitraege,
  Empfehlung „ausbauen/pruefen“. Grundlage: `ausgabe/protokoll.jsonl` (jedes Posten/Verwerfen, dauerhaft).
- **Kommentar-Assistent:** 15:30 und 20:30 je 5 frische Posts grosser Konten (`kommentare.konten`) mit gepruefter
  Kommentar-Vorlage (antippen = kopiert). Tobias postet selbst.
- **Freigabe-Tor:** Routine-Formate (`autopost.formate`) posten automatisch, wenn sie 14 Tage lang mindestens 10-mal
  freigegeben und nie verworfen wurden und die Pruefung bestanden ist. News/Eilmeldungen nie. `/auto` zeigt den
  Stand, `/auto aus` stoppt, `/auto an` laesst wieder zu.

## Wal-Karussell (S11) und Termine der Woche (S13), seit 02.11.2026
- `main.py karussell` (sonntags 17:00): die 5 größten Wal-Bewegungen der Woche (7 Tage, Prozentpunkte, ab 20 Mio $ MCap)
  als Bilderserie: Deckblatt mit Balken, je Wal eine Folie, Abschluss „Follow“. Instagram-Karussell, TikTok-Fotoserie,
  X (erste 4 Folien), Telegram-Album (`social/karussell.py`, `social/karussell_posten.py`). YouTube: nicht möglich.
- `main.py termine` (sonntags 18:00): US-Termine der **kommenden** Woche (nie die vergangene) (CPI, Arbeitsmarkt, PCE, ISM, Fed, Fed-Protokoll, Wahlen) aus
  `inhalte/termine.yaml` plus Optionsverfall Deribit (letzter Freitag, 08:00 UTC, berechnet). Zeiten in ET und UTC.
  Die Liste muss die Redaktion pflegen; 4 Wochen bevor sie ausläuft, meldet der Redaktions-Bot das.
- Fußzeile in Bildern zeigt `@whalesqueeze`, solange `website.oeffentlich: false` (vorher `whalesqueeze.com` mit Passwort).

## Zeitversetzt posten (S31, seit 02.11.2026)
- „✅ Alle Kanäle“ postet Telegram und X sofort, Instagram ab 18:00, TikTok ab 19:00, YouTube ab 20:00 (deutsche Zeit,
  US-Hauptzeit). Liegt die Freigabe im Fenster, geht es sofort. `tools/geplant.py` (alle 10 Min.) holt Fälliges nach.
- News und Beiträge aus dem Redaktions-Chat: überall sofort. TikTok bei „Alle“ nur Videos/Bilderserien.
- Ein einzelner Kanal-Knopf postet immer sofort. 🗑 Verwerfen stoppt geplante Posts. Einstellungen: `config.yaml zeitplan`.

## Stimme (S17, seit 01.11.2026)
- Google Cloud Text-to-Speech, Stimme „Chirp 3 HD“ (`stimme.anbieter: google`, `stimme.google_stimme`).
  1 Mio Zeichen/Monat gratis, Bedarf ca. 50.000. Schlüssel `google_tts_key` über `tools/schluessel.py`.
- Hörproben: `tools/stimme_probe.py` schickt 4 Stimmen an Tobias. Ohne Schlüssel oder bei Fehler entstehen
  Videos ohne Stimme (Quelle steht im Freigabe-Hinweis), es bricht nichts ab.

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
