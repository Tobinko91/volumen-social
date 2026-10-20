#!/bin/bash
# EINMALIG auf dem Server: Redaktion WhaleSqueeze einrichten.
# Aufruf (als root):  bash einrichten.sh
# Darf mehrfach laufen. Bot und Website werden nicht angefasst, Bot-Daten nur gelesen.
set -e
REPO=git@github-social:Tobinko91/volumen-social.git
BASIS=/opt/volumen-social
SCHLUESSEL=/root/.ssh/volumen_social_ed25519

echo "== 1/6 Zugang zu GitHub (eigener Schluessel nur fuer die Redaktion)"
mkdir -p /root/.ssh
if [ ! -f "$SCHLUESSEL" ]; then
  ssh-keygen -q -t ed25519 -N "" -C "server-volumen-social" -f "$SCHLUESSEL"
fi
grep -q "Host github-social" /root/.ssh/config 2>/dev/null || cat >> /root/.ssh/config <<CFG

Host github-social
  HostName github.com
  User git
  IdentityFile $SCHLUESSEL
  IdentitiesOnly yes
CFG
if ! ssh -o StrictHostKeyChecking=accept-new -T github-social 2>&1 | grep -q "successfully authenticated"; then
  echo
  echo "!! GitHub kennt den Schluessel noch nicht. Bitte auf github.com eintragen:"
  echo "   Repository volumen-social -> Settings -> Deploy keys -> Add deploy key"
  echo "   Titel: Server, Haken bei 'Allow write access' NICHT setzen, diesen Text einfuegen:"
  echo
  cat "$SCHLUESSEL.pub"
  echo
  echo "   Danach dieses Skript noch einmal starten."
  exit 1
fi
echo "ok"

echo "== 2/6 Pakete (Video, Bilder, Schrift)"
apt-get update -qq
apt-get install -y -qq git ffmpeg python3-pil python3-yaml python3-requests fonts-inter fonts-dejavu-core >/dev/null
ffmpeg -version | head -1

echo "== 3/6 Eigener Benutzer 'redaktion' ohne Rechte am Bot"
id redaktion >/dev/null 2>&1 || useradd --system --home-dir "$BASIS" --shell /usr/sbin/nologin redaktion
mkdir -p "$BASIS/ausgabe"
[ -f "$BASIS/sperrliste.txt" ] || printf "# Coins, in denen du eine Position haeltst (ein Ticker pro Zeile)\n" > "$BASIS/sperrliste.txt"
[ -f "$BASIS/secrets.yaml" ] || : > "$BASIS/secrets.yaml"
chmod 600 "$BASIS/secrets.yaml"
[ -f /opt/volumen-bot/secrets.yaml ] && chmod 600 /opt/volumen-bot/secrets.yaml
ls /opt/volumen-bot/web/stand.json >/dev/null 2>&1 && echo "Bot-Daten gefunden" || echo "!! /opt/volumen-bot/web fehlt noch (Bot ab Version 9.7 noetig)"

echo "== 4/6 Code aus GitHub"
if [ -d "$BASIS/app/.git" ]; then
  git -C "$BASIS/app" fetch -q origin main && git -C "$BASIS/app" reset -q --hard origin/main
else
  rm -rf "$BASIS/app"; git clone -q "$REPO" "$BASIS/app"
fi
# Code gehoert root (sonst verweigert git die Updates), nur Ausgabe und Geheimnisse gehoeren "redaktion"
chown root:root "$BASIS"; chmod 755 "$BASIS"
chown -R redaktion:redaktion "$BASIS/ausgabe" "$BASIS/secrets.yaml" "$BASIS/sperrliste.txt"
echo "Version $(git -C "$BASIS/app" rev-parse --short HEAD)"
( cd "$BASIS/app" && python3 -m unittest discover -q tests )

echo "== 5/6 Automatische Updates (alle 15 Minuten, nur nach gruenen Tests)"
cat > /etc/cron.d/volumen-social <<'CRON'
*/15 * * * * root /bin/bash /opt/volumen-social/app/tools/auto_update.sh >> /var/log/volumen-social-update.log 2>&1
CRON

echo "== 6/6 Aufraeumen: fertige Videos nach 3 Tagen loeschen"
cat > /etc/cron.d/volumen-social-aufraeumen <<'CRON'
30 3 * * * root find /opt/volumen-social/ausgabe -mindepth 1 -maxdepth 1 -mtime +3 -exec rm -rf {} +
CRON

echo
echo "FERTIG. Naechster Schritt: Schluessel eintragen mit"
echo "   python3 $BASIS/app/tools/schluessel.py"
systemctl is-active volumen-bot >/dev/null 2>&1 && echo "Bot laeuft weiter: ok"
