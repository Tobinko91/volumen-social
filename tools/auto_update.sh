#!/bin/bash
# Holt freigegebene Aenderungen (main). Laeuft per cron alle 15 Minuten.
# Schlagen die Tests fehl, bleibt die alte Version.
APP=/opt/volumen-social/app
cd "$APP" || exit 1
# Tagesplan aus dem Repository einspielen (aendert sich nur per freigegebenem Pull Request)
[ -f deploy/plan.cron ] && ! cmp -s deploy/plan.cron /etc/cron.d/volumen-social-plan && \
  cp deploy/plan.cron /etc/cron.d/volumen-social-plan && echo "$(date '+%F %T') Tagesplan eingespielt"
[ -f deploy/aufraeumen.cron ] && ! cmp -s deploy/aufraeumen.cron /etc/cron.d/volumen-social-aufraeumen && \
  cp deploy/aufraeumen.cron /etc/cron.d/volumen-social-aufraeumen
# Freigabe-Dienst (Knoepfe im Redaktions-Bot) einspielen und laufen lassen
D=volumen-social-freigabe.service
if [ -f deploy/$D ] && ! cmp -s deploy/$D /etc/systemd/system/$D; then
  cp deploy/$D /etc/systemd/system/$D && systemctl daemon-reload && systemctl enable -q $D
  systemctl restart $D && echo "$(date '+%F %T') Freigabe-Dienst eingespielt"
fi
systemctl is-active -q $D 2>/dev/null || systemctl start $D 2>/dev/null
git fetch -q origin main || exit 1
ALT=$(git rev-parse HEAD)
NEU=$(git rev-parse origin/main)
[ "$ALT" = "$NEU" ] && exit 0
TMP=$(mktemp -d)
git worktree add -q --detach "$TMP" "$NEU"
if ( cd "$TMP" && python3 -m unittest discover -q tests ); then
  git reset -q --hard "$NEU"
  systemctl restart volumen-social-freigabe.service 2>/dev/null
  echo "$(date '+%F %T') Update auf $(git rev-parse --short HEAD)"
  MELDUNG="Redaktion aktualisiert auf $(git log -1 --format='%h %s')"
else
  echo "$(date '+%F %T') Tests fehlgeschlagen, bleibe auf $(git rev-parse --short "$ALT")"
  MELDUNG="Redaktions-Update $(git rev-parse --short "$NEU") NICHT eingespielt: Tests fehlgeschlagen"
fi
git worktree remove --force "$TMP"
[ -x /opt/volumen-bot/venv/bin/python ] && [ -f /opt/volumen-bot/tools/notify_cli.py ] && \
  ( cd /opt/volumen-bot && venv/bin/python tools/notify_cli.py "$MELDUNG" ) >/dev/null 2>&1 || true
