#!/usr/bin/python
import sys
import time
from selenium.webdriver import Firefox
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from fake_useragent import UserAgent


def main():
    token_filename = "patreon_token.txt"
    profile_path = "profile"
    url = "https://www.patreon.com/portal/registration/register-clients"
    useragent = UserAgent()
    profile = FirefoxProfile(profile_path)
    profile.set_preference("general.useragent.override", useragent.random)
    driver = Firefox(firefox_profile=profile)
    driver.get(url)
    token = get_new_token(driver)
    driver.close()
    with open(token_filename, "w") as f:
        f.write(token)


def get_new_token(driver):
    expand_button_xpath = "(//div[contains(concat(' ', normalize-space(@class), ' '), ' sc-gKclnd iYVejI ')])[3]"
    refresh_button_xpath = "(//div[contains(concat(' ', normalize-space(@class), ' '), ' sc-cxpSdN fGpiTY ')])[2]"
    token_xpath = "(//span[contains(concat(' ', normalize-space(@class), ' '), ' sc-iqseJM IXZtX ')])[17]"
    time.sleep(3)
    try:
        click_button(driver, expand_button_xpath)
    except NoSuchElementException:
        print("Error: could not expand API client box")
        sys.exit(1)
    time.sleep(3)
    try:
        click_button(driver, refresh_button_xpath)
    except NoSuchElementException:
        print("Error: could not refresh token")
        sys.exit(2)
    time.sleep(3)
    try:
        token = driver.find_element(by=By.XPATH, value=token_xpath).text
    except:
        print("Error: could not find new token")
        sys.exit(3)
    return token


def scroll_to_element(driver, object):
    coords = object.location_once_scrolled_into_view
    x = object.location["x"]
    y = object.location["y"]
    scroll_by_coord = "window.scrollTo(%s,%s);" % (x, y)
    scroll_nav_out_of_way = "window.scrollBy(0, -120);"
    driver.execute_script(scroll_by_coord)
    driver.execute_script(scroll_nav_out_of_way)


def click_button(driver, button_xpath):
    button = driver.find_element(by=By.XPATH, value=button_xpath)
    scroll_to_element(driver, button)
    actions = ActionChains(driver)
    actions.move_to_element(button)
    actions.click()
    actions.perform()


if __name__ == "__main__":
    main()
