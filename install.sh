#!/bin/sh

# Error out if anything fails.
set -e

# Make sure script is run as root.
if [ "$(id -u)" != "0" ]; then
  echo "Must be run as root with sudo! Try: sudo ./install.sh"
  exit 1
fi


echo "Installing dependencies..."
echo "=========================="
apt update && apt -y install python3 python3-pip python3-pygame supervisor omxplayer ntfs-3g exfat-fuse

apt -y install git build-essential python3-dev autoconf automake libtool

echo "Installing libde265..."
echo "========================="
git clone https://github.com/lomorage/libde265.git
cd libde265
./autogen.sh
./configure --prefix=/opt/lomorage/lib
make -j2
make install
cd ..

echo "Installing libheif..."
echo "========================="
git clone https://github.com/lomorage/libheif.git
cd libheif
./autogen.sh
./configure --prefix=/opt/lomorage/lib
make -j2
make install
cd ..

echo "Installing SDL_image..."
echo "========================="
apt -y install libsdl1.2-dev
git clone https://github.com/lomorage/SDL_image.git
cd SDL_image
./autogen.sh
./configure CFLAGS=-I/opt/lomorage/lib/include LDFLAGS=-L/opt/lomorage/lib/lib  --prefix=/opt/lomorage/lib
make -j2
make install
cd ..

echo "Installing video_looper program..."
echo "=================================="

# change the directoy to the script location
cd "$(dirname "$0")"

mkdir -p /mnt/usbdrive0 # This is very important if you put your system in readonly after
mkdir -p /home/pi/video # create default video directory

pip3 install setuptools
python3 setup.py install --force

cp ./assets/video_looper.ini /boot/video_looper.ini

echo "Configuring video_looper to run on start..."
echo "==========================================="

cp ./assets/video_looper.conf /etc/supervisor/conf.d/

service supervisor restart

echo "Finished!"
