#!/bin/bash
# Wichtigste neue Krypto-Nachricht als Beitrag bauen und an Tobias schicken. Aufruf als root:
#   bash /opt/volumen-social/app/tools/probe_news.sh
cd /opt/volumen-social/app || exit 1
sudo -u redaktion env TZ=Europe/Berlin SOCIAL_GEHEIM=/opt/volumen-social SOCIAL_AUSGABE=/opt/volumen-social/ausgabe \
  python3 main.py news --senden
