#!/bin/bash
#xrandr --newmode $(cvt 464 1000 60 | grep Modeline | cut -d' ' -f2- -)
#mode=$(xrandr | grep 464 | cut -d'(' -f2- | sed 's/).*//' | grep 0x)
#xrandr --addmode LVDS-1 $mode
#xrandr --output LVDS-1 --mode $mode
cd ~/patreon
#./patreon_posts.py --sync-posts --sync-media --sync-pages 1
#./patreon_posts.py --sync-pages --sync-media --sync-pages
./patreon_posts.py --sync-pages
cp patreon.html.j2 /var/www/html/patreon.html
cp -- *.html /var/www/html
cp -- *.css /var/www/html
cp -- *.png /var/www/html
cp -- *.webm /var/www/html
cp -- *.jpg /var/www/html
#mate-session-save --force-logout
