#!/bin/bash
# Beitraege aus dem Redaktions-Chat (Branch warteschlange) holen und als Vorschlag schicken.
# Laeuft aus tools/plan.sh (:00/:30) UND seit 06.11.2026 aus tools/live.sh (alle 10 Minuten, Wunsch Tobias:
# Eilmeldungen wie die Arbeitsmarktdaten muessen schnell im Bot sein). flock: nie zwei Laeufe gleichzeitig.
export TZ=Europe/Berlin
cd /opt/volumen-social/app || exit 1
exec 8>/tmp/volumen-social-eingang.lock
flock -w 120 8 || exit 0
UMGEBUNG="TZ=Europe/Berlin SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe"
# 10.11.2026 GitHub schonend (nach der Sperre 06.-09.11.): EINE Sammelabfrage holt main UND warteschlange,
# hoechstens alle 9 Minuten. auto_update.sh nutzt dieses Ergebnis und fragt selbst nicht mehr nach.
STEMPEL=/tmp/volumen-social-fetch.stamp
if [ -f "$STEMPEL" ] && [ $(( $(date +%s) - $(stat -c %Y "$STEMPEL") )) -lt 540 ]; then
  exit 0
fi
if git fetch -q origin main warteschlange 2>/dev/null && touch "$STEMPEL"; then
  rm -rf /opt/volumen-social/eingang && mkdir -p /opt/volumen-social/eingang
  git archive origin/warteschlange warteschlange 2>/dev/null | tar -x -C /opt/volumen-social/eingang --strip-components=1
  chmod -R a+rX /opt/volumen-social/eingang
  sudo -u redaktion env $UMGEBUNG python3 tools/eingang.py
fi
