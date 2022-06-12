#!/usr/bin/python
# -*- encoding: utf-8 -*-
import os, time
import traceback
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import json
from utils_selenium import *
from selenium.webdriver.common.by import By
import requests
from tenacity import retry, wait_fixed

WEBDRIVER_DELAY = 30
SMALLER_DELAY = 3
DATA_DIR = "./Data"
# Error pop-up
# "Грешка"
# driver.find_element(by= By.CLASS_NAME, value = 'popupc').find_element(by= By.TAG_NAME, value = 'button').click()


def main():
    Path(f"{DATA_DIR}").mkdir(parents=True, exist_ok=True)

    driver = get_driver()
    driver.get("https://ceop.apr.gov.rs/ceopweb/sr-cyrl/home")

    WebDriverWait(driver, WEBDRIVER_DELAY).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="query"]'))
    )
    query_el = driver.find_element(by=By.XPATH, value='//*[@id="query"]')
    # Insert search query
    # query_el.send_keys("ROP-BGDU-29")
    query_el.send_keys("ROP-BGDU-38441-")

    # Click on search
    query_el.send_keys(Keys.ENTER)

    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.CLASS_NAME, "table--mobile.table--rowHover.t1")
        )
    )

    @retry(wait=wait_fixed(2))
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
    try:
        nbr_of_pages = int(
            soup.find("li", {"class": "ellipsis"})
            .next_sibling.text.split("page")[-1]
            .strip()
        )
    except:
        nbr_of_pages = 1
    for page in range(0, nbr_of_pages):
        response_json = get_resp("searchString")

        # df = pd.DataFrame(response_json["ResultList"])

        # Predmeti
        for submission_id in response_json["ResultList"]:
            submission_name = submission_id["ParentLegalUniqueNumber"].replace("/", "_")

            Path(f"{DATA_DIR}/{submission_name}").mkdir(parents=True, exist_ok=True)
            with open(
                f"{DATA_DIR}/{submission_name}/{submission_name}.json",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(json.dumps(submission_id, ensure_ascii=False, indent="\t"))
            row_id = response_json["ResultList"].index(submission_id)
            print(f"Clicked on row {row_id}")

            driver.find_element(
                by=By.CSS_SELECTOR,
                value=f"body > rd-app > div > rd-home > div > rd-search > div > div > div > table > tbody > tr:nth-child({row_id+2})",
            ).click()

            # Wait to load (TO DO: implement Wait)
            time.sleep(SMALLER_DELAY)

            # Lista predmeta u dosijeu
            submission_resp = get_resp("getAllCaseDetails")
            print(
                f"Found: {len(submission_resp)} cases for {submission_id['SubmissionId']}"
            )

            # Table: Сви повезани предмети у досијеу
            inner_table_el = driver.find_element(
                by=By.CLASS_NAME, value="table--mobile.table--rowHover.t1.tree"
            )
            # 0th element is header, skip it
            inner_table_rows = inner_table_el.find_elements(by=By.TAG_NAME, value="tr")[
                1:
            ]

            for inner_submission in submission_resp:
                inner_submission_name = inner_submission["LegalUniqueNumber"].replace(
                    "/", ""
                )
                Path(f"{DATA_DIR}/{submission_name}/{inner_submission_name}").mkdir(
                    parents=True, exist_ok=True
                )
                with open(
                    f"{DATA_DIR}/{submission_name}/{inner_submission_name}/{inner_submission_name}.json",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(
                        json.dumps(inner_submission, ensure_ascii=False, indent="\t")
                    )

                WebDriverWait(driver, WEBDRIVER_DELAY).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//*[contains(text(), 'Надлежни орган')]")
                    )
                )
                inner_table_rows[submission_resp.index(inner_submission)].click()

                # Wait for 'javno dostupni podaci u izabranom predmetu' to load
                WebDriverWait(driver, WEBDRIVER_DELAY).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//*[contains(text(), 'ИЗДАТА РЕШЕЊА')]")
                    )
                )

                javno_dostupni_podaci = get_resp("getAllDataDetails")

                # Download pdf if present
                if javno_dostupni_podaci["Documents"]:
                    url = f"https://ceop.apr.gov.rs/eregistrationportal/Public/Manage/LoadRepositoryDocument?fileId={javno_dostupni_podaci['Documents'][0]['Path'].split('/')[2]}"
                    response = requests.request("GET", url)

                    with open(
                        f"{DATA_DIR}/{submission_name}/{inner_submission_name}/{javno_dostupni_podaci['Documents'][0]['DocumentTypeName']}.pdf",
                        "wb",
                    ) as f:
                        f.write(response.content)

                with open(
                    f"{DATA_DIR}/{submission_name}/{inner_submission_name}/javno_dostupni_podaci.json",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(
                        json.dumps(
                            javno_dostupni_podaci, ensure_ascii=False, indent="\t"
                        )
                    )

        # Next page:
        try:
            driver.find_element(By.XPATH, value="//a[@aria-label='Next page']").click()
        except:
            raise Exception("Couldnt find next page element to click")
        # # Wait to load (TO DO: implement Wait)
        time.sleep(2)

    # quit all tabs! (to quit one tab use driver.close())
    driver.quit()

    # # Used for pagination
    # next_page_el = driver.find_element(By.XPATH, value="//a[@aria-label='Next page']")

    # # Non visible on first page
    # # previous_page_el = driver.find_element(By.XPATH, value="//a[@aria-label='Previous page']")

    # raise ("End")


if __name__ == "__main__":
    main()
