#!/bin/bash
# Tagesplan der Redaktion (Probelauf: alles geht nur an Tobias per Telegram).
# Laeuft per cron um :00 und :30. Zeiten in deutscher Zeit, Ruhe von 22 bis 7 Uhr.
# Seit 27.10.2026 auf das englischsprachige Publikum (USA) ausgerichtet. Seit 1.11.2026 US-Winterzeit:
# Abstand zur US-Ostkueste 6 Std. (bis 8.3.2027; danach 5 Std., dann alles eine Stunde frueher). In Klammern ET:
#   14:30 Markt-Beitrag als Bild + Video „Why did it move?“ (8:30 ET, vor US-Boersenstart)
#   15:00 20:00 21:00 News (9:00 / 14:00 / 15:00 ET)
#   16:00 Coin-Check (10:00 ET)
#   18:30 „Why did it move?“ fuer den groessten Verlierer (12:30 ET)
#   15:30 20:30 Kommentar-Vorschlaege (9:30 / 14:30 ET, Tobias postet selbst)
#   17:30 Folge-Liste an Tobias (X per Knopf, Instagram/YouTube per Link; Wunsch 31.10.)
#   19:00 Wal des Tages (13:00 ET, US-Mittagspause)
#   21:30 Lern-Beitrag + Erinnerung an offene Vorschlaege (15:30 ET; spaeter waere fuer die USA besser, ab 22 Uhr ist aber Ruhezeit)
#   09:00 Gesundheits-Check an Tobias (gestern: Termine, Vorschlaege, Fehler, Update, Daten)
#   So 18:30 Wochenbericht an Tobias (Follower, Aufrufe je Format, Empfehlung)
#   Eilmeldungen: eigener Lauf tools/live.sh alle 10 Minuten rund um die Uhr (seit 30.10.2026)
export TZ=Europe/Berlin
H=$(date +%H); M=$(date +%M)
SLOT="$H:$([ "$M" -lt 30 ] && echo 00 || echo 30)"
cd /opt/volumen-social/app || exit 1
UMGEBUNG="TZ=Europe/Berlin SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe"
# Beitraege aus dem Redaktions-Chat (Branch warteschlange) holen und als Vorschlag schicken (auch alle 10 Min. aus live.sh)
bash tools/eingang.sh
# Musik-Ordner (Tobias schickt Stuecke an den Redaktions-Bot, der speichert sie hier)
mkdir -p /opt/volumen-social/musik && chown redaktion:redaktion /opt/volumen-social/musik
# Oeffentlicher Bild-Ordner fuer Instagram (Website liefert ihn unter /medien/ aus, nur fuer Minuten befuellt)
mkdir -p /opt/volumen-social/oeffentlich && chown redaktion:redaktion /opt/volumen-social/oeffentlich && \
  chmod 755 /opt/volumen-social/oeffentlich
# Instagram-Token taeglich verlaengern (gilt sonst nur 60 Tage)
[ "$SLOT" = "04:00" ] && sudo -u redaktion env $UMGEBUNG python3 tools/instagram_token.py
# TikTok-Zugang taeglich erneuern (Access-Token 24 Std., Refresh-Token laeuft sonst nach 365 Tagen ab)
[ "$SLOT" = "04:00" ] && sudo -u redaktion env $UMGEBUNG python3 tools/tiktok_verbinden.py --erneuern
# Gesundheits-Check taeglich 09:00 (auch waehrend Pause): lief gestern alles, welche Fehler? (Wunsch Tobias 02.11.)
[ "$SLOT" = "09:00" ] && sudo -u redaktion env $UMGEBUNG python3 tools/gesundheit.py --senden
# Funding/Open-Interest-Verlauf stuendlich mitschreiben (fuer „Why did it move?“, Wunsch 04.11.), auch in der Pause
[ "$(date +%M)" -lt 30 ] && sudo -u redaktion env $UMGEBUNG python3 tools/verlauf.py
# Pause: im Redaktions-Bot /pause schreiben (oder Datei anlegen), weiter mit /weiter
[ -f /opt/volumen-social/pause ] || [ -f /opt/volumen-social/ausgabe/.pause ] && exit 0
lauf() { sudo -u redaktion env $UMGEBUNG python3 main.py "$@" --senden; }
# Wochenbericht sonntags 18:30 (Punkt E): Follower, Aufrufe je Format, Empfehlung
[ "$SLOT" = "18:30" ] && [ "$(date +%u)" = "7" ] && sudo -u redaktion env $UMGEBUNG python3 tools/wochenbericht.py --senden
[ "$SLOT" = "18:30" ] && [ "$(date +%u)" = "7" ] && sudo -u redaktion env $UMGEBUNG python3 tools/kommentar_bilanz.py --senden
# S11 Wal-Karussell sonntags 17:00; S13 Termine der KOMMENDEN Woche sonntags 18:00 (vor Wochenbeginn)
[ "$SLOT" = "17:00" ] && [ "$(date +%u)" = "7" ] && lauf karussell
[ "$SLOT" = "18:00" ] && [ "$(date +%u)" = "7" ] && lauf termine
# S30 Willkommensvideo EINMAL (sobald die Stimme laeuft), danach Merkdatei; neu: Datei loeschen
W=/opt/volumen-social/ausgabe/.willkommen_gesendet
[ ! -f "$W" ] && [ "$SLOT" = "14:00" -o "$SLOT" = "16:30" -o "$SLOT" = "18:30" ] && lauf willkommen --nur-mit-stimme && sudo -u redaktion touch "$W"
# „Why did it move?“ EINMAL sofort als Probe (Wunsch Tobias 04.11.), danach Merkdatei; tagsueber 07-22 Uhr
T=/opt/volumen-social/ausgabe/.warum_probe_gesendet
[ ! -f "$T" ] && [ "$H" -ge 7 ] && [ "$H" -lt 22 ] && [ "$SLOT" != "14:30" ] && { lauf warum; sudo -u redaktion touch "$T"; }
case "$SLOT" in
  14:30) lauf markt --art post; lauf warum ;;   # 04.11.2026: Markt nur noch als Bild, Video = „Why did it move?“
  15:00|20:00|21:00) lauf news ;;
  18:30) lauf warum --richtung runter ;;   # größter Verlierer: „Why did X drop?“ (Wunsch Tobias 04.11.2026)
  16:00) lauf coincheck ;;
  19:00) lauf wal ;;
  21:30) lauf wissen; sudo -u redaktion env $UMGEBUNG python3 tools/offen.py --senden ;;   # Abend-Erinnerung offene Vorschlaege
  17:30) sudo -u redaktion env $UMGEBUNG python3 tools/folgen.py --senden ;;
  15:30|20:30) sudo -u redaktion env $UMGEBUNG python3 tools/kommentare.py --senden ;;
esac
echo "$(date '+%F %T') Plan $SLOT erledigt"
