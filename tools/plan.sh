#!/bin/bash
# Tagesplan der Redaktion (Probelauf: alles geht nur an Tobias per Telegram).
# Laeuft per cron um :00 und :30. Zeiten in deutscher Zeit, Ruhe von 22 bis 7 Uhr.
# Seit 27.10.2026 auf das englischsprachige Publikum (USA) ausgerichtet; in Klammern US-Ostkueste (ab 1.11. Winterzeit):
#   13:30 Markt-Beitrag (7:30 ET, vor US-Boersenstart)
#   14:00 19:00 21:00 News (9:00 / 14:00 / 16:00 ET)
#   15:00 Coin-Check (10:00 ET)
#   18:00 Wal des Tages (12:00 ET)
#   21:30 Lern-Beitrag (16:30 ET; 0:00 deutscher Zeit waere besser, liegt aber in der Ruhezeit fuer die Freigabe)
#   Eilmeldungen: eigener Lauf tools/live.sh alle 10 Minuten rund um die Uhr (seit 30.10.2026)
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
  13:30) lauf markt --art post ;;
  14:00|19:00|21:00) lauf news ;;
  15:00) lauf coincheck ;;
  18:00) lauf wal ;;
  21:30) lauf wissen ;;
esac
echo "$(date '+%F %T') Plan $SLOT erledigt"
