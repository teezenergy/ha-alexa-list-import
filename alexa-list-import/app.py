#!/usr/bin/env python3
import requests
import time
import logging
import os
import json
import re
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='[app.py] %(message)s')

EMAIL = os.getenv("amazon_email")
PASSWORD = os.getenv("amazon_password")
TOTP_SECRET = os.getenv("amazon_2fa")
WEBHOOK_URL = os.getenv("webhook_url")
REGION = os.getenv("region", "de")

SESSION = requests.Session()

# Alexa Device Headers (Required 2025)
ALEXA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 9) Alexa/3.0",
    "x-amzn-device-type": "A3NWHXTQ4EBCZS",
    "x-amzn-device-serial": "1234567890",
    "x-amzn-app-id": "A2M4YX06LWP8WI",
    "Accept": "application/json",
    "Accept-Language": "de-DE,de;q=0.9",
}


def mask(text):
    if not text:
        return ""
    if len(text) <= 2:
        return "**"
    return text[:2] + "*" * (len(text) - 2)


def load_login_url():
    logging.info("Loading amazon homepage to locate login link")
    r = SESSION.get(f"https://www.amazon.{REGION}/")
    soup = BeautifulSoup(r.text, "html.parser")

    signin_link = soup.select_one("#nav-link-accountList")
    if not signin_link:
        raise RuntimeError("Login link not found")

    url = "https://www.amazon.%s%s" % (REGION, signin_link["href"])
    logging.info(f"Dynamic login URL: {url}")
    return url


def perform_login():
    login_url = load_login_url()
    r = SESSION.get(login_url)

    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        raise RuntimeError("Login form missing")

    action = form.get("action")
    if not action.startswith("https://"):
        action = f"https://www.amazon.{REGION}{action}"

    logging.info(f"Submitting login form to action: {action}")
    logging.info(f"Email used: {EMAIL}")
    logging.info(f"Password used: {mask(PASSWORD)}")
    logging.info(f"Masked 2FA secret: {mask(TOTP_SECRET)}")

    data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        value = inp.get("value", "")
        if not name:
            continue
        data[name] = value

    # override user/pass fields
    data["email"] = EMAIL
    data["password"] = PASSWORD

    r = SESSION.post(action, data=data)

    # Check if login cookies exist
    cookies = SESSION.cookies.get_dict()
    good = any(k.startswith("session-") for k in cookies)
    if not good:
        logging.error("Login did not produce session cookies")
        return False

    logging.info("Detected login cookies, assuming login success")

    # Check if "at-main" is there (required for Alexa)
    if "at-main" not in cookies:
        logging.warning("at-main cookie missing – Alexa API may reject session")

    return True


def fetch_list_json():
    url = f"https://www.amazon.{REGION}/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"
    logging.info(f"Fetching shopping list from: {url}")

    r = SESSION.get(url, headers=ALEXA_HEADERS, allow_redirects=True)

    # If redirected to login → session insufficient
    if "/ap/signin" in r.url:
        logging.error("Alexa API redirected to login – session not accepted as device")
        return None

    # Try find JSON
    try:
        # sometimes direct JSON
        data = r.json()
        return data
    except:
        pass

    # sometimes inside HTML <script>…</script>
    m = re.search(r"({\"lists\":.*?})", r.text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass

    logging.error("Could not parse shopping list JSON")
    return None


def post_webhook(items):
    if not items:
        logging.info("No items to send")
        return

    payload = {"items": items}
    r = SESSION.post(WEBHOOK_URL, json=payload)
    logging.info(f"Webhook result: HTTP {r.status_code}")


def main_loop():
    while True:
        logging.info(f"Polling at {time.strftime('%Y-%m-%d %H:%M:%S')}")

        if not perform_login():
            logging.error("Login failed – retrying next interval")
            time.sleep(180)
            continue

        data = fetch_list_json()
        if not data:
            logging.error("Fetching shopping list failed")
            time.sleep(180)
            continue

        # Extract items
        items = []
        try:
            for item in data["lists"][0]["items"]:
                items.append(item.get("value"))
        except:
            logging.error("Shopping list JSON structure unexpected")

        logging.info(f"Found {len(items)} items")

        post_webhook(items)

        time.sleep(180)


if __name__ == "__main__":
    main_loop()
