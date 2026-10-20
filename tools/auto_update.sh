#!/bin/bash
# Holt freigegebene Aenderungen (main). Laeuft per cron alle 15 Minuten.
# Schlagen die Tests fehl, bleibt die alte Version.
APP=/opt/volumen-social/app
cd "$APP" || exit 1
git fetch -q origin main || exit 1
ALT=$(git rev-parse HEAD)
NEU=$(git rev-parse origin/main)
[ "$ALT" = "$NEU" ] && exit 0
TMP=$(mktemp -d)
git worktree add -q --detach "$TMP" "$NEU"
if ( cd "$TMP" && python3 -m unittest discover -q tests ); then
  git reset -q --hard "$NEU"
  echo "$(date '+%F %T') Update auf $(git rev-parse --short HEAD)"
  MELDUNG="Redaktion aktualisiert auf $(git log -1 --format='%h %s')"
else
  echo "$(date '+%F %T') Tests fehlgeschlagen, bleibe auf $(git rev-parse --short "$ALT")"
  MELDUNG="Redaktions-Update $(git rev-parse --short "$NEU") NICHT eingespielt: Tests fehlgeschlagen"
fi
git worktree remove --force "$TMP"
[ -x /opt/volumen-bot/venv/bin/python ] && [ -f /opt/volumen-bot/tools/notify_cli.py ] && \
  ( cd /opt/volumen-bot && venv/bin/python tools/notify_cli.py "$MELDUNG" ) >/dev/null 2>&1 || true
