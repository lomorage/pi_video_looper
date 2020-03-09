#! /bin/bash
set -e

sudo mv /opt/lomorage/var/lomo-playlist.txt /opt/lomorage/var/lomo-playlist.txt.bak
sudo service supervisor restart
sleep 1800
sudo service supervisor stop
