#!/bin/python3
import os
import pickle
import re
import sys
import time
import unicodedata
from datetime import date
from operator import attrgetter
from os.path import exists
from pathlib import Path
from shlex import quote as cmd_quote
from urllib.parse import parse_qs, urlparse

import ffmpeg
import jinja2
import requests
from bs4 import BeautifulSoup
from PIL import Image
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Firefox, FirefoxProfile
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from yt_dlp import YoutubeDL


# post class to store the data necessary to generate post pages
class post:
    title = ""
    slug = ""
    url = ""
    image = ""
    vid = ""
    media_type = ""
    tags = []

    def __init__(self, title, slug, url, image, vid, media_type, tags):
        self.title = title
        self.slug = slug
        self.url = url
        self.image = image
        self.vid = vid
        self.media_type = media_type
        self.tags = tags


# tag class to store the data necessary to generate tag page
class tag:
    name = ""
    nb_name = ""
    count = 0

    def __init__(self, name, nb_name, count):
        self.name = name
        self.nb_name = nb_name
        self.count = count


# allow user to choose between downloading all metadata, downloading only n pages of metadata,
# downloading all media, or generating all pages
def main():
    pickle_filename = "profile.pickle"
    get_posts = "--sync-posts" in sys.argv
    get_media = "--sync-media" in sys.argv
    set_pages = "--sync-pages" in sys.argv
    argv_ints = list(
        map(int, re.findall(r"\d+", " ".join(map(cmd_quote, sys.argv[1:]))))
    )
    page_count = argv_ints[0] if argv_ints else 0

    if get_posts:
        sync_posts(pickle_filename, get_media, page_count)

    if get_media:
        download_media(pickle_filename)

    if set_pages:
        generate_pages(pickle_filename)


# download new data from patreon.com and, if applicable, merge it with existing list of data,
# replacing any old data that conflicts, serialize and save to system
def sync_posts(pickle_filename, get_videos=False, page_count=0):
    source_filename = "profile.txt"
    title_class = "sc-1di2uql-1 wkoTA"
    tag_class = "sc-jrQzAO WqDYW"

    source = download_source(title_class, get_videos, page_count)
    with open(source_filename, "w") as file:
        file.write(source)
    with open(source_filename, "r") as file:
        new_posts = extract_posts(file, title_class, tag_class)
    if exists(pickle_filename) and page_count:
        with open(pickle_filename, "rb") as file:
            posts = pickle.load(file)
        for new_post in new_posts.reverse():
            stored = False
            for post in posts:
                if post.title == new_post.title:
                    post.url = new_post.url
                    post.tags = new_post.tags
                    post.image = new_post.image
                    post.media_type = new_post.media_type
                    if get_videos:
                        post.vid = new_post.vid
                    stored = True
            if not stored:
                posts.insert(0, new_post)
    else:
        print(
            pickle_filename + " missing or no page limit! Replacing with new posts..."
        )
        posts = new_posts
    with open(pickle_filename, "wb") as file:
        pickle.dump(posts, file)


# use selenium geckodriver firefox to automatically scrape patreon.com for the needed data
# this step requires user intervention within 30 seconds to manually complete the captcha that is likely to appear
def download_source(title_class, get_videos, page_count):
    profile_path = "/home/rita/patreon/profile"
    url = "https://www.patreon.com/RitaKirkmanStudio/posts"
    button_xpath = "//div[contains(concat(' ', normalize-space(@class), ' '), ' sc-llYSUQ bmzcNW ') and text()='Load more']"
    video_xpath = "//div[contains(concat(' ', normalize-space(@class), ' '), ' sc-10zv41x-1 VTlAt middle-xs center-xs ')]"
    loader_xpath = "//div[contains(concat(' ', normalize-space(@class), ' '), ' lazyload-placeholder ')]"
    duplicates = False
    current_page = 1

    profile = FirefoxProfile(profile_path)
    driver = Firefox(firefox_profile=profile)
    driver.maximize_window()
    driver.get(url)
    time.sleep(30)

    while not duplicates:
        try:
            load_images = True
            while load_images:
                try:
                    loader = driver.find_element(by=By.XPATH, value=loader_xpath)
                    scroll_to_element(driver, loader)
                except NoSuchElementException:
                    load_images = False
                time.sleep(1)
            if get_videos:
                load_videos = True
                while load_videos:
                    try:
                        click_button(driver, video_xpath)
                    except NoSuchElementException:
                        load_videos = False
                    time.sleep(1)
            click_button(driver, button_xpath)
            time.sleep(15)
            duplicates = check_for_duplicate_posts(driver.page_source, title_class)
        except NoSuchElementException:
            duplicates = True
        if page_count and (current_page == page_count):
            duplicates = True
        else:
            current_page += 1

    source = driver.page_source
    driver.close()
    return source


# use webdriver find element by xpath, scroll to element, move to element, then click element
def click_button(driver, button_xpath):
    button = driver.find_element(by=By.XPATH, value=button_xpath)
    scroll_to_element(driver, button)
    actions = ActionChains(driver)
    actions.move_to_element(button)
    actions.click()
    actions.perform()


# scroll webdriver to element
def scroll_to_element(driver, object):
    x = object.location["x"]
    y = object.location["y"]
    scroll_by_coord = "window.scrollTo(%s,%s);" % (x, y)
    scroll_nav_out_of_way = "window.scrollBy(0, -120);"
    driver.execute_script(scroll_by_coord)
    driver.execute_script(scroll_nav_out_of_way)


# use bs4 on a page source to check whether it contains duplicate posts
def check_for_duplicate_posts(source, title_class):
    soup = BeautifulSoup(source, features="lxml")
    titles = []
    for title in soup.findAll("span", attrs={"class": title_class}):
        titles.append(title.find("a").contents[0])
    for title in titles:
        if titles.count(title) > 1:
            return True
    return False


# use bs4 on a sufficiently populated patreon posts page source to pick the data out of it
# and manipulate it into a list of post objects
def extract_posts(source, title_class, tag_class):
    posts = []
    soup = BeautifulSoup(source, features="lxml")
    for title_iterator in soup.findAll("span", attrs={"class": title_class}):
        title = str(title_iterator.find("a").contents[0])
        url = str(title_iterator.find("a")["href"])
        image = ""
        vid = ""
        media_type = "text"
        tags = []
        if title not in (post.title for post in posts):
            for tag in title_iterator.parent.parent.parent.findAll(
                "div", attrs={"class": tag_class}
            ):
                if tag.find("p"):
                    tags.append(str(tag.find("p").contents[0]))
            video_iframe = title_iterator.parent.parent.parent.parent.find("iframe")
            image_img = title_iterator.parent.parent.parent.parent.find("img")
            if image_img:
                image = str(image_img["src"])
                if "gif" in str(
                    requests.head(image, allow_redirects=True).headers["Content-Type"]
                ):
                    media_type = "gif"
                else:
                    media_type = "image"
            if video_iframe:
                vid = str(get_vid(video_iframe["src"]))
                media_type = "video"
            if vid and "Premium video post" in tags:
                media_type = "image"
            if media_type == "video" and not vid:
                media_type = "unknown"
            posts.append(post(title, slugify(title), url, image, vid, media_type, tags))
    return posts


# extract youtube video id from a youtube url
def get_vid(url):
    """Returns Video_ID extracting from the given url of Youtube

    Examples of URLs:
      Valid:
        'http://youtu.be/_lOT2p_FCvA',
        'www.youtube.com/watch?v=_lOT2p_FCvA&feature=feedu',
        'http://www.youtube.com/embed/_lOT2p_FCvA',
        'http://www.youtube.com/v/_lOT2p_FCvA?version=3&amp;hl=en_US',
        'https://www.youtube.com/watch?v=rTHlyTphWP0&index=6&list=PLjeDyYvG6-40qawYNR4juzvSOg-ezZ2a6',
        'youtube.com/watch?v=_lOT2p_FCvA',

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
    else:
        return ""


# use yt-dlp, ffmpeg and pillow to download all non-GIF media referenced by the collected metadata
# and process it by scaling and trimming as desired
def download_media(pickle_filename):
    if exists(pickle_filename):
        with open(pickle_filename, "rb") as file:
            posts = pickle.load(file)
        for post in posts:
            print("post.vid: " + post.vid)
            print("post.media_type: " + post.media_type)
            if post.vid:
                if post.media_type == "video":
                    ydl_opts = {
                        "retries": 100,
                        "ignoreerrors": True,
                        "outtmpl": "%(id)s",
                        "format": format_selector,
                    }
                    yt_url = ["https://www.youtube.com/watch?v=" + post.vid]
                    with YoutubeDL(ydl_opts) as ydl:
                        ydl.download(yt_url)
                    filename = post.slug + ".webm"
                    os.rename(post.vid + ".webm", filename)
                else:
                    ydl_opts = {
                        "retries": 100,
                        "ignoreerrors": True,
                        "writethumbnail": True,
                        "skip_download": True,
                        "outtmpl": "%(id)s",
                        "format": format_selector,
                    }
                    yt_url = ["https://www.youtube.com/watch?v=" + post.vid]
                    with YoutubeDL(ydl_opts) as ydl:
                        ydl.download(yt_url)
                    filename = post.slug + ".jpg"
                    os.rename(post.vid + ".webp", filename)
            elif post.media_type == "image":
                image = requests.get(post.image)
                with open(post.slug + ".jpg", "wb") as f:
                    f.write(image.content)
        images = [file for file in os.listdir() if file.endswith(("jpg"))]
        for image in images:
            img = Image.open(image).convert("RGB")
            img.thumbnail((300, 300))
            img.save(image, optimize=True, quality=85)
        videos = [file for file in os.listdir() if file.endswith(("webm"))]
        for video in videos:
            ffmpeg.input(video).output(
                video + ".webm",
                ss=("00:00:06"),
                to=("00:00:10"),
                vcodec="libvpx-vp9",
                crf=25,
            ).run()
        for path in Path(".").glob("*.webm.webm"):
            path.rename(path.with_name(path.stem.partition(".webm")[0] + path.suffix))

    else:
        print(pickle_filename + " missing! Cannot download media.")


# choose only vp9 webms at least 240p for yt-dlp format selection
def format_selector(ctx):
    """Select the best video and the best audio that won't result in an mkv.
    NOTE: This is just an example and does not handle all cases"""

    # formats are already sorted worst to best
    formats = ctx.get("formats")[::-1]

    # first strictly vp9 webm without audio that is at least 240p
    best_video = next(
        f
        for f in formats
        if f["vcodec"] == "vp9"
        and f["acodec"] == "none"
        and f["height"] >= 240
        and f["ext"] == "webm"
    )

    # find compatible audio extension
    audio_ext = {"webm": "webm"}[best_video["ext"]]
    # vcodec='none' means there is no video
    best_audio = next(
        f
        for f in formats
        if (f["acodec"] != "none" and f["vcodec"] == "none" and f["ext"] == audio_ext)
    )

    # These are the minimum required fields for a merged format
    yield {
        "format_id": f'{best_video["format_id"]}+{best_audio["format_id"]}',
        "ext": best_video["ext"],
        "requested_formats": [best_video, best_audio],
        # Must be + separated list of protocols
        "protocol": f'{best_video["protocol"]}+{best_audio["protocol"]}',
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


# generate all pages for the index in a modular way that can be rapidly prototyped
# to demo for the client
def generate_pages(pickle_filename):
    vos_sort = "ordinal"
    # tags chosen by the client for a series of manually-chosen categories
    premium = ["Premium video post"]
    vos = ["VOS day"]
    paint_alongs = ["Paint-Along"]
    animals = ["animals"]
    portraits = ["portrait"]
    landscapes = ["landscape"]
    pasteling = ["pastel"]
    underpainting = ["underpainting"]
    progress_pics = ["progress pics"]
    speed_videos = ["speed video"]
    video_montages = ["video montage"]
    art_tips = ["art tips"]
    conversation = ["conversation"]
    problem_solving = ["problem solving"]
    bonus_full_length_videos = ["Free Full-Length Videos"]
    cow = ["cows"]
    sheep = ["sheep"]
    bird = ["bird"]
    wildlife = ["wildlife"]
    pet_portrait = ["pet portrait"]

    # deserialize the previously-stored list of posts from pickle file
    if exists(pickle_filename):
        with open(pickle_filename, "rb") as file:
            posts = pickle.load(file)
    else:
        print(pickle_filename + " missing! Cannot generate posts.")
        return

    # generate all the pages needed for the index site
    generate_page(posts, "ALL")

    generate_page(posts, "ALL VOS EPISODE", premium + vos, sort=vos_sort)
    generate_page(posts, "VOS PAINT-ALONG", premium + vos + paint_alongs, sort=vos_sort)
    generate_page(posts, "VOS ANIMAL", premium + vos + animals, sort=vos_sort)
    generate_page(posts, "VOS PORTRAIT", premium + vos + portraits, sort=vos_sort)
    generate_page(posts, "VOS LANDSCAPE", premium + vos + landscapes, sort=vos_sort)
    generate_page(posts, "VOS PASTELING", premium + vos + pasteling, sort=vos_sort)
    generate_page(
        posts, "VOS UNDERPAINTING", premium + vos + underpainting, sort=vos_sort
    )
    generate_page(
        posts,
        "OTHER VOS EPISODE",
        premium + vos,
        paint_alongs + animals + portraits + landscapes + pasteling + underpainting,
        vos_sort,
    )
    generate_page(posts, "OTHER PREMIUM", premium, vos)

    generate_page(posts, "ALL PUBLIC", without_tags=premium)

    generate_page(posts, "PROGRESS PIC", progress_pics, premium)
    generate_page(posts, "SPEED VIDEO", speed_videos, premium)
    generate_page(posts, "VIDEO MONTAGE", video_montages, premium)
    generate_page(posts, "ART TIP", art_tips, premium)
    generate_page(posts, "CONVERSATION", conversation, premium)
    generate_page(posts, "PROBLEM SOLVING", problem_solving, premium)
    generate_page(posts, "BONUS FULL-LENGTH VIDEO", bonus_full_length_videos, premium)
    generate_page(
        posts,
        "OTHER PUBLIC",
        without_tags=premium
        + progress_pics
        + speed_videos
        + video_montages
        + art_tips
        + conversation
        + problem_solving
        + bonus_full_length_videos,
    )

    generate_page(posts, "PORTRAIT", portraits)
    generate_page(posts, "COW", cow)
    generate_page(posts, "SHEEP", sheep)
    generate_page(posts, "BIRD", bird)
    generate_page(posts, "WILDLIFE", wildlife)
    generate_page(posts, "PET PORTRAIT", pet_portrait)
    generate_page(
        posts,
        "OTHER",
        without_tags=portraits + cow + sheep + bird + wildlife + pet_portrait,
    )

    generate_tag_pages(posts)


# filter by tags and sort the posts, then use jinja2 to populate the page with data and write
# it to a new file
def generate_page(posts, filename, with_tags=[], without_tags=[], sort="none"):
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


# derive a list of all tags from the list of posts, then iterate it to generate a tag homepage
# and pages of posts sorted by tags
def generate_tag_pages(posts):
    filename = "TAGS"
    tags = extract_tags(posts)
    current_date = date.today()
    page = (
        jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
        .get_template("tags_template.html.j2")
        .render(filename=filename, date=current_date, tags=tags)
    )
    with open(filename + ".html", "w") as f:
        f.write(page)
    for tag in tags:
        generate_page(posts, tag.name, [tag.name])


# count the occurrences of posts associated with each possible tag, store the data in a list of tags,
# and generate a non-breaking title for the tag to display nicely on the tags page
def extract_tags(posts):
    tags = []
    for post in posts:
        for post_tag in post.tags:
            if post_tag not in (tag.name for tag in tags):
                tags.append(
                    tag(
                        post_tag,
                        post_tag.replace(" ", "&nbsp;").replace("-", "&#8209;"),
                        1,
                    )
                )
            else:
                next(tag for tag in tags if tag.name == post_tag).count += 1
    keyfun = lambda tag: tag.name.upper()
    tags.sort(key=keyfun, reverse=False)
    return tags


# filter the list of posts by tags inclusively and exclusively
def filter_posts(posts, with_tags, without_tags):
    if with_tags:
        posts = [post for post in posts if include_tags(post, with_tags)]
    if without_tags:
        posts = [post for post in posts if exclude_tags(post, without_tags)]
    return posts


# keep only posts containing all given tags
def include_tags(post, tags):
    keep = True
    for tag in tags:
        if tag not in post.tags:
            keep = False
    return keep


# keep only posts containing none of the given tags
def exclude_tags(post, tags):
    keep = True
    for tag in tags:
        if tag in post.tags:
            keep = False
    return keep


# sort posts alphabetically case-insensitive, ordinally by the first number detected,
# or do not sort posts at all
def sort_posts(posts, sort):
    match sort:
        case "alphabetical":
            keyfun = lambda post: post.title.upper()
            posts.sort(key=keyfun, reverse=True)
        case "ordinal":
            keyfun = (
                lambda post: list(map(int, re.findall(r"\d+", post.title)))[0]
                if list(map(int, re.findall(r"\d+", post.title)))
                else 0
            )
            posts.sort(key=keyfun, reverse=True)
        case _:
            pass
    return posts


if __name__ == "__main__":
    main()
