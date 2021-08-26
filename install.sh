#!/bin/bash

# Error out if anything fails.
set -e

CUR_DIR=$(dirname "$0")
pushd $CUR_DIR

echo "Installing dependencies..."
echo "=========================="
sudo apt update && sudo apt -y install python3 python3-pip python3-pygame supervisor vlc ntfs-3g exfat-fuse

sudo apt -y install git build-essential python3-dev autoconf automake libtool

echo "Installing libde265..."
echo "========================="
cd ..
git clone https://github.com/lomorage/libde265.git
cd libde265
./autogen.sh
./configure --prefix=/opt/lomorage/lib
make -j2
make install

echo "Installing libheif..."
echo "========================="
cd ..
git clone https://github.com/lomorage/libheif.git
cd libheif
./autogen.sh
./configure --prefix=/opt/lomorage/lib
make -j2
make install

echo "Installing SDL_image..."
echo "========================="
cd ..
sudo apt -y install libsdl1.2-dev
git clone https://github.com/lomorage/SDL_image.git
cd SDL_image
./autogen.sh
./configure CFLAGS=-I/opt/lomorage/lib/include LDFLAGS=-L/opt/lomorage/lib/lib  --prefix=/opt/lomorage/lib
make -j2
make install
echo "Installing video_looper program..."
echo "=================================="

# change the directoy to the script location
popd
sudo mkdir -p /mnt/usbdrive0 # This is very important if you put your system in readonly after
sudo mkdir -p /home/pi/video # create default video directory

sudo pip3 install setuptools
sudo python3 setup.py install --force

mkdir -p /opt/lomorage/var
sudo cp ./assets/video_looper.ini /opt/lomorage/var/video_looper.ini

echo "Configuring video_looper to run on start..."
echo "==========================================="

sudo cp ./assets/video_looper.conf /etc/supervisor/conf.d/

sudo service supervisor restart

# to test run `LD_LIBRARY_PATH=/opt/lomorage/lib/lomoframe/ python3 -u -m Adafruit_Video_^Coper.video_looper`
echo "Finished!"
