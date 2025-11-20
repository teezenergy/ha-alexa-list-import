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


def mask(text):
    if not text:
        return ""
    if len(text) <= 2:
        return "**"
    return text[:2] + "*" * (len(text) - 2)


# -----------------------------
#  AMAZON LOGIN URL DETECTION
# -----------------------------
def load_login_url():
    logging.info("Loading amazon homepage to locate login link")

    r = SESSION.get(f"https://www.amazon.{REGION}/", timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    # 1️⃣ Primary (desktop)
    link = soup.select_one("#nav-link-accountList")
    if link and link.get("href"):
        url = f"https://www.amazon.{REGION}{link['href']}"
        logging.info(f"Found login URL via nav-link-accountList: {url}")
        return url

    # 2️⃣ Fallback: any link containing /ap/signin
    link = soup.find("a", href=re.compile(r"/ap/signin"))
    if link:
        href = link.get("href")
        if href.startswith("http"):
            return href
        return f"https://www.amazon.{REGION}{href}"

    # 3️⃣ Fallback: form with action to signin
    form = soup.find("form", action=re.compile(r"/ap/signin"))
    if form:
        action = form.get("action")
        if action.startswith("http"):
            return action
        return f"https://www.amazon.{REGION}{action}"

    logging.error("AMAZON HTML RECEIVED:")
    logging.error(r.text[:2000])  # print first 2k chars for debugging

    raise RuntimeError("Amazon login link not found in HTML")


# -----------------------------
#  LOGIN
# -----------------------------
def perform_login():
    try:
        login_url = load_login_url()
    except Exception as e:
        logging.error(str(e))
        return False

    r = SESSION.get(login_url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        logging.error("Login form missing in response HTML")
        return False

    action = form.get("action")
    if not action.startswith("http"):
        action = f"https://www.amazon.{REGION}{action}"

    logging.info(f"Submitting login form to: {action}")
    logging.info(f"Email: {mask(EMAIL)}")
    logging.info(f"Password: {mask(PASSWORD)}")
    logging.info(f"2FA: {mask(TOTP_SECRET)}")

    data = {}

    for inp in form.find_all("input"):
        name = inp.get("name")
        value = inp.get("value", "")
        if name:
            data[name] = value

    data["email"] = EMAIL
    data["password"] = PASSWORD

    r = SESSION.post(action, data=data, timeout=15)

    cookies = SESSION.cookies.get_dict()
    if not any(k.startswith("session-") for k in cookies):
        logging.error("Login failed: No session-* cookies")
        return False

    logging.info("Login successful → session cookies detected")
    return True


# -----------------------------
#  FETCH SHOPPING LIST
# -----------------------------
ALEXA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 9) Alexa/3.0",
    "x-amzn-device-type": "A3NWHXTQ4EBCZS",
    "x-amzn-device-serial": "1234567890",
    "Accept": "application/json",
    "Accept-Language": "de-DE,de;q=0.9",
}


def fetch_list_json():
    url = f"https://www.amazon.{REGION}/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"
    logging.info(f"Fetching shopping list from: {url}")

    r = SESSION.get(url, headers=ALEXA_HEADERS, allow_redirects=True)

    if "/ap/signin" in r.url:
        logging.error("Alexa API redirected to login (session insufficient)")
        return None

    # Try JSON
    try:
        return r.json()
    except:
        pass

    # Try extract in HTML
    m = re.search(r"({\"lists\":.*?})", r.text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass

    logging.error("Could not parse JSON from Alexa Shopping List response")
    return None


# -----------------------------
#  PROCESS + SEND
# -----------------------------
def post_webhook(items):
    if not items:
        logging.info("0 items – nothing to send")
        return

    SESSION.post(WEBHOOK_URL, json={"items": items})
    logging.info("Items sent to webhook.")


# -----------------------------
#  MAIN LOOP
# -----------------------------
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

        items = []
        try:
            for item in data["lists"][0]["items"]:
                items.append(item.get("value"))
        except:
            logging.error("JSON structure unexpected")

        logging.info(f"Found {len(items)} items")
        post_webhook(items)

        time.sleep(180)


if __name__ == "__main__":
    main_loop()
