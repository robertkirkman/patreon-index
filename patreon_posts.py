#!/bin/python3
import sys
import time
import jinja2
from datetime import date
from selenium.webdriver import Firefox
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup


class post:
    title = ""
    url = ""
    tags = []

    def __init__(self, title, url, tags):
        self.title = title
        self.url = url
        self.tags = tags


def scroll_to_element(driver, object):
    x = object.location["x"]
    y = object.location["y"]
    scroll_by_coord = "window.scrollTo(%s,%s);" % (x, y)
    scroll_nav_out_of_way = "window.scrollBy(0, -120);"
    driver.execute_script(scroll_by_coord)
    driver.execute_script(scroll_nav_out_of_way)


def click_button(driver, button_xpath):
    button = driver.find_element(by=By.XPATH, value=button_xpath)
    scroll_to_element(driver, button)
    time.sleep(2)
    scroll_to_element(driver, button)
    actions = ActionChains(driver)
    actions.move_to_element(button)
    actions.click()
    actions.perform()


def check_for_duplicate_posts(source, title_class):
    soup = BeautifulSoup(source, features="lxml")
    titles = []
    for title in soup.findAll("span", attrs={"class": title_class}):
        titles.append(title.find("a").contents[0])
    for title in titles:
        if titles.count(title) > 1:
            return True
    return False


def filter_tags(post, tags):
    for tag in tags:
        if tag in post.tags:
            return True
    return False


def filter_posts(posts, with_tags, without_tags):
    if with_tags:
        posts = [post for post in posts if filter_tags(post, with_tags)]
    if without_tags:
        posts = [post for post in posts if not filter_tags(post, without_tags)]
    return posts


def extract_posts(source, title_class, tag_class):
    posts = []
    soup = BeautifulSoup(source, features="lxml")
    for title_iterator in soup.findAll("span", attrs={"class": title_class}):
        title = title_iterator.find("a").contents[0]
        url = title_iterator.find("a")["href"]
        tags = []
        if title not in (post.title for post in posts) and "checkout" not in url:
            for tag in title_iterator.parent.parent.parent.findAll(
                "div", attrs={"class": tag_class}
            ):
                if tag.find("p"):
                    tags.append(tag.find("p").contents[0])
            posts.append(post(title, url, tags))
    return posts


def generate_page(posts, filename, with_tags=[], without_tags=[]):
    posts = filter_posts(posts, with_tags, without_tags)
    current_date = date.today()
    page = (
        jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
        .get_template("template.html")
        .render(filename=filename, date=current_date, posts=posts)
    )
    with open(filename + ".html", "w") as f:
        f.write(page)


def download_source(profile_path, title_class, captcha_xpath, button_xpath, url):
    profile = FirefoxProfile(profile_path)
    driver = Firefox(firefox_profile=profile)
    driver.maximize_window()
    driver.get(url)
    time.sleep(30)
    duplicates = False
    while not duplicates:
        try:
            click_button(driver, button_xpath)
            time.sleep(15)
            duplicates = check_for_duplicate_posts(driver.page_source, title_class)
        except NoSuchElementException:
            duplicates = True
    source = driver.page_source
    driver.close()
    return source


def check_for_captcha(driver, captcha_xpath):
    captcha = True
    try:
        driver.switch_to.frame(driver.find_element(by=By.TAG_NAME, value="iframe"))
        driver.find_element(by=By.XPATH, value=captcha_xpath)
    except NoSuchElementException:
        captcha = False
    driver.switch_to.parent_frame()
    if captcha:
        print("captcha detected")
        time.sleep(20)


def main():
    all_profile_path = "/home/rita/patreon/profile"
    public_profile_path = "/home/rita/patreon/profile-alt"
    url = "https://www.patreon.com/RitaKirkmanStudio/posts"
    title_class = "sc-1di2uql-1 wkoTA"
    tag_class = "sc-jrQzAO WqDYW"
    captcha_xpath = '//div[contains(., "robot")]'
    button_xpath = "//div[contains(concat(' ', normalize-space(@class), ' '), ' sc-llYSUQ bmzcNW ') and text()='Load more']"
    vos_with_tags = [
        "VOS day",
    ]
    vos_underpaintings_with_tags = [
        "VOS day",
        "underpainting",
    ]
    vos_pasteling_with_tags = [
        "VOS day",
        "pastel",
    ]
    vos_portraits_with_tags = [
        "VOS day",
        "portrait",
    ]
    vos_animals_with_tags = [
        "VOS day",
        "animals",
    ]
    vos_other_without_tags = [
        "underpainting",
        "pastel",
        "portrait",
        "animals",
    ]
    public_conversations_with_tags = [
        "conversation",
    ]
    public_speed_demos_with_tags = [
        "speed video",
    ]
    public_progress_pics_with_tags = [
        "progress pics",
    ]
    portraits_with_tags = [
        "portrait",
    ]
    cow_with_tags = [
        "cows",
    ]
    sheep_with_tags = [
        "sheep",
    ]
    bird_with_tags = [
        "bird",
    ]
    wildlife_with_tags = [
        "wildlife",
    ]
    pet_portraits_with_tags = [
        "pet portrait",
    ]
    other_without_tags = [
        "portrait",
        "cows",
        "sheep",
        "bird",
        "wildlife",
        "pet portrait",
    ]

    if len(sys.argv) > 1:
        if sys.argv[1] == "--download":
            all_source = download_source(
                all_profile_path, title_class, captcha_xpath, button_xpath, url
            )
            public_source = download_source(
                public_profile_path, title_class, captcha_xpath, button_xpath, url
            )
            with open("all_source.html", "w") as source:
                source.write(all_source)
            with open("public_source.html", "w") as source:
                source.write(public_source)

    with open("all_source.html", "r") as source:
        all_posts = extract_posts(source, title_class, tag_class)

    with open("public_source.html", "r") as source:
        public_posts = extract_posts(source, title_class, tag_class)

    generate_page(all_posts, "ALL")

    generate_page(all_posts, "ALL VOS", vos_with_tags)
    generate_page(all_posts, "VOS UNDERPAINTING", vos_underpaintings_with_tags)
    generate_page(all_posts, "VOS PASTELING", vos_pasteling_with_tags)
    generate_page(all_posts, "VOS PORTRAIT", vos_portraits_with_tags)
    generate_page(all_posts, "VOS ANIMAL", vos_animals_with_tags)
    generate_page(all_posts, "OTHER VOS", vos_with_tags, vos_other_without_tags)

    generate_page(public_posts, "ALL PUBLIC")

    generate_page(
        public_posts, "ALL PUBLIC CONVERSATION", public_conversations_with_tags
    )
    generate_page(public_posts, "ALL PUBLIC SPEED DEMO", public_speed_demos_with_tags)
    generate_page(
        public_posts, "ALL PUBLIC PROGRESS PIC", public_progress_pics_with_tags
    )

    generate_page(all_posts, "PORTRAIT", portraits_with_tags)
    generate_page(all_posts, "COW", cow_with_tags)
    generate_page(all_posts, "SHEEP", sheep_with_tags)
    generate_page(all_posts, "BIRD", bird_with_tags)
    generate_page(all_posts, "WILDLIFE", wildlife_with_tags)
    generate_page(all_posts, "PET PORTRAIT", pet_portraits_with_tags)
    generate_page(all_posts, "OTHER", without_tags=other_without_tags)


if __name__ == "__main__":
    main()
