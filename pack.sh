#!/bin/bash
set -e

nowDate=$(date +"%Y-%m-%d")
nowTime=$(date +"%H-%M-%S")
commitHash=$(git rev-parse --short HEAD)
VERSION="$nowDate.$nowTime.0.$commitHash"

PACKAGE_NAME="lomo-frame"
BUILD_NAME=$PACKAGE_NAME
INI_FILE=/opt/lomorage/var/video_looper.ini
NEW_INI_FILE=/opt/lomorage/var/video_looper.ini.new

rm -rf lomo-frame_*

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
Depends: python3, python3-pyudev, python3-pygame, python3-watchdog, supervisor, vlc, ntfs-3g, exfat-fuse, ffmpeg, lomo-framed
Maintainer: Jeromy Fu<fuji246@gmail.com>
Description: Lomorage Digital Frame
EOF

cat << EOF > $BUILD_NAME/DEBIAN/preinst
#!/bin/bash
if [ -f "/lib/systemd/system/supervisor.service" ]
then
    service supervisor stop
fi
EOF
chmod +x $BUILD_NAME/DEBIAN/preinst

cat << EOF > $BUILD_NAME/DEBIAN/postinst
#!/bin/bash
ln -sf /opt/lomorage/lib/lomoframe/libde265.so.0.0.12        /opt/lomorage/lib/lomoframe/libde265.so
ln -sf /opt/lomorage/lib/lomoframe/libde265.so.0.0.12        /opt/lomorage/lib/lomoframe/libde265.so.0
ln -sf /opt/lomorage/lib/lomoframe/libheif.so.1.6.2          /opt/lomorage/lib/lomoframe/libheif.so
ln -sf /opt/lomorage/lib/lomoframe/libheif.so.1.6.2          /opt/lomorage/lib/lomoframe/libheif.so.1
ln -sf /opt/lomorage/lib/lomoframe/libSDL_image-1.2.so.0.8.4 /opt/lomorage/lib/lomoframe/libSDL_image.so
ln -sf /opt/lomorage/lib/lomoframe/libSDL_image-1.2.so.0.8.4 /opt/lomorage/lib/lomoframe/libSDL_image-1.2.so.0

if [ -f "$INI_FILE" ]; then
    echo "difference of configuration:"
    diff "$NEW_INI_FILE" "$INI_FILE"
    mv "$INI_FILE" "$INI_FILE.bak"
fi
mv "$NEW_INI_FILE" "$INI_FILE"

#sudo -u pi bash -c "/sbin/framectrl.sh add"

sed -i 's/geteuid/getppid/' /usr/bin/vlc
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
cp Adafruit_Video_Looper/playlist_builders.py  $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/usb_drive_copymode.py $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/usb_drive_mounter.py  $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/usb_drive.py          $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/utils.py              $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/
cp Adafruit_Video_Looper/video_looper.py       $BUILD_NAME/usr/lib/python3/dist-packages/Adafruit_Video_Looper/

mkdir -p $BUILD_NAME/sbin
cp framectrl.sh $BUILD_NAME/sbin/

mkdir -p $BUILD_NAME/opt/lomorage/var/log
cp assets/video_looper.ini  $BUILD_NAME/$NEW_INI_FILE

mkdir -p $BUILD_NAME/etc/supervisor/conf.d
cp assets/video_looper.conf $BUILD_NAME/etc/supervisor/conf.d/

mkdir -p $BUILD_NAME/etc/cron.weekly
cp rescan.sh $BUILD_NAME/etc/cron.weekly/

mkdir -p $BUILD_NAME/opt/lomorage/lib/lomoframe

cp deps/arm/libde265.a                    $BUILD_NAME/opt/lomorage/lib/lomoframe/
cp deps/arm/libde265.la                   $BUILD_NAME/opt/lomorage/lib/lomoframe/
cp deps/arm/libde265.so.0.0.12            $BUILD_NAME/opt/lomorage/lib/lomoframe/
cp deps/arm/libheif.a                     $BUILD_NAME/opt/lomorage/lib/lomoframe/
cp deps/arm/libheif.la                    $BUILD_NAME/opt/lomorage/lib/lomoframe/
cp deps/arm/libheif.so.1.6.2              $BUILD_NAME/opt/lomorage/lib/lomoframe/
cp deps/arm/libSDL_image.a                $BUILD_NAME/opt/lomorage/lib/lomoframe/
cp deps/arm/libSDL_image.la               $BUILD_NAME/opt/lomorage/lib/lomoframe/
cp deps/arm/libSDL_image-1.2.so.0.8.4     $BUILD_NAME/opt/lomorage/lib/lomoframe/

#chown pi:pi -R $BUILD_NAME
dpkg -b $BUILD_NAME
