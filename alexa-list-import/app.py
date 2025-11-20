# Option A - Requests-based Cookie Reuse for Alexa Shopping List
# Full working example with Selenium login + requests fetch

import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

LOGIN_URL = "https://www.amazon.de/ap/signin"
SHOPPING_LIST_URL = (
    "https://www.amazon.de/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"
)


def selenium_login(email, password):
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.get(LOGIN_URL)

    # Email
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "ap_email"))
    ).send_keys(email)
    driver.find_element(By.ID, "continue").click()

    # Password
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "ap_password"))
    ).send_keys(password)
    driver.find_element(By.ID, "signInSubmit").click()

    # Wait until Amazon redirects past login
    time.sleep(5)

    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    driver.quit()
    return cookies


def fetch_list_with_requests(cookies):
    session = requests.Session()

    # Add cookies
    for k, v in cookies.items():
        session.cookies.set(k, v, domain=".amazon.de")

    r = session.get(SHOPPING_LIST_URL, allow_redirects=True)

    if "signin" in r.url:
        return None

    return r.text


if __name__ == "__main__":
    email = "DEINE_EMAIL"
    password = "DEIN_PASSWORD"

    print("[A] Logging in via Selenium...")
    cookies = selenium_login(email, password)
    print("[A] Cookies received:", list(cookies.keys()))

    print("[A] Fetching Alexa shopping list via Requests...")
    page = fetch_list_with_requests(cookies)

    if page is None:
        print("[A] FAILED – Amazon rejected session")
    else:
        print("[A] SUCCESS – Received page:")
        print(page[:1000])
