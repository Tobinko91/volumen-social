#!/bin/bash
# Live-Eilmeldungen (Wunsch Tobias 30.10.2026): alle 10 Minuten, rund um die Uhr.
# Prueft alle Quellen inkl. News-Radar (Telegram-Vorschau, kostenlos; X nie, das kostet je Abruf).
# Nur echte Eilmeldungen (Hack, Auszahlungsstopp, Depeg, ETF-Zulassung, Verbot ...) mit mindestens 2 Quellen
# gehen als Vorschlag an Tobias. Gepostet wird erst nach seinem Knopfdruck.
export TZ=Europe/Berlin
cd /opt/volumen-social/app || exit 1
[ -f /opt/volumen-social/pause ] || [ -f /opt/volumen-social/ausgabe/.pause ] && exit 0
# nie zwei Laeufe gleichzeitig (ein langsamer Feed darf sich nicht stapeln)
exec 9>/tmp/volumen-social-live.lock
flock -n 9 || exit 0
sudo -u redaktion env TZ=Europe/Berlin SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe \
  timeout 300 python3 main.py news --eil --senden
