#!/usr/bin/python
# -*- encoding: utf-8 -*-
import os, time
import traceback
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import json
from utils_selenium import *


def main():
    Path("./Data").mkdir(parents=True, exist_ok=True)

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

    def get_resp(api_endpoint):
        logs_raw = driver.get_log("performance")
        logs = [json.loads(lr["message"])["message"] for lr in logs_raw]
        logs = [x for x in logs if "response" in x["params"]]
        logs = [
            x
            for x in logs
            if x["method"] == "Network.responseReceived"
            and "json" in x["params"]["response"]["mimeType"]
        ]
        logs = [x for x in logs if api_endpoint in x["params"]["response"]["url"]]

        log = list(logs)[0]
        request_id = log["params"]["requestId"]
        resp_url = log["params"]["response"]["url"]
        print(f"Caught {resp_url}")
        resp_json = json.loads(
            driver.execute_cdp_cmd(
                "Network.getResponseBody", {"requestId": request_id}
            )["body"]
        )
        return resp_json

    soup = BeautifulSoup(driver.page_source, "html.parser")
    nbr_of_pages = int(
        soup.find("li", {"class": "ellipsis"})
        .next_sibling.text.split("page")[-1]
        .strip()
    )
    for page in range(0, 3):
        response_json = get_resp("searchString")
        df = pd.DataFrame(response_json["ResultList"])

        # Predmeti
        for submission_id in response_json["ResultList"]:
            row_id = response_json["ResultList"].index(submission_id)
            print(f"Clicked on row {row_id}")

            driver.find_element(
                by=By.CSS_SELECTOR,
                value=f"body > rd-app > div > rd-home > div > rd-search > div > div > div > table > tbody > tr:nth-child({row_id+2})",
            ).click()

            # Wait to load (TO DO: implement Wait)
            time.sleep(3)

            # Lista predmeta u dosijeu
            submission_resp = get_resp("getAllCaseDetails")
            print(
                f"Found: {len(submission_resp)} cases for {submission_id['SubmissionId']}"
            )
            df_inner = pd.DataFrame(submission_resp)
            df_inner.rename(columns={"SubmissionId": "InnerSubmissionId"}, inplace=True)
            df_inner["SubmissionId"] = submission_id["SubmissionId"]
            merged_df = pd.merge(df, df_inner, how="outer", on="SubmissionId")
            merged_df.sort_values(by="SubmissionId", inplace=True, ascending=False)
            merged_df.dropna(subset=["InnerSubmissionId"], inplace=True)
            merged_df.to_csv(
                "./Data/Data.csv",
                index=False,
                mode="a",
                header=not os.path.exists("./Data/Data.csv"),
            )
        driver.find_element(By.XPATH, value="//a[@aria-label='Next page']").click()
        # Wait to load (TO DO: implement Wait)
        time.sleep(2)

        # Javno dostupni podaci o izabranom predmetu, api endpoint:
        # get_resp("getAllDataDetails")

    # quit all tabs! (to quit one tab use driver.close())
    driver.quit()

    # # Get nbr of pages
    # soup = BeautifulSoup(driver.page_source, "html.parser")
    # nbr_of_pages = int(
    #     soup.find("li", {"class": "ellipsis"})
    #     .next_sibling.text.split("page")[-1]
    #     .strip()
    # )

    # main_table = soup.find("table", {"class": "table--mobile table--rowHover t1"})
    # main_rows = main_table.find_all("tr")

    # # First two are part of table header
    # for row in main_rows[2:]:

    #     # Broj predmeta (eg: ROP-BGDU-2944-LOC-3/2022')
    #     row_id = row.td.span.text.replace("/", "-")

    #     # Get css selector of a current row and use it for 'click' event
    #     css_selector = get_css_path(row) + f":nth-child({main_rows.index(row)})"
    #     driver.find_element(by=By.CSS_SELECTOR, value=css_selector).click()

    #     # Wait to load (TO DO: implement Wait)
    #     time.sleep(1)

    #     # Resulting table of a clicked row
    #     inner_table_el = driver.find_element(
    #         by=By.CLASS_NAME, value="table--mobile.table--rowHover.t1.tree"
    #     )

    #     # Convert it to html to load it iinto pandas
    #     parent_table_el = inner_table_el.find_element(by = By.XPATH, value="..")
    #     parent_table_el_html = parent_table_el.get_attribute("innerHTML")

    #     # pd.read_html will convert parent_table_el_html
    #     # into two dfs, we need first one
    #     html_df = pd.read_html(parent_table_el_html)[0]
    #     html_df.to_csv(f"./Data/{row_id}.csv", index=False, encoding="utf8")

    # # Used for pagination
    # next_page_el = driver.find_element(By.XPATH, value="//a[@aria-label='Next page']")

    # # Non visible on first page
    # # previous_page_el = driver.find_element(By.XPATH, value="//a[@aria-label='Previous page']")

    # raise ("End")


if __name__ == "__main__":
    main()
