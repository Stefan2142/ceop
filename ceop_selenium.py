import os, time
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path


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
        executable_path="./chromedriver.exe", chrome_options=chrome_options
    )
    return driver


def main():
    Path('./Data').mkdir(parents=True, exist_ok=True)
    
    driver = get_driver()
    driver.get("https://ceop.apr.gov.rs/ceopweb/sr-cyrl/home")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="query"]'))
    )
    query_el = driver.find_element(by=By.XPATH, value='//*[@id="query"]')
    # Insert search query
    query_el.send_keys("ROP-BGDU-29")

    # Click on search
    query_el.send_keys(Keys.ENTER)

    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.CLASS_NAME, "table--mobile.table--rowHover.t1")
        )
    )
    # Get nbr of pages
    soup = BeautifulSoup(driver.page_source, "html.parser")
    nbr_of_pages = int(
        soup.find("li", {"class": "ellipsis"})
        .next_sibling.text.split("page")[-1]
        .strip()
    )

    main_table = soup.find("table", {"class": "table--mobile table--rowHover t1"})
    main_rows = main_table.find_all("tr")

    # First two are part of table header
    for row in main_rows[2:]:

        # Broj predmeta (eg: ROP-BGDU-2944-LOC-3/2022')
        row_id = row.td.span.text.replace("/", "-")

        # Get css selector of a current row and use it for 'click' event
        css_selector = get_css_path(row) + f":nth-child({main_rows.index(row)})"
        driver.find_element(by=By.CSS_SELECTOR, value=css_selector).click()

        # Wait to load (TO DO: implement Wait)
        time.sleep(1)

        # Resulting table of a clicked row
        inner_table_el = driver.find_element(
            by=By.CLASS_NAME, value="table--mobile.table--rowHover.t1.tree"
        )

        # Convert it to html to load it iinto pandas
        parent_table_el = inner_table_el.find_element(by = By.XPATH, value="..")
        parent_table_el_html = parent_table_el.get_attribute("innerHTML")

        # pd.read_html will convert parent_table_el_html
        # into two dfs, we need first one
        html_df = pd.read_html(parent_table_el_html)[0]
        html_df.to_csv(f"./Data/{row_id}.csv", index=False, encoding="utf8")

    # Used for pagination
    next_page_el = driver.find_element(By.XPATH, value="//a[@aria-label='Next page']")

    # Non visible on first page
    # previous_page_el = driver.find_element(By.XPATH, value="//a[@aria-label='Previous page']")

    raise ("End")


if __name__ == "__main__":
    main()
