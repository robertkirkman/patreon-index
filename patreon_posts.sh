#!/bin/bash
set -euo pipefail
cd $(realpath "$(dirname "$0")")
export DISPLAY=:0.0
# ./update_patreon_token.py 2>&1 | tee update_patreon_token.log
export PATREON_ACCESS_TOKEN=$(cat patreon_token.txt)
./patreon_posts.py --download-posts --download-media --process-media --generate-site 2>&1 | tee patreon_posts.log
cp -- *.html /var/www/html
cp -- *.css  /var/www/html
cp -- *.png  /var/www/html
cp -- *.ico  /var/www/html
cp -- *.webm /var/www/html
cp -- *.jpg  /var/www/html
