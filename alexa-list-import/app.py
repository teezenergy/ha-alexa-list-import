# -*- coding: utf-8 -*-
import time
import json
import requests
import pyotp
from bs4 import BeautifulSoup

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[app.py] %(message)s'
)

SHOPPING_LIST_URL = (
    "https://www.amazon.de/alexaquantum/sp/alexaShoppingList"
    "?ref_=list_d_wl_ys_list_1"
)

DELETE_URL = "https://www.amazon.de/alexaquantum/sp/deleteListItem"

AMAZON_LOGIN_URL = (
    "https://www.amazon.de/ap/signin?"
    "openid.pape.max_auth_age=0&"
    "openid.return_to=https://www.amazon.de/&"
    "openid.ns=http://specs.openid.net/auth/2.0"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}

def read_config():
    with open("/data/options.json", "r") as f:
        return json.load(f)

def amazon_login(email, password, secret, debug):
    session = requests.Session()
    session.headers.update(HEADERS)

    if debug:
        logging.debug("Login URL: " + AMAZON_LOGIN_URL)
        logging.debug("Fetching login page")

    r = session.get(AMAZON_LOGIN_URL)
    if r.status_code != 200:
        logging.error("Failed to load Amazon login page")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    form_data = {}

    for inp in soup.find_all("input"):
        name = inp.get("name")
        value = inp.get("value")
        if name:
            form_data[name] = value

    form_data["email"] = email
    form_data["password"] = password

    if debug:
        logging.debug("Submitting login form")

    r2 = session.post(AMAZON_LOGIN_URL, data=form_data)

    if "auth-error-message-box" in r2.text and "Passwort" in r2.text:
        logging.error("Login failed: wrong password")
        return None

    if "auth-mfa-form" in r2.text or "otpCode" in r2.text:
        if debug:
            logging.debug("MFA requested")

        totp = pyotp.TOTP(secret).now()
        mfa_data = {
            "otpCode": totp,
            "rememberDevice": "true"
        }

        r3 = session.post(AMAZON_LOGIN_URL, data=mfa_data)

        if "auth-error-message-box" in r3.text:
            logging.error("MFA failed")
            return None

        if debug:
            logging.debug("MFA successful")

        return session

    if debug:
        logging.debug("Login successful")

    return session

def get_shopping_list(session, debug):
    if debug:
        logging.debug("Fetching shopping list")

    r = session.get(SHOPPING_LIST_URL)

    if debug:
        logging.debug("GET status " + str(r.status_code))

    if r.status_code != 200:
        logging.error("Failed to fetch shopping list page")
        return None

    try:
        data = r.json()
        return data.get("items", [])
    except Exception as e:
        logging.error("JSON parse error: " + str(e))
        return None

def send_to_webhook(items, url, debug):
    payload = {
        "items": items,
        "count": len(items)
    }

    if debug:
        logging.debug("Sending webhook payload")

    try:
        r = requests.post(url, json=payload)
        if debug:
            logging.debug("Webhook response " + str(r.status_code))
    except Exception as e:
        logging.error("Webhook error: " + str(e))

def delete_items(session, items, debug):
    for item in items:
        if "itemId" not in item:
            continue

        if debug:
            logging.debug("Deleting item")

        try:
            session.post(DELETE_URL, json={"itemId": item["itemId"]})
        except:
            pass

def main():
    cfg = read_config()
    debug = cfg.get("debug", False)

    if debug:
        logging.debug("Loaded config")
        logging.debug(json.dumps(cfg))

    logging.info("Polling at " + time.strftime("%Y-%m-%d %H:%M:%S"))

    session = amazon_login(
        cfg["amazon_email"],
        cfg["amazon_password"],
        cfg["amazon_2fa"],
        debug
    )

    if session is None:
        logging.error("Login failed, retrying next interval")
        return

    items = get_shopping_list(session, debug)

    if items is None:
        logging.error("Failed to fetch list")
        return

    logging.info("Found " + str(len(items)) + " items")

    if debug:
        for item in items:
            logging.debug("Item: " + str(item))

    if cfg["webhook_url"]:
        send_to_webhook(items, cfg["webhook_url"], debug)

    if cfg.get("clear_after_import", True):
        delete_items(session, items, debug)

if __name__ == "__main__":
    main()
