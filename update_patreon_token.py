#!/usr/bin/python
import sys
import time
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from fake_useragent import UserAgent


def main():
    token_filename = "patreon_token.txt"
    profile_path = "profile"
    url = "https://www.patreon.com/portal/registration/register-clients"
    useragent = UserAgent()
    options = Options()
    options.add_argument("-profile")
    options.add_argument(profile_path)
    options.set_preference("general.useragent.override", useragent.random)
    service = Service("/usr/bin/geckodriver")
    driver = Firefox(service=service, options=options)
    driver.get(url)
    token = get_new_token(driver)
    driver.close()
    with open(token_filename, "w") as f:
        f.write(token)


def get_new_token(driver):
    # expand_button_xpath = "(//div[contains(concat(' ', normalize-space(@class), ' '), ' sc-gKclnd iYVejI ')])[3]"
    # refresh_button_xpath = "(//div[contains(concat(' ', normalize-space(@class), ' '), ' sc-iJKOTD qvzkB ')])[2]"
    # token_xpath = "(//span[contains(concat(' ', normalize-space(@class), ' '), ' sc-ieecCq cFhZVW ')])[17]"
    # patreon randomizes their classes, so try absolute xpaths
    expand_button_xpath = "/html/body/div[4]/div/main/div[1]/div[3]/div/div/div[2]/div/div/div[3]/div/div/div/div/div/div[4]/button"
    refresh_button_xpath = "/html/body/div[4]/div/main/div[1]/div[3]/div/div/div[2]/div/div/div[3]/div/div/div/div[2]/div[6]/button"
    token_xpath = "/html/body/div[4]/div/main/div[1]/div[3]/div/div/div[2]/div/div/div[3]/div/div/div/div[2]/div[5]/div[1]/span"
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
