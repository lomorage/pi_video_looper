#!/bin/bash
set -e

nowDate=$(date +"%Y%m%d")
commitHash=$(git rev-parse --short HEAD)
VERSION="$nowDate+$commitHash"
PACKAGE_NAME="lomo-frame"
BUILD_NAME=$PACKAGE_NAME"_"$VERSION

if [ -d $BUILD_NAME ]; then
    rm -rf $BUILD_NAME
fi

mkdir $BUILD_NAME
mkdir $BUILD_NAME/DEBIAN

cat << EOF > $BUILD_NAME/DEBIAN/control
Package: $PACKAGE_NAME
Version: $VERSION
Section: python
Priority: optional
Architecture: all
Depends: python3, python3-pyudev, python3-pygame, supervisor, omxplayer, ntfs-3g, exfat-fuse
Maintainer: Jeromy Fu<fuji246@gmail.com>
Description: Lomorage Digital Frame
EOF

cat << EOF > $BUILD_NAME/DEBIAN/preinst
#!/bin/bash
service supervisor stop
EOF
chmod +x $BUILD_NAME/DEBIAN/preinst

cat << EOF > $BUILD_NAME/DEBIAN/postinst
#!/bin/bash
ln -s /opt/lomorage/lib/lib/libde265.so.0.0.12 /opt/lomorage/lib/lib/libde265.so
ln -s /opt/lomorage/lib/lib/libde265.so.0.0.12 /opt/lomorage/lib/lib/libde265.so.0
ln -s /opt/lomorage/lib/lib/libheif.so.1.6.2 /opt/lomorage/lib/lib/libheif.so
ln -s /opt/lomorage/lib/lib/libheif.so.1.6.2 /opt/lomorage/lib/lib/libheif.so.1
ln -s /opt/lomorage/lib/lib/libSDL_image-1.2.so.0.8.4 /opt/lomorage/lib/lib/libSDL_image.so
ln -s /opt/lomorage/lib/lib/libSDL_image-1.2.so.0.8.4 /opt/lomorage/lib/lib/libSDL_image-1.2.so.0
service supervisor start
EOF
chmod +x $BUILD_NAME/DEBIAN/postinst

mkdir -p $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper
cp Adafruit_Video_Looper/alsa_config.py        $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/baselog.py            $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/directory.py          $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/hello_video.py        $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/__init__.py           $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/lomo_home.py          $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/lomoplayer.py         $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/model.py              $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/omxplayer.py          $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/playlist_builders.py  $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/usb_drive_copymode.py $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/usb_drive_mounter.py  $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/usb_drive.py          $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/utils.py              $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/video_looper.py       $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/

mkdir -p $BUILD_NAME/opt/lomorage/var
cp assets/video_looper.ini  $BUILD_NAME/opt/lomorage/var/

mkdir -p $BUILD_NAME/etc/supervisor/conf.d
cp assets/video_looper.conf $BUILD_NAME/etc/supervisor/conf.d/

mkdir -p $BUILD_NAME/opt/lomorage/lib/lib

cp deps/arm/libde265.a         $BUILD_NAME/opt/lomorage/lib/lib/
cp deps/arm/libde265.la        $BUILD_NAME/opt/lomorage/lib/lib/
cp deps/arm/libde265.so.0.0.12 $BUILD_NAME/opt/lomorage/lib/lib/

cp deps/arm/libheif.a          $BUILD_NAME/opt/lomorage/lib/lib/
cp deps/arm/libheif.la         $BUILD_NAME/opt/lomorage/lib/lib/
cp deps/arm/libheif.so.1.6.2   $BUILD_NAME/opt/lomorage/lib/lib/

cp deps/arm/libSDL_image.a                $BUILD_NAME/opt/lomorage/lib/lib/
cp deps/arm/libSDL_image.la               $BUILD_NAME/opt/lomorage/lib/lib/
cp deps/arm/libSDL_image-1.2.so.0.8.4     $BUILD_NAME/opt/lomorage/lib/lib/

chown root:root -R $BUILD_NAME
dpkg -b $BUILD_NAME
