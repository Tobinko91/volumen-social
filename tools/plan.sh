#!/bin/bash
# Tagesplan der Redaktion (Probelauf: alles geht nur an Tobias per Telegram).
# Laeuft per cron um :00 und :30. Zeiten in deutscher Zeit, Ruhe von 22 bis 7 Uhr.
#   07:30 Markt-Beitrag (Bild + Text)
#   08:00 13:00 19:00 News (wichtigste neue Nachricht)
#   17:00 Lern-Beitrag
#   sonst jede volle Stunde 7-21 Uhr: Eilmeldung, falls es eine gibt (hoechstens 2 am Tag)
export TZ=Europe/Berlin
H=$(date +%H); M=$(date +%M)
SLOT="$H:$([ "$M" -lt 30 ] && echo 00 || echo 30)"
[ -f /opt/volumen-social/pause ] && exit 0      # Pause: Datei anlegen mit  touch /opt/volumen-social/pause
cd /opt/volumen-social/app || exit 1
lauf() { sudo -u redaktion env TZ=Europe/Berlin SOCIAL_GEHEIM=/opt/volumen-social \
         SOCIAL_AUSGABE=/opt/volumen-social/ausgabe python3 main.py "$@" --senden; }
case "$SLOT" in
  07:30) lauf markt --art post ;;
  08:00|13:00|19:00) lauf news ;;
  17:00) lauf wissen ;;
  0[7-9]:00|1[0-9]:00|2[01]:00) lauf news --eil ;;
esac
echo "$(date '+%F %T') Plan $SLOT erledigt"
