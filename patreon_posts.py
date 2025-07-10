#!/usr/bin/env python3
import argparse
import json
import os
import pickle
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import ffmpeg
import jinja2
import patreon
import requests
from PIL import Image, UnidentifiedImageError
from yt_dlp import YoutubeDL


@dataclass
class Tag:
    name: str
    nb_name: str = field(init=False)
    slug: str = field(init=False)
    count: int = 0

    def __post_init__(self):
        self.nb_name = self.name.replace(" ", "\u00a0").replace("-", "\u2011")
        self.slug = slugify(self.name)


def download_posts(
    cookies_pickle_filename: str, posts_pickle_filename: str, access_token: str
):
    print("Downloading new posts...", flush=True)

    try:
        with open(cookies_pickle_filename, "rb") as f:
            cookies = pickle.load(f)
    except FileNotFoundError:
        print(f"Error: {cookies_pickle_filename} not found.")
        return

    api_client = patreon.API(access_token)
    try:
        print("Fetching campaign ID from Patreon...", flush=True)
        campaign_id = api_client.get_campaigns(1).data()[0].id()
    except (AttributeError, IndexError):
        print("Error: Invalid ACCESS_TOKEN. Please update it.")
        return

    posts_data = []
    cursor = None
    while True:
        posts_url = f"https://www.patreon.com/api/oauth2/v2/campaigns/{campaign_id}/posts?page[size]=1000"
        if cursor:
            posts_url += f"&page[cursor]={cursor}"

        try:
            print(f"Fetching new posts from Patreon at {posts_url}...", flush=True)
            response = requests.get(
                posts_url, headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            data = response.json()
            posts_data.extend(data["data"])
            cursor = (
                data.get("meta", {})
                .get("pagination", {})
                .get("cursors", {})
                .get("next")
            )
            if not cursor:
                break
        except requests.RequestException as e:
            print(f"Error fetching posts: {e}")
            break
        except json.JSONDecodeError:
            print("Error decoding JSON from posts API.")
            break

    print("Fetching new posts completed.", flush=True)

    processed_posts = []
    for post_data in posts_data:
        post_url = f"https://www.patreon.com/api/posts/{post_data['id']}"
        try:
            post_response = requests.get(
                post_url,
                cookies=cookies,
                headers={
                    "User-Agent": "Patreon-Python, version 0.5.0, platform Linux-5.4.170+-x86_64-with-glibc2.29"
                },
            )
            post_response.raise_for_status()
            post_json = post_response.json()

            attributes = post_json["data"]["attributes"]
            post_slug = slugify(attributes["title"])
            print(f"Processing post: {post_slug}...", flush=True)
            attributes["title_slug"] = post_slug
            attributes["icon_type"] = determine_icon_type(post_json)
            processed_posts.append(post_json)

        except requests.RequestException as e:
            print(f"Error fetching post {post_url}: {e}")
        except json.JSONDecodeError:
            print(f"Failed to load JSON from post: {post_url}")

    with open(posts_pickle_filename, "wb") as f:
        pickle.dump(processed_posts, f)

    print("Downloading new posts completed.", flush=True)


def download_media(posts_pickle_filename: str):
    print("Downloading new media...", flush=True)

    posts = load_posts(posts_pickle_filename)
    if not posts:
        return

    for post in posts:
        attrs = post["data"]["attributes"]
        post_slug = attrs["title_slug"]
        post_tags = get_post_tags(post)
        icon_type = attrs["icon_type"]
        print(f"Downloading {icon_type} media for {post_slug}...")

        if (
            icon_type in ("video", "speedvideo")
            and "Premium video post" not in post_tags
        ):
            download_video_media(post, post_slug, icon_type)
        elif icon_type in ("image", "gif", "link") or "Premium video post" in post_tags:
            download_image_media(post, post_slug, icon_type)

    print("Downloading new media completed.", flush=True)


def process_media():
    print("Processing new media...", flush=True)
    process_images()
    process_gifs()
    process_videos()
    print("Processing new media completed.", flush=True)


def generate_site(posts_pickle_filename: str):
    print("Generating pages...", flush=True)

    posts = load_posts(posts_pickle_filename)
    if not posts:
        return

    # Client-chosen tags for various categories
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

    # Page definitions
    pages = {
        "ALL": {},
        "ALL VOS EPISODE": {"with_tags": vos, "sort": "ordinal"},
        "VOS PAINT-ALONG": {"with_tags": vos + paint_along, "sort": "ordinal"},
        "VOS ANIMAL": {"with_tags": vos + animal, "sort": "ordinal"},
        "VOS PORTRAIT": {"with_tags": vos + portrait, "sort": "ordinal"},
        "VOS LANDSCAPE": {"with_tags": vos + landscape, "sort": "ordinal"},
        "VOS PASTELING": {"with_tags": vos + pasteling, "sort": "ordinal"},
        "VOS UNDERPAINTING": {"with_tags": vos + underpainting, "sort": "ordinal"},
        "OTHER VOS EPISODE": {
            "with_tags": vos,
            "without_tags": paint_along
            + animal
            + portrait
            + landscape
            + pasteling
            + underpainting,
            "sort": "ordinal",
        },
        "OTHER PREMIUM": {"with_tags": premium, "without_tags": vos},
        "ALL PUBLIC": {"without_tags": premium},
        "ART TIP": {"with_tags": art_tip, "without_tags": premium},
        "BONUS FULL-LENGTH VIDEO": {
            "with_tags": bonus_full_length_videos,
            "without_tags": premium,
        },
        "CONVERSATION": {"with_tags": conversation, "without_tags": premium},
        "INSPIRATION": {"with_tags": inspiration, "without_tags": premium},
        "PROBLEM SOLVING": {"with_tags": problem_solving, "without_tags": premium},
        "PROGRESS PIC": {"with_tags": progress_pic, "without_tags": premium},
        "SPEED VIDEO": {"with_tags": speed_video, "without_tags": premium},
        "VIDEO MONTAGE": {"with_tags": video_montage, "without_tags": premium},
        "COLOR PALETTE": {"with_tags": color_palette, "without_tags": premium},
        "OTHER PUBLIC": {
            "without_tags": premium
            + progress_pic
            + speed_video
            + video_montage
            + color_palette
            + art_tip
            + conversation
            + inspiration
            + problem_solving
            + bonus_full_length_videos
        },
        "BIRD": {"with_tags": bird, "without_tags": no_subject},
        "BUNNY": {"with_tags": bunny, "without_tags": no_subject},
        "COW": {"with_tags": cow, "without_tags": no_subject},
        "DONKEY": {"with_tags": donkey, "without_tags": no_subject},
        "ALL DRAWING": {"with_tags": drawing, "without_tags": no_subject},
        "CARICATURE": {"with_tags": caricature, "without_tags": no_subject},
        "LANDSCAPE DRAWING": {
            "with_tags": drawing + landscape,
            "without_tags": no_subject,
        },
        "ANIMAL DRAWING": {"with_tags": drawing + animal, "without_tags": no_subject},
        "HUMAN DRAWING": {"with_tags": drawing + portrait, "without_tags": no_subject},
        "OTHER DRAWING": {
            "with_tags": drawing,
            "without_tags": caricature + landscape + animal + portrait + no_subject,
        },
        "GOAT": {"with_tags": goat, "without_tags": no_subject},
        "HORSE": {"with_tags": horse, "without_tags": no_subject},
        "LANDSCAPE": {"with_tags": landscape, "without_tags": no_subject},
        "PIG": {"with_tags": pig, "without_tags": no_subject},
        "PET PORTRAIT": {"with_tags": pet_portrait, "without_tags": no_subject},
        "HUMAN PORTRAIT": {"with_tags": portrait, "without_tags": no_subject},
        "SHEEP": {"with_tags": sheep, "without_tags": no_subject},
        "ALL WILDLIFE": {"with_tags": wildlife, "without_tags": no_subject},
        "WILD BIRD": {"with_tags": wildlife + bird, "without_tags": no_subject},
        "BUG": {"with_tags": bug, "without_tags": no_subject},
        "DEER": {"with_tags": deer, "without_tags": no_subject},
        "SQUIRREL": {"with_tags": squirrel, "without_tags": no_subject},
        "OTHER WILDLIFE": {
            "with_tags": wildlife,
            "without_tags": bird + bug + deer + squirrel + no_subject,
        },
        "STILL LIFE": {"with_tags": still_life, "without_tags": no_subject},
        "OTHER SUBJECT": {
            "without_tags": bird
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
            + no_subject
        },
    }

    for name, config in pages.items():
        generate_page(posts, name, **config)

    generate_tag_pages(posts)
    generate_page([], filename="patreon.html", template="patreon.html.j2")

    print("Finished generating pages.", flush=True)


def determine_icon_type(post: Dict[str, Any]) -> str:
    attributes = post["data"]["attributes"]
    post_tags = get_post_tags(post)
    post_type = attributes.get("post_type", "")

    # special case
    if "Premium video post" in post_tags:
        return "video"

    if post_type in ("text_only", "poll"):
        return "text"
    if post_type in ("image_file", "link"):
        image_url = attributes.get("image", {}).get("url", "")
        if image_url and "gif" in requests.head(
            image_url, allow_redirects=True
        ).headers.get("Content-Type", ""):
            return "gif"
        return "link" if post_type == "link" else "image"
    if post_type in ("video_embed", "video_external_file"):
        url = (
            (attributes.get("embed") or {}).get("url")
            or (attributes.get("post_file") or {}).get("url")
            or attributes.get("url")
        )
        if get_vid(url):
            if "speed video" in post_tags and "video montage" not in post_tags:
                return "speedvideo"
            return "video"
        return "image"
    return "unknown"


def download_video_media(post: Dict[str, Any], post_slug: str, icon_type: str):
    attrs = post["data"]["attributes"]
    yt_url = (attrs.get("embed") or {}).get("url") or (
        attrs.get("post_file") or {}
    ).get("url")
    vid = get_vid(yt_url)
    if not vid:
        return

    filename = f"{post_slug}.{'webm' if icon_type == 'speedvideo' else 'jpg'}"
    if Path(filename).exists():
        print(f"Warning: Reusing cached video {filename}...")
        return

    ydl_opts = {
        "retries": 10,
        "ignoreerrors": True,
        "outtmpl": vid,
        "format": format_selector if icon_type == "speedvideo" else None,
        "writethumbnail": icon_type != "speedvideo",
        "skip_download": icon_type != "speedvideo",
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([yt_url])

    for ext in [".mp4", ".webm", ".webp"]:
        if Path(f"{vid}{ext}").exists():
            Path(f"{vid}{ext}").rename(filename)
            break


def download_image_media(post: Dict[str, Any], post_slug: str, icon_type: str):
    image_filename = f"{post_slug}.{icon_type if icon_type == 'gif' else 'jpg'}"
    if Path(image_filename).exists():
        print(f"Warning: Reusing cached image {image_filename}...")
        return

    attrs = post["data"]["attributes"]
    image_url = (attrs.get("post_file") or {}).get("url")

    if not image_url or icon_type == "gif":
        image_url = (attrs.get("image") or {}).get("url")

    if image_url:
        try:
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            with open(image_filename, "wb") as f:
                f.write(image_response.content)
        except requests.RequestException as e:
            print(f"Error: Failed to download image: {image_url}: {e}")


def process_images():
    for image_file in Path.cwd().glob("*.jpg"):
        if "_processed" in image_file.name:
            continue
        dest_file = image_file.with_name(f"{image_file.stem}_processed.jpg")
        if not dest_file.exists():
            try:
                with Image.open(image_file).convert("RGB") as img:
                    img.thumbnail((300, 300))
                    img.save(dest_file, optimize=True, quality=85)
            except UnidentifiedImageError:
                print(f"Error: Image invalid or corrupted: {image_file}")


def process_gifs():
    for gif_file in Path.cwd().glob("*.gif"):
        if "_processed" in gif_file.name:
            continue
        dest_file = gif_file.with_name(f"{gif_file.stem}_processed.webm")
        if not dest_file.exists():
            try:
                ffmpeg.input(str(gif_file)).filter("scale", -1, 300).output(
                    str(dest_file),
                    ss="00:00:02",
                    to="00:00:06",
                    vcodec="libvpx-vp9",
                    pix_fmt="yuv420p",
                    movflags="faststart",
                    crf=35,
                ).overwrite_output().run()
            except ffmpeg.Error as e:
                print(f"Error: GIF invalid or corrupted: {gif_file}")


def process_videos():
    for video_file in Path.cwd().glob("*.webm"):
        if "_processed" in video_file.name:
            continue
        dest_file = video_file.with_name(f"{video_file.stem}_processed.webm")
        if not dest_file.exists():
            try:
                ffmpeg.input(str(video_file)).filter("scale", -1, 300).output(
                    str(dest_file),
                    ss="00:00:06",
                    to="00:00:10",
                    vcodec="libvpx-vp9",
                    movflags="faststart",
                    crf=35,
                ).overwrite_output().run()
            except ffmpeg.Error as e:
                print(f"Error: Video invalid or corrupted: {video_file}")


def generate_page(
    posts: List[Dict],
    filename: str,
    with_tags: Optional[List[str]] = None,
    without_tags: Optional[List[str]] = None,
    sort: str = "temporal",
    template: str = "template.html.j2",
):
    filtered_posts = filter_posts(posts, with_tags, without_tags)
    sorted_posts = sort_posts(filtered_posts, sort)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
    template = env.get_template(template)
    page_content = template.render(
        filename=filename,
        date=date.today(),
        posts=sorted_posts,
    )
    with open(f"{filename}.html", "w") as f:
        f.write(page_content)


def filter_posts(
    posts: List[Dict],
    with_tags: Optional[List[str]] = None,
    without_tags: Optional[List[str]] = None,
) -> List[Dict]:
    if with_tags:
        posts = [p for p in posts if all(t in get_post_tags(p) for t in with_tags)]
    if without_tags:
        posts = [
            p for p in posts if not any(t in get_post_tags(p) for t in without_tags)
        ]
    return posts


def get_post_tags(post: Dict) -> List[str]:
    return [
        tag["id"].split(";", 1)[1]
        for tag in post["data"]["relationships"]["user_defined_tags"]["data"]
    ]


def sort_posts(posts: List[Dict], sort: str) -> List[Dict]:
    if sort == "alphabetical":
        key = lambda p: p["data"]["attributes"]["title"].upper()
        posts.sort(key=key)
    elif sort == "ordinal":
        key = lambda p: (
            int(re.findall(r"\d+", p["data"]["attributes"]["title"])[0])
            if re.findall(r"\d+", p["data"]["attributes"]["title"])
            else 0
        )
        posts.sort(key=key, reverse=True)
    elif sort == "temporal":
        key = lambda p: int(
            re.sub(r"[^0-9]", "", p["data"]["attributes"]["published_at"])
        )
        posts.sort(key=key, reverse=True)
    return posts


# extract youtube video id from a youtube url
def get_vid(url: str) -> str:
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
        return query.path[1:].split(".", 1)[0]
    else:
        return ""


def format_selector(ctx: Dict) -> Dict:
    formats = ctx.get("formats")[::-1]
    best_video = next(
        (
            f
            for f in formats
            if f.get("vcodec") != "none"
            and f.get("acodec") == "none"
            and f.get("height", 0) >= 360
            and f.get("ext") == "mp4"
        ),
        None,
    )
    if best_video:
        yield {
            "format_id": best_video["format_id"],
            "ext": best_video["ext"],
            "requested_formats": [best_video],
            "protocol": best_video["protocol"],
        }


def slugify(value: str, allow_unicode: bool = False) -> str:
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


def generate_tag_pages(posts: List[Dict]):
    tags = extract_tags(posts)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
    template = env.get_template("tags_template.html.j2")
    page_content = template.render(
        filename="TAGS",
        date=date.today(),
        tags=tags,
    )
    with open("TAGS.html", "w") as f:
        f.write(page_content)

    for tag in tags:
        generate_page(posts, tag.slug, with_tags=[tag.name])


def extract_tags(posts: List[Dict]) -> List[Tag]:
    tag_counts = {}
    for post in posts:
        for tag_name in get_post_tags(post):
            tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1

    tags = [Tag(name=name, count=count) for name, count in tag_counts.items()]
    tags.sort(key=lambda t: t.name.upper())
    return tags


def load_posts(posts_pickle_filename: str) -> Optional[List[Dict]]:
    try:
        with open(posts_pickle_filename, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"{posts_pickle_filename} missing! Cannot generate posts.")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Patreon content downloader and site generator."
    )
    parser.add_argument(
        "--download-posts", action="store_true", help="Download all post metadata."
    )
    parser.add_argument(
        "--download-media", action="store_true", help="Download all media."
    )
    parser.add_argument(
        "--process-media", action="store_true", help="Process all downloaded media."
    )
    parser.add_argument(
        "--generate-site", action="store_true", help="Generate the static site."
    )
    args = parser.parse_args()

    cookies_pickle_filename = "cookies.pickle"
    posts_pickle_filename = "posts.pickle"
    access_token = os.getenv("PATREON_ACCESS_TOKEN")

    if not access_token:
        print("Error: PATREON_ACCESS_TOKEN environment variable not set.")
        return

    if args.download_posts:
        download_posts(cookies_pickle_filename, posts_pickle_filename, access_token)
    if args.download_media:
        download_media(posts_pickle_filename)
    if args.process_media:
        process_media()
    if args.generate_site:
        generate_site(posts_pickle_filename)


if __name__ == "__main__":
    main()
