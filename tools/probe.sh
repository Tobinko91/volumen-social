#!/bin/bash
# Probevideo aus den echten Bot-Daten bauen und per Telegram an Tobias schicken. Aufruf als root:
#   bash /opt/volumen-social/app/tools/probe.sh
cd /opt/volumen-social/app || exit 1
sudo -u redaktion env SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe \
  python3 main.py markt --senden
