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
| `social/formate.py` | Formate (bisher: Market in 30 seconds) |
| `social/texte.py` | Sprechtext ueber Claude-API, nur aus Fakten |
| `social/pruefung.py` | automatische Pruefung |
| `social/bilder.py` | Bilder 1080x1920 in den Website-Farben |
| `social/stimme.py` | ElevenLabs oder Stille |
| `social/video.py` | ffmpeg-Zusammenbau |
| `secrets.example.yaml` | Vorlage fuer Schluessel (echte Datei nur auf dem Server) |
| `sperrliste.example.txt` | Vorlage: Coins mit eigener Position |

## Schutzregeln (fest eingebaut)
Risiko- und KI-Hinweis in jedem Bild, Interessenkonflikt-Hinweis im Abspann, keine Einstiegskurse,
keine Kauf-/Verkaufsaufforderung, keine Zahl ohne Datenquelle, keine Coins von der Sperrliste.
