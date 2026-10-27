#!/bin/bash
# Tagesplan der Redaktion (Probelauf: alles geht nur an Tobias per Telegram).
# Laeuft per cron um :00 und :30. Zeiten in deutscher Zeit, Ruhe von 22 bis 7 Uhr.
#   07:30 Markt-Beitrag (Bild + Text)
#   08:00 13:00 19:00 News (wichtigste neue Nachricht)
#   11:00 Coin-Check (auffaelligster Coin)
#   11:30 Wal des Tages (groesste Wal-Veraenderung in 7 Tagen)
#   17:00 Lern-Beitrag
#   sonst jede volle Stunde 7-21 Uhr: Eilmeldung, falls es eine gibt (hoechstens 2 am Tag)
export TZ=Europe/Berlin
H=$(date +%H); M=$(date +%M)
SLOT="$H:$([ "$M" -lt 30 ] && echo 00 || echo 30)"
cd /opt/volumen-social/app || exit 1
UMGEBUNG="TZ=Europe/Berlin SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe"
# Beitraege aus dem Redaktions-Chat (Branch warteschlange) holen und als Vorschlag schicken
if git fetch -q origin warteschlange 2>/dev/null; then
  rm -rf /opt/volumen-social/eingang && mkdir -p /opt/volumen-social/eingang
  git archive origin/warteschlange warteschlange 2>/dev/null | tar -x -C /opt/volumen-social/eingang --strip-components=1
  chmod -R a+rX /opt/volumen-social/eingang
  sudo -u redaktion env $UMGEBUNG python3 tools/eingang.py
fi
# Oeffentlicher Bild-Ordner fuer Instagram (Website liefert ihn unter /medien/ aus, nur fuer Minuten befuellt)
mkdir -p /opt/volumen-social/oeffentlich && chown redaktion:redaktion /opt/volumen-social/oeffentlich && \
  chmod 755 /opt/volumen-social/oeffentlich
# Instagram-Token taeglich verlaengern (gilt sonst nur 60 Tage)
[ "$SLOT" = "04:00" ] && sudo -u redaktion env $UMGEBUNG python3 tools/instagram_token.py
# TikTok-Zugang taeglich erneuern (Access-Token 24 Std., Refresh-Token laeuft sonst nach 365 Tagen ab)
[ "$SLOT" = "04:00" ] && sudo -u redaktion env $UMGEBUNG python3 tools/tiktok_verbinden.py --erneuern
# Pause: im Redaktions-Bot /pause schreiben (oder Datei anlegen), weiter mit /weiter
[ -f /opt/volumen-social/pause ] || [ -f /opt/volumen-social/ausgabe/.pause ] && exit 0
lauf() { sudo -u redaktion env $UMGEBUNG python3 main.py "$@" --senden; }
case "$SLOT" in
  07:30) lauf markt --art post ;;
  08:00|13:00|19:00) lauf news ;;
  11:00) lauf coincheck ;;
  11:30) lauf wal ;;
  17:00) lauf wissen ;;
  0[7-9]:00|1[0-9]:00|2[01]:00) lauf news --eil ;;
esac
echo "$(date '+%F %T') Plan $SLOT erledigt"
