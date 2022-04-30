#!/bin/bash
#xrandr --newmode $(cvt 464 1000 60 | grep Modeline | cut -d' ' -f2- -)
#mode=$(xrandr | grep 464 | cut -d'(' -f2- | sed 's/).*//' | grep 0x)
#xrandr --addmode LVDS-1 $mode
#xrandr --output LVDS-1 --mode $mode
cd ~/patreon
#/patreon_posts.py --sync-posts --sync-media --sync-pages
#./patreon_posts.py --sync-pages --sync-media
./patreon_posts.py --sync-pages
cp *.html /var/www/html
cp *.css /var/www/html
cp *.png /var/www/html
#for i in *.webm; do ffmpeg -y -ss 00:00:06 -to 00:00:10 -i ./$i -vcodec libvpx-vp9 -crf 25 ./$i.webm; mv -- $i.webm $i; done
#for i in *.mp4; do ffmpeg -y -ss 00:00:06 -to 00:00:10 -i ./$i -vcodec libvpx-vp9 -crf 25 ./$i.webm; mv -- $i.webm $i; done
#for i in *.mp4; do mv -- "$i" "${i%.mp4}.webm"; done
#rm -- *.webm.webm
mv -- *.webm /var/www/html
mv -- *.jpg /var/www/html
#mate-session-save --force-logout
