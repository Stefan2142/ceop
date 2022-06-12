#!/usr/bin/python
# -*- encoding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

def get_element(node):
    # for XPATH we have to count only for nodes with same type!
    length = len(list(node.previous_siblings)) + 1
    if (length) > 1:
        return "%s" % (node.name)
    else:
        return node.name


def get_css_path(node):
    path = [get_element(node)]
    for parent in node.parents:
        if parent.name == "html":
            break
        path.insert(0, get_element(parent))
    return " > ".join(path)


def get_driver():
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "download.prompt_for_download": False,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.default_content_setting_values.geolocation": 2,
    }

    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--window-size=1536,865")

    driver = webdriver.Chrome(
        desired_capabilities=caps,
        executable_path="./chromedriver.exe", # @TODO make logic to use .exe for windows, no .exe for others
        chrome_options=chrome_options
    )
    return driver
