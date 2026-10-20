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
- Social-Media-Inhalte auf Englisch; Code-Kommentare, Chats und Planung auf Deutsch.

## Schutzregeln (nie abschwächen)
- Jede Zahl im Sprechtext muss in den Bot-Daten stehen (`social/pruefung.py`).
- Keine Einstiegskurse, Stops, Kursziele, keine Kauf-/Verkaufsaufforderung, keine Gewinnversprechen.
- Risiko-, KI- und Interessenkonflikt-Hinweis in jedem Video. Keine Coins von der Sperrliste.
- Nur lizenzfreie Musik und eigene Grafiken. Öffentlich posten erst nach Freigabe durch Tobias.
