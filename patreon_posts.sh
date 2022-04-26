#!/bin/bash
xrandr --newmode $(cvt 464 1000 60 | grep Modeline | cut -d' ' -f2- -)
mode=$(xrandr | grep 464 | cut -d'(' -f2- | sed 's/).*//' | grep 0x)
xrandr --addmode LVDS-1 $mode
xrandr --output LVDS-1 --mode $mode
cd ~/patreon
~/patreon/patreon_posts.py --download
#~/patreon/patreon_posts.py
cp ~/patreon/*.html /var/www/html
cp ~/patreon/*.css /var/www/html
mate-session-save --force-logout 
