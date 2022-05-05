#!/bin/bash
# work-in-progress/temporary wrapper
xrandr --newmode $(cvt 464 1000 60 | grep Modeline | cut -d' ' -f2- -)
mode=$(xrandr | grep 464 | cut -d'(' -f2- | sed 's/).*//' | grep 0x)
xrandr --addmode eDP $mode
xrandr --output eDP --mode $mode
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
cp patreon.html.j2 patreon.html
cp -- *.html /var/www/html
cp -- *.css /var/www/html
cp -- *.png /var/www/html
cp -- favicon.ico /var/www/html
mv -- *.webm /var/www/html
mv -- *.jpg /var/www/html
rm -- *.gif
mate-session-save --force-logout
