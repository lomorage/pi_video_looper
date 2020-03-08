# !/bin/bash

set -e

HOUR_ON=08
MIN_ON=00

HOUR_OFF=21
MIN_OFF=00

OPTIONS="-o '' -l on-hour:,on-min:,off-hour:,off-min:"
PARSED=$(getopt $OPTIONS $*)
if [ $? -ne 0 ]; then
    exit 2
fi

eval set -- "$PARSED"

while [ $# -gt 0 ]
do
    case "$1" in
        --on-hour)
            HOUR_ON=$2
            shift 2
            ;;
        --on-min)
            MIN_ON=$2
            shift 2
            ;;
        --off-hour)
            HOUR_OFF=$2
            shift 2
            ;;
        --off-min)
            MIN_OFF=$2
            shift 2
            ;;
        --)
	    shift
            break
            ;;
        *)
            echo "option not found!"
            exit 3
            ;;
    esac
done

frame_off_cmd="vcgencmd display_power 0;sudo service supervisor stop"
frame_off_job="$MIN_OFF $HOUR_OFF * * * $frame_off_cmd"

frame_on_cmd="vcgencmd display_power 1;sudo service supervisor start"
frame_on_job="$MIN_ON $HOUR_ON * * * $frame_on_cmd"

remove_job() {
	$( (crontab -l | grep -v -F "$frame_on_cmd" ) | crontab -)
	$( (crontab -l | grep -v -F "$frame_off_cmd" ) | crontab -)
	echo "cron jobs:"
	crontab -l
}

add_job() {
	$( (crontab -l | grep -v -F "$frame_on_cmd" ; echo "$frame_on_job" ) | crontab -)
	$( (crontab -l | grep -v -F "$frame_off_cmd" ; echo "$frame_off_job" ) | crontab -)
	echo "cron jobs:"
	crontab -l
}

frame_on() {
	eval $frame_on_cmd
}

frame_off() {
	eval $frame_off_cmd
}

case "$1" in
        add)
		add_job
		;;
	remove)
		remove_job
		;;
        on)
	        frame_on
		;;
        off)
	        frame_off
		;;
	*)
		echo "Usage: $0 { add | remove | on | off } --on-hour [00-23] --on-min [00-59] --off-hour [00-23] --off-min [00-59]" >&2
		exit 3
		;;
esac
