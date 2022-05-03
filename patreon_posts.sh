#!/bin/bash
# work-in-progress/temporary wrapper
#xrandr --newmode $(cvt 464 1000 60 | grep Modeline | cut -d' ' -f2- -)
#mode=$(xrandr | grep 464 | cut -d'(' -f2- | sed 's/).*//' | grep 0x)
#xrandr --addmode LVDS-1 $mode
#xrandr --output LVDS-1 --mode $mode
cd ~/patreon

#invocations
#./patreon_posts.py --sync-posts --sync-media --sync-pages 1
./patreon_posts.py --sync-posts --sync-media --sync-pages
#./patreon_posts.py --sync-media --sync-pages
#./patreon_posts.py --sync-pages

# test 
#cp patreon.html.j2 patreon.html
#scp -- *.html tacokoneko@192.168.120.77:/var/www/html
#scp -- *.css tacokoneko@192.168.120.77:/var/www/html
#scp -- *.png tacokoneko@192.168.120.77:/var/www/html
#scp -- *.webm tacokoneko@192.168.120.77:/var/www/html
#scp -- *.jpg tacokoneko@192.168.120.77:/var/www/html
#scp -- favicon.ico tacokoneko@192.168.120.77:/var/www/html

# prod
#cp patreon.html.j2 patreon.html
#cp -- *.html /var/www/html
#cp -- *.css /var/www/html
#cp -- *.png /var/www/html
#cp -- *.webm /var/www/html
#cp -- *.jpg /var/www/html
#cp -- favicon.ico /var/www/html
#mate-session-save --force-logout
