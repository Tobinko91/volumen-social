# WhaleSqueeze-Redaktion – Hinweise für Claude

Social Media zum Volumen-Bot (YouTube, TikTok, Instagram, X), gesichtslos und automatisiert.
Besitzer: Tobias (Deutsch, technischer Laie, Windows/PowerShell, iPhone). Antworten auf Deutsch,
einfache Schritte, ein Befehl pro Block, zu jeder Bitte kurz warum. Niemals Passwörter oder Schlüssel im Chat.

## Zuständigkeit
- Dieses Repository gehört dem Redaktions-Chat. `volumen-bot` und `volumen-web` nur lesen, keine PRs.
- Neue Daten vom Bot: als Wunsch ins Projekt-Dokument `website-briefing` („Wünsche der Redaktion“).
- Änderungen: Branch `vorschlag/<thema>` + Pull Request, Tobias merged. Nie direkt auf `main`.

## Technik
- Liest nur `/opt/volumen-bot/web/*.json` (Format wie `beispieldaten/`). Schreibt nie in den Bot.
- Python 3 + ffmpeg + Pillow + PyYAML + requests. Keine weiteren Pakete ohne Grund.
- Tests: `python3 -m unittest discover tests` – jede Änderung braucht grüne Tests.
- Schlüssel nur in `secrets.yaml` auf dem Server (gitignored). Sperrliste nur in `sperrliste.txt` (gitignored).
- Social-Media-Inhalte auf Deutsch (Start, entschieden 20.10.2026), Englisch später als eigene Kanäle.

## Design
- Corporate Design „Nachtleuchten“ (Design 06) aus `volumen-web`: Mitternacht #140F2E, Leuchtminze #3CF2C0,
  Flieder #B69CFF, Space Grotesk (`assets/schrift`, OFL), Logo `assets/logo-1080.png`. Alles in `social/design.py`.
- Hintergründe wechseln (Themen nacht, sonar, tiefsee, flieder, minze), Grafiken in `social/grafik.py`.
  Grafiken nur mit nachgerechneten Werten; Schemas sind als „Schema“ beschriftet.

## Schutzregeln (nie abschwächen)
- Jede Zahl im Sprechtext muss in den Bot-Daten stehen (`social/pruefung.py`).
- Keine Einstiegskurse, Stops, Kursziele, keine Kauf-/Verkaufsaufforderung, keine Gewinnversprechen.
- Überall (Texte, Bilder, Videos) nur „Keine Anlageberatung“ – kein KI-, Totalverlust- oder Betreiber-Hinweis
  (Wunsch Tobias 22.10.2026, nicht wieder verlängern).
  Keine Coins von der Sperrliste.
- Nur lizenzfreie Musik und eigene Grafiken. Öffentlich posten erst nach Freigabe durch Tobias.
