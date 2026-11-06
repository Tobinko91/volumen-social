#!/bin/bash
# Beitraege aus dem Redaktions-Chat (Branch warteschlange) holen und als Vorschlag schicken.
# Laeuft aus tools/plan.sh (:00/:30) UND seit 06.11.2026 aus tools/live.sh (alle 10 Minuten, Wunsch Tobias:
# Eilmeldungen wie die Arbeitsmarktdaten muessen schnell im Bot sein). flock: nie zwei Laeufe gleichzeitig.
export TZ=Europe/Berlin
cd /opt/volumen-social/app || exit 1
exec 8>/tmp/volumen-social-eingang.lock
flock -w 120 8 || exit 0
UMGEBUNG="TZ=Europe/Berlin SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe"
if git fetch -q origin warteschlange 2>/dev/null; then
  rm -rf /opt/volumen-social/eingang && mkdir -p /opt/volumen-social/eingang
  git archive origin/warteschlange warteschlange 2>/dev/null | tar -x -C /opt/volumen-social/eingang --strip-components=1
  chmod -R a+rX /opt/volumen-social/eingang
  sudo -u redaktion env $UMGEBUNG python3 tools/eingang.py
fi
