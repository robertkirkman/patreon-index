#!/bin/bash
export DISPLAY=:0.0
cd ~/patreon-index
./update_patreon_token.py > update_patreon_token.log 2>&1
export PATREON_ACCESS_TOKEN=$(cat patreon_token.txt)
./patreon_posts.py --download-posts --download-media --process-media --generate-site > patreon_posts.log 2>&1
cp patreon.html.j2 patreon.html
cp -- *.html /var/www/html
cp -- *.css  /var/www/html
cp -- *.png  /var/www/html
cp -- *.ico  /var/www/html
cp -- *.webm /var/www/html
cp -- *.jpg  /var/www/html
