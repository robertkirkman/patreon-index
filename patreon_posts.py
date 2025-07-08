#!/usr/bin/python
import os
import pickle
import re
import sys
import time
import json
import unicodedata
import patreon
from datetime import date
from operator import attrgetter
from os.path import exists
from pathlib import Path
from shlex import quote as cmd_quote
from urllib.parse import parse_qs, urlparse

import pdb
import ffmpeg
import jinja2
import requests
from PIL import Image
from PIL import UnidentifiedImageError
from yt_dlp import YoutubeDL


# tag class to store the data necessary to generate tag page
class tag:
    name = ""
    nb_name = ""
    slug = ""
    count = 0

    def __init__(self, name, nb_name, slug, count):
        self.name = name
        self.nb_name = nb_name
        self.slug = slug
        self.count = count


# download all posts in the campaign, mark them with icon and post_type depending on a
# custom arbitrary pattern of decisions that uses the post metadata, and store them in a file
def download_posts(cookies_pickle_filename, posts_pickle_filename, access_token):
    with open(cookies_pickle_filename, "rb") as file:
        cookies = pickle.load(file)
    api_client = patreon.API(access_token)
    campaign_response = api_client.get_campaigns(1)
    try:
        campaign_id = campaign_response.data()[0].id()
    except AttributeError:
        print("ACCESS_TOKEN invalid! Please update ACCESS_TOKEN.")

    posts_json = []
    cursor = True
    while cursor:
        posts_url = (
            "https://www.patreon.com/api/oauth2/v2/campaigns/"
            + campaign_id
            + "/posts?page[size]=1000"
        )
        if cursor and isinstance(cursor, str):
            posts_url += "&page[cursor]=" + cursor
        posts_response = requests.get(
            url=posts_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            cursor = json.loads(posts_response.text)["meta"]["pagination"]["cursors"]["next"]
        except:
            cursor = False
        posts_json += json.loads(posts_response.text)["data"]

    posts = []
    for post_iterator in posts_json:
        post_url = "https://www.patreon.com/api/posts/" + post_iterator["id"]
        post = requests.get(
            url=post_url,
            cookies=cookies,
            headers={
                "User-Agent": "Patreon-Python, version 0.5.0, platform Linux-5.4.170+-x86_64-with-glibc2.29"
            },
        )

        try:
            post_json = json.loads(post.text)
        except json.decoder.JSONDecodeError:
            print("failed to load json from post with url: " + post_url)

        post_json["data"]["attributes"]["title_slug"] = slugify(
            post_json["data"]["attributes"]["title"]
        )
        post_type = post_json["data"]["attributes"]["post_type"]
        post_tags = tags(post_json)
        icon = "unknown"
        if post_type == "text_only" or post_type == "poll":
            icon = "text"
        elif post_type == "image_file" or post_type == "link":
            image_url = post_json["data"]["attributes"]["image"]["url"]
            if "gif" in str(
                requests.head(image_url, allow_redirects=True).headers["Content-Type"]
            ):
                icon = "gif"
            elif post_type == "link":
                icon = "link"
            else:
                icon = "image"
        elif post_type == "video_embed" or post_type == "video_external_file":
            if post_type == "video_embed":
                try:
                    url = post_json["data"]["attributes"]["embed"]["url"]
                except KeyError:
                    print("error: " + post_json["data"]["attributes"]["title_slug"] + " has post_type video_embed but has no embed url associated with it")
                    url = post_json["data"]["attributes"]["url"]
            else:
                try:
                    url = post_json["data"]["attributes"]["post_file"]["url"]
                except KeyError:
                    print("error: " + post_json["data"]["attributes"]["title_slug"] + " has post_type video_external_file but has no post_file url associated with it")
                    url = post_json["data"]["attributes"]["url"]

            if get_vid(url):
                if (
                    "speed video" in post_tags
                    and "Premium video post" not in post_tags
                    and "video montage" not in post_tags
                ):
                    icon = "speedvideo"
                else:
                    icon = "video"
            else:
                icon = "image"
        
        post_json["data"]["attributes"]["icon_type"] = icon
        posts.append(post_json)
    with open(posts_pickle_filename, "wb") as file:
        pickle.dump(posts, file)


# use yt-dlp, ffmpeg and pillow to download all non-GIF media referenced by the collected metadata
def download_media(posts_pickle_filename):
    if not exists(posts_pickle_filename):
        print(posts_pickle_filename + " missing! Cannot download media.")
        return
    with open(posts_pickle_filename, "rb") as file:
        posts = pickle.load(file)
    for post in posts:
        post_slug = post["data"]["attributes"]["title_slug"]
        post_type = post["data"]["attributes"]["post_type"]
        icon_type = post["data"]["attributes"]["icon_type"]
        print(post_slug)
        print(post_type)
        print(icon_type)
        if icon_type == "video" or icon_type == "speedvideo":
            if post_type == "video_embed":
                yt_url = post["data"]["attributes"]["embed"]["url"]
            else:
                yt_url = post["data"]["attributes"]["post_file"]["url"]
            vid = get_vid(yt_url)
            if icon_type == "speedvideo":
                filename = post_slug + ".webm"
                while not exists(filename):
                    if post_type == "video_embed":
                        ydl_opts = {
                            "retries": 100,
                            "ignoreerrors": True,
                            "outtmpl": vid,
                            "format": format_selector,
                        }
                    else:
                        ydl_opts = {
                            "retries": 100,
                            "ignoreerrors": True,
                            "outtmpl": vid,
                        }

                    with YoutubeDL(ydl_opts) as ydl:
                        ydl.download(yt_url)
                    if exists(vid + ".mp4"):
                        os.rename(vid + ".mp4", filename)
                    if exists(vid + ".webm"):
                        os.rename(vid + ".webm", filename)
            else:
                if post_type == "video_embed":
                    filename = post_slug + ".jpg"
                else:
                    filename = post_slug + "_processed.jpg"
                while not exists(filename):
                    if post_type == "video_embed":
                        ydl_opts = {
                            "retries": 100,
                            "ignoreerrors": True,
                            "writethumbnail": True,
                            "skip_download": True,
                            "outtmpl": "%(id)s",
                            "format": format_selector,
                        }
                        with YoutubeDL(ydl_opts) as ydl:
                            ydl.download(yt_url)
                    else:
                        # this one is a real jpg already
                        image_url = post["data"]["attributes"]["thumbnail"]["url"]
                        image = requests.get(image_url)
                        with open(filename, "wb") as f:
                            f.write(image.content)
                    # NOT a jpg yet, named temporarily for convenience
                    if exists(vid + ".webp"):
                        os.rename(vid + ".webp", filename)
        elif icon_type == "image" or icon_type == "gif" or icon_type == "link":
            if icon_type == "gif":
                image_filename = post_slug + ".gif"
            else:
                image_filename = post_slug + ".jpg"
            if not exists(image_filename):
                image_url = post["data"]["attributes"]["image"]["url"]
                image = requests.get(image_url)
                with open(image_filename, "wb") as f:
                    f.write(image.content)


# process the media by reencoding, scaling and trimming as desired
def process_media():
    images = [
        file
        for file in os.listdir()
        if file.endswith(("jpg")) and "processed" not in file
    ]
    gifs = [file for file in os.listdir() if file.endswith(("gif"))]
    videos = [
        file
        for file in os.listdir()
        if file.endswith(("webm")) and "processed" not in file
    ]
    for image in images:
        image_dest = image.split(".")[0] + "_processed.jpg"
        if not exists(image_dest):
            try:
                img = Image.open(image).convert("RGB")
                img.thumbnail((300, 300))
                img.save(image_dest, optimize=True, quality=85)
            except UnidentifiedImageError:
                print("image invalid or corrupted: " + image)
    for gif in gifs:
        gif_dest = gif.split(".")[0] + "_processed.webm"
        if not exists(gif_dest):
            ffmpeg.input(gif).filter("scale", -1, 300).output(
                gif_dest,
                ss=("00:00:02"),
                to=("00:00:06"),
                vcodec="libvpx-vp9",
                pix_fmt="yuv420p",
                movflags="faststart",
                crf=35,
            ).overwrite_output().run()
    for video in videos:
        video_dest = video.split(".")[0] + "_processed.webm"
        if not exists(video_dest):
            ffmpeg.input(video).filter("scale", -1, 300).output(
                video_dest,
                ss=("00:00:06"),
                to=("00:00:10"),
                vcodec="libvpx-vp9",
                movflags="faststart",
                crf=35,
            ).overwrite_output().run()


# generate all pages for the index in a modular way that can be rapidly prototyped
# to demo for the client
def generate_site(posts_pickle_filename):
    vos_sort = "ordinal"
    # tags chosen by the client for a series of manually-chosen categories
    premium = ["Premium video post"]
    vos = ["VOS day"]
    paint_along = ["Paint-Along"]
    animal = ["animals"]
    portrait = ["portrait"]
    landscape = ["landscape"]
    pasteling = ["pastel"]
    underpainting = ["underpainting"]
    progress_pic = ["progress pics"]
    speed_video = ["speed video"]
    video_montage = ["video montage"]
    color_palette = ["color palette"]
    art_tip = ["art tips"]
    conversation = ["conversation"]
    problem_solving = ["problem solving"]
    bonus_full_length_videos = ["Free Full-Length Videos"]
    cow = ["cows"]
    bunny = ["bunny"]
    sheep = ["sheep"]
    bird = ["bird"]
    wildlife = ["wildlife"]
    pet_portrait = ["pet portrait"]
    drawing = ["drawing"]
    goat = ["goat"]
    deer = ["deer"]
    donkey = ["donkey"]
    horse = ["horse"]
    pig = ["pig"]
    still_life = ["still life"]
    no_subject = ["nada subject"]
    inspiration = ["Inspiration"]
    bug = ["bugs"]
    caricature = ["caricatures"]
    squirrel = ["squirrel"]

    # deserialize the previously-stored list of posts from pickle file
    if not exists(posts_pickle_filename):
        print(posts_pickle_filename + " missing! Cannot generate posts.")
        return

    with open(posts_pickle_filename, "rb") as file:
        posts = pickle.load(file)

    # generate all the pages needed for the index site
    generate_page(posts, "ALL")

    generate_page(posts, "ALL VOS EPISODE", vos, sort=vos_sort)
    generate_page(posts, "VOS PAINT-ALONG", vos + paint_along, sort=vos_sort)
    generate_page(posts, "VOS ANIMAL", vos + animal, sort=vos_sort)
    generate_page(posts, "VOS PORTRAIT", vos + portrait, sort=vos_sort)
    generate_page(posts, "VOS LANDSCAPE", vos + landscape, sort=vos_sort)
    generate_page(posts, "VOS PASTELING", vos + pasteling, sort=vos_sort)
    generate_page(posts, "VOS UNDERPAINTING", vos + underpainting, sort=vos_sort)
    generate_page(
        posts,
        "OTHER VOS EPISODE",
        vos,
        paint_along + animal + portrait + landscape + pasteling + underpainting,
        vos_sort,
    )
    generate_page(posts, "OTHER PREMIUM", premium, vos)

    generate_page(posts, "ALL PUBLIC", without_tags=premium)

    generate_page(posts, "ART TIP", art_tip, premium)
    generate_page(posts, "BONUS FULL-LENGTH VIDEO", bonus_full_length_videos, premium)
    generate_page(posts, "CONVERSATION", conversation, premium)
    generate_page(posts, "INSPIRATION", inspiration, premium)
    generate_page(posts, "PROBLEM SOLVING", problem_solving, premium)
    generate_page(posts, "PROGRESS PIC", progress_pic, premium)
    generate_page(posts, "SPEED VIDEO", speed_video, premium)
    generate_page(posts, "VIDEO MONTAGE", video_montage, premium)
    generate_page(posts, "COLOR PALETTE", color_palette, premium)
    generate_page(
        posts,
        "OTHER PUBLIC",
        without_tags=premium
        + progress_pic
        + speed_video
        + video_montage
        + color_palette
        + art_tip
        + conversation
        + inspiration
        + problem_solving
        + bonus_full_length_videos,
    )

    generate_page(posts, "BIRD", bird, no_subject)
    generate_page(posts, "BUNNY", bunny, no_subject)
    generate_page(posts, "COW", cow, no_subject)
    generate_page(posts, "DONKEY", donkey, no_subject)
    generate_page(posts, "ALL DRAWING", drawing, no_subject)
    generate_page(posts, "CARICATURE", caricature, no_subject)
    generate_page(posts, "LANDSCAPE DRAWING", drawing + landscape, no_subject)
    generate_page(posts, "ANIMAL DRAWING", drawing + animal, no_subject)
    generate_page(posts, "HUMAN DRAWING", drawing + portrait, no_subject)
    generate_page(posts, "OTHER DRAWING", drawing, caricature + landscape + animal + portrait + no_subject)
    generate_page(posts, "GOAT", goat, no_subject)
    generate_page(posts, "HORSE", horse, no_subject)
    generate_page(posts, "LANDSCAPE", landscape, no_subject)
    generate_page(posts, "PIG", pig, no_subject)
    generate_page(posts, "PET PORTRAIT", pet_portrait, no_subject)
    generate_page(posts, "HUMAN PORTRAIT", portrait, no_subject)
    generate_page(posts, "SHEEP", sheep, no_subject)
    generate_page(posts, "ALL WILDLIFE", wildlife, no_subject)
    generate_page(posts, "WILD BIRD", wildlife + bird, no_subject)
    generate_page(posts, "BUG", bug, no_subject)
    generate_page(posts, "DEER", deer, no_subject)
    generate_page(posts, "SQUIRREL", squirrel, no_subject)
    generate_page(posts, "OTHER WILDLIFE", wildlife, bird + bug + deer + squirrel + no_subject)
    generate_page(posts, "STILL LIFE", still_life, no_subject)
    generate_page(
        posts,
        "OTHER SUBJECT",
        without_tags=bird
        + bunny
        + cow
        + donkey
        + caricature
        + drawing
        + goat
        + horse
        + landscape
        + pig
        + pet_portrait
        + portrait
        + sheep
        + wildlife
        + bug
        + deer
        + squirrel
        + still_life
        + no_subject,
    )

    generate_tag_pages(posts)


# filter by tags and sort the posts, then use jinja2 to populate the page with data and write
# it to a new file
def generate_page(posts, filename, with_tags=[], without_tags=[], sort="temporal"):
    posts = filter_posts(posts, with_tags, without_tags)
    posts = sort_posts(posts, sort)
    current_date = date.today()
    page = (
        jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
        .get_template("template.html.j2")
        .render(filename=filename, date=current_date, posts=posts)
    )
    with open(filename + ".html", "w") as f:
        f.write(page)


# filter the list of posts by tags inclusively and exclusively
def filter_posts(posts, with_tags, without_tags):
    if with_tags:
        posts = [post for post in posts if include_tags(post, with_tags)]
    if without_tags:
        posts = [post for post in posts if exclude_tags(post, without_tags)]
    return posts


# keep only posts containing all given tags
def include_tags(post, with_tags):
    keep = True
    for tag in with_tags:
        if tag not in tags(post):
            keep = False
    return keep


# keep only posts containing none of the given tags
def exclude_tags(post, without_tags):
    keep = True
    for tag in without_tags:
        if tag in tags(post):
            keep = False
    return keep


def tags(post):
    tags = []
    for tag_iter in post["data"]["relationships"]["user_defined_tags"]["data"]:
        tags.append(tag_iter["id"].split(";", 1)[1])
    return tags


# sort posts alphabetically case-insensitive, ordinally by the first number detected,
# or do not sort posts at all
def sort_posts(posts, sort):
    match sort:
        case "alphabetical":
            keyfun = lambda post: post["data"]["attributes"]["title"].upper()
            posts.sort(key=keyfun, reverse=False)
        case "ordinal":
            keyfun = (
                lambda post: list(
                    map(int, re.findall(r"\d+", post["data"]["attributes"]["title"]))
                )[0]
                if list(
                    map(
                        int,
                        re.findall(r"\d+", post["data"]["attributes"]["title"]),
                    )
                )
                else 0
            )
            posts.sort(key=keyfun, reverse=True)
        case "temporal":
            keyfun = lambda post: int(
                re.sub("[^0-9]", "", post["data"]["attributes"]["published_at"])
            )
            posts.sort(key=keyfun, reverse=True)
        case "_":
            pass
    return posts


# extract youtube video id from a youtube url
def get_vid(url):
    """Returns Video_ID extracting from the given url of Youtube or mux.com

    Examples of URLs:
      Valid:
        'http://youtu.be/_lOT2p_FCvA',
        'www.youtube.com/watch?v=_lOT2p_FCvA&feature=feedu',
        'http://www.youtube.com/embed/_lOT2p_FCvA',
        'http://www.youtube.com/v/_lOT2p_FCvA?version=3&amp;hl=en_US',
        'https://www.youtube.com/watch?v=rTHlyTphWP0&index=6&list=PLjeDyYvG6-40qawYNR4juzvSOg-ezZ2a6',
        'youtube.com/watch?v=_lOT2p_FCvA',
        'https://stream.mux.com/MCPFt6R8J9s02NUd9tA01aUZdNqiXQ5cMMecJHlBRiMTw.m3u8?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik5CY3o3Sk5RcUNmdDdWcmo5MWhra2lEY3Vyc2xtRGNmSU1oSFUzallZMDI0In0.eyJzdWIiOiJNQ1BGdDZSOEo5czAyTlVkOXRBMDFhVVpkTnFpWFE1Y01NZWNKSGxCUmlNVHciLCJleHAiOjE2Njk2NDQwMDAsImF1ZCI6InYiLCJwbGF5YmFja19yZXN0cmljdGlvbl9pZCI6IklyMDJGbXFzcVVuTUlwRXFIODlNZGx2V2ExNVF3T282ZENuZWxDdFNJOVlJIn0.UpirIC1KJ8RTUTSnVJxRjanMsakiH25pjRamf0PbKYS2zg6CA7ybNaC0ApIwnOt_H5qnlWKmB913596R8z05trb2vAqlMYQlwh4BdEi-5ROxuc6yeNOUOiuA_ix8IMue4xvmrzG0_PQtRez_-kU58XMgg5W18MbwSm3i7nyuAKU9NGunUkIM21_jcqjMOZ_iAa8PrgIl-DtFwVx_a3DdvLIdzKrvNm7C_-Ap-tZSqh_M-CedXU47A_ZdzeHg33_DErHjl65uRfb1X62pZEPfFlShrsQo_z1_NFPl94MoAiqP0xYCv99_zikO9OEoEal12s1B50NPAdGQlPA8zVgAIg'

      Invalid:
        'youtu.be/watch?v=_lOT2p_FCvA',
    """

    if url.startswith(("youtu", "www")):
        url = "http://" + url

    query = urlparse(url)

    if "youtube" in query.hostname:
        if query.path == "/watch":
            return parse_qs(query.query)["v"][0]
        elif query.path.startswith(("/embed/", "/v/")):
            return query.path.split("/")[2]
    elif "youtu.be" in query.hostname:
        return query.path[1:]
    elif "mux.com" in query.hostname:
        return query.path[1:].split('.', 1)[0]
    else:
        return ""


# choose only mp4s at least 360p for yt-dlp format selection
def format_selector(ctx):
    """Select the best video and the best audio that won't result in an mkv.
    NOTE: This is just an example and does not handle all cases"""

    # formats are already sorted worst to best
    formats = ctx.get("formats")[::-1]

    # first mp4 without audio that is at least 360p
    best_video = next(
        f
        for f in formats
        if f["acodec"] == "none"
        and f["height"] >= 360
        and f["ext"] == "mp4"
    )

    # These are the minimum required fields for a merged format
    yield {
        "format_id": f'{best_video["format_id"]}',
        "ext": best_video["ext"],
        "requested_formats": [best_video],
        # Must be + separated list of protocols
        "protocol": f'{best_video["protocol"]}',
    }


# deterministically convert strings into readable equivalents that are filename-friendly
def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


# derive a list of all tags from the list of posts, then iterate it to generate a tag homepage
# and pages of posts sorted by tags
def generate_tag_pages(posts):
    filename = "TAGS"
    post_tags = extract_tags(posts)
    current_date = date.today()
    page = (
        jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
        .get_template("tags_template.html.j2")
        .render(
            filename=filename,
            date=current_date,
            tags=post_tags,
        )
    )
    with open(filename + ".html", "w") as f:
        f.write(page)
    for tag in post_tags:
        generate_page(posts, tag.slug, [tag.name])


# count the occurrences of posts associated with each possible tag, store the data in a list of tags,
# and generate a non-breaking title for the tag to display nicely on the tags page
def extract_tags(posts):
    post_tags = []
    for post in posts:
        for post_tag in tags(post):
            if post_tag not in (tag.name for tag in post_tags):
                post_tags.append(
                    tag(
                        post_tag,
                        post_tag.replace(" ", "&nbsp;").replace("-", "&#8209;"),
                        slugify(post_tag),
                        1,
                    )
                )
            else:
                next(tag for tag in post_tags if tag.name == post_tag).count += 1
    keyfun = lambda tag: tag.name.upper()
    post_tags.sort(key=keyfun, reverse=False)
    return post_tags


# allow user to choose between downloading all metadata, downloading only n pages of metadata,
# downloading all media, or generating all pages
def main():
    cookies_pickle_filename = "cookies.pickle"
    posts_pickle_filename = "posts.pickle"
    access_token = os.getenv("PATREON_ACCESS_TOKEN")

    if "--download-posts" in sys.argv:
        download_posts(cookies_pickle_filename, posts_pickle_filename, access_token)

    if "--download-media" in sys.argv:
        download_media(posts_pickle_filename)

    if "--process-media" in sys.argv:
        process_media()

    if "--generate-site" in sys.argv:
        generate_site(posts_pickle_filename)


if __name__ == "__main__":
    main()
