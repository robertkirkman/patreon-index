# patreon-index

This is the source code of the Rita Kirkman Studio Patreon Index Website.

[Live](https://www.ritakirkman.com/page/39921/patreon-index)

## Developer information

### Server-side dependencies

- [bash](http://www.gnu.org/software/bash/)
- [Python](https://www.python.org/)
- [Jinja](https://jinja.palletsprojects.com/en/stable/)
- [FFmpeg](https://www.ffmpeg.org/)
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [Pillow](https://python-pillow.github.io/)
- [Firefox](https://www.firefox.com/en-US/)
- [geckodriver](https://github.com/mozilla/geckodriver)
- [selenium](https://pypi.org/project/selenium/)
- [patreon-python 0.5.1](https://github.com/Patreon/patreon-python/issues/30)
- [fake-useragent](https://github.com/fake-useragent/fake-useragent)
- [Patreon creator account](https://www.patreon.com/create)
- For deployment, a web server and a cron daemon recommended
  - [nginx](https://nginx.org/) suggested for a web server
  - [cronie](https://github.com/cronie-crond/cronie) suggested for a cron daemon


### Relevant code that any forks should consider editing first

- The `.j2` template files with the custom header links, and the `patreon.html.j2` homepage template with the personalized description at the bottom

- The `generate_site()` function in `patreon_posts.py`, which defines which custom pages are generated with which combinations of tag words

https://github.com/robertkirkman/patreon-index/blob/2fb2dc08e7b8551bf611ecca84ec81459c2f87fa/patreon_posts.py#L268-L273

- If you are using an X11 server, change the `DISPLAY` variable in `patreon_posts.sh` to the correct value for your system

https://github.com/robertkirkman/patreon-index/blob/2fb2dc08e7b8551bf611ecca84ec81459c2f87fa/patreon_posts.sh#L2

- Modify the `color:`, `font-family:` and `@font-face` attributes in the `patreon.css` file to apply your desired color scheme and fonts

- Customize the logic that determines what kind of tag words identify video posts that are allowed to have GIF thumbnails, versus video posts that are only allowed to have still thumbnails

https://github.com/robertkirkman/patreon-index/blob/2fb2dc08e7b8551bf611ecca84ec81459c2f87fa/patreon_posts.py#L158

- Set the installation location of patreon-index appropriately

https://github.com/robertkirkman/patreon-index/blob/38eb2861a11917d1b09729c12b0d051b6ea9750a/patreon_posts.sh#L3

- Set the HTML root directory of the web server appropriately

https://github.com/robertkirkman/patreon-index/blob/38eb2861a11917d1b09729c12b0d051b6ea9750a/patreon_posts.sh#L8


### Code that can sometimes require manual editing

> [!NOTE]
> This code should ideally be rewritten to be fully automated.

- xpaths of buttons on the [Patreon API Keys portal](https://www.patreon.com/portal/registration/register-clients)

https://github.com/robertkirkman/patreon-index/blob/2fb2dc08e7b8551bf611ecca84ec81459c2f87fa/update_patreon_token.py#L36-L38


### Suggested setup

1. Install the dependencies on your platform.
  - Be careful to make sure you follow the examples of the users in the [linked patreon-python issue to get patreon-python **version 0.5.1**](https://github.com/Patreon/patreon-python/issues/30), not the version of patreon-python that's on PyPi if that version's still only version 0.5.0 when you read this.
  - Also make sure to check that you do **not** have [python-ffmpeg](https://github.com/jonghwanhyeon/python-ffmpeg) installed, and uninstall it if you do, because it is different from the one that is necessary for patreon-index, [ffmpeg-python](https://github.com/kkroening/ffmpeg-python), and having python-ffmpeg installed could result in a conflict.

2. Make the appropriate modifications to the code marked above in the "consider editing first" section.

3. Log into your Patreon creator account at https://www.patreon.com/create, then copy and paste your Firefox profile folder from `~/.mozilla/firefox/` to `~/patreon-index/` and rename it to "`profile`".

4. Run the command `./patreon_posts.sh` and wait for it to complete.

5. Preview website at file:///var/www/html/patreon.html.

6. If desired, deploy website by [enabling the nginx service on your platform](https://nginx.org/en/docs/beginners_guide.html) and performing the setup on a VPS or other server that can forward the ports for HTTP and HTTPS.

7. If desired, set website to automatically fetch and index new posts by setting `crontab -e` to run `patreon_posts.sh`. Example to run `patreon_posts.sh` every day at 7:30 AM:

```
30 7 * * * /home/user/patreon-index/patreon_posts.sh
```
