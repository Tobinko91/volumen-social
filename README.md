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
| `social/daten.py` | liest die Bot-Dateien, Altcoin-Breite |
| `social/formate.py` | Formate (bisher: Krypto-Markt in 30 Sekunden) |
| `social/sprache.py` | alle Texte je Sprache (Start: Deutsch, Englisch vorbereitet) |
| `social/texte.py` | Sprechtext ueber Claude-API, nur aus Fakten |
| `social/pruefung.py` | automatische Pruefung |
| `social/bilder.py` | Bilder 1080x1920 in den Website-Farben |
| `social/stimme.py` | ElevenLabs oder Stille |
| `social/video.py` | ffmpeg-Zusammenbau |
| `social/post.py` | Bild (4:5) + Text fuer Telegram und X (dort Hauptformat) |
| `social/wissen.py`, `inhalte/wissen.yaml` | Lern-Beitraege: 10 Themen, jede Zahl nachgerechnet |
| `secrets.example.yaml` | Vorlage fuer Schluessel (echte Datei nur auf dem Server) |
| `sperrliste.example.txt` | Vorlage: Coins mit eigener Position |

## Schutzregeln (fest eingebaut)
Risiko- und KI-Hinweis in jedem Bild, Interessenkonflikt-Hinweis im Abspann, keine Einstiegskurse,
keine Kauf-/Verkaufsaufforderung, keine Zahl ohne Datenquelle, keine Coins von der Sperrliste.

## Server
Einmalig als root: `bash einrichten.sh` (aus `tools/`). Legt `/opt/volumen-social` an:
`app/` (Code, root), `secrets.yaml` und `sperrliste.txt` (nur Benutzer `redaktion`), `ausgabe/` (Videos, nach 3 Tagen geloescht).
Schluessel eintragen: `python3 /opt/volumen-social/app/tools/schluessel.py` (Eingabe unsichtbar).
Probevideo an Telegram: `bash /opt/volumen-social/app/tools/probe.sh`.
Updates: cron alle 15 Minuten, nur nach gruenen Tests.
News: `python3 main.py news` (Quellen in `inhalte/quellen.yaml`, Test: `python3 tools/quellen_test.py`).
Tagesplan: `tools/plan.sh` per cron (`deploy/plan.cron`), 07:30 Markt, 08/13/19 Uhr News, 17 Uhr Lernen,
stuendlich Eilmeldungen, Ruhe 22–7 Uhr. Pause: `touch /opt/volumen-social/pause` (weiter: Datei loeschen).
