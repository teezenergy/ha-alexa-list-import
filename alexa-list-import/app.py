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

SHOPPING_LIST_URL = "https://www.amazon.de/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"
DELETE_URL = "https://www.amazon.de/alexaquantum/sp/deleteListItem"

def read_config():
    with open("/data/options.json", "r") as f:
        return json.load(f)

def amazon_login(email, password, secret, region, debug):
    session = requests.Session()

    login_url = "https://www.amazon." + region + "/ap/signin"
    if debug:
        logging.debug("Login URL: " + login_url)

    r = session.get(login_url)
    if r.status_code != 200:
        logging.error("Failed to load Amazon login page.")
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
        logging.debug("Sending login form...")

    r2 = session.post(login_url, data=form_data)

    if "auth-mfa-otpcode" in r2.text:
        if debug:
            logging.debug("Amazon requires TOTP 2FA code...")

        totp = pyotp.TOTP(secret).now()
        mfa_data = {
            "otpCode": totp,
            "rememberDevice": "true"
        }

        r3 = session.post(login_url, data=mfa_data)
        if "Your password is incorrect" in r3.text:
            logging.error("Login failed (wrong password?)")
            return None

        if debug:
            logging.debug("2FA accepted.")
        return session

    if "Your password is incorrect" in r2.text:
        logging.error("Login failed (wrong password?)")
        return None

    if debug:
        logging.debug("Login successful without 2FA.")

    return session

def get_shopping_list(session, debug):
    if debug:
        logging.debug("Fetching shopping list from: " + SHOPPING_LIST_URL)

    r = session.get(SHOPPING_LIST_URL)

    if debug:
        logging.debug("GET status: " + str(r.status_code))

    if r.status_code != 200:
        logging.error("Could not load shopping list page.")
        return None

    try:
        data = r.json()
        if debug:
            logging.debug("Shopping list JSON loaded.")

        return data.get("items", [])
    except Exception as e:
        logging.error("Error parsing shopping list JSON: " + str(e))
        return None

def send_to_webhook(items, url, debug):
    payload = {
        "items": items,
        "count": len(items)
    }

    if debug:
        logging.debug("Sending webhook payload: " + json.dumps(payload))

    try:
        r = requests.post(url, json=payload)
        if debug:
            logging.debug("Webhook response: " + str(r.status_code))
    except Exception as e:
        logging.error("Webhook error: " + str(e))

def delete_items(session, items, debug):
    for item in items:
        if "itemId" not in item:
            continue

        if debug:
            logging.debug("Deleting item: " + str(item))

        try:
            session.post(DELETE_URL, json={"itemId": item["itemId"]})
        except Exception:
            pass

def main():
    cfg = read_config()
    debug = cfg.get("debug", False)

    if debug:
        logging.debug("Loaded config: " + json.dumps(cfg))

    session = amazon_login(
        cfg["amazon_email"],
        cfg["amazon_password"],
        cfg["amazon_2fa"],
        cfg.get("region", "de"),
        debug
    )

    if session is None:
        logging.error("Login failed, retrying next interval.")
        return

    items = get_shopping_list(session, debug)
    if items is None:
        logging.error("Fetching shopping list failed.")
        return

    logging.info("Found " + str(len(items)) + " items.")

    if debug:
        for item in items:
            logging.debug("Item: " + str(item))

    if cfg["webhook_url"]:
        send_to_webhook(items, cfg["webhook_url"], debug)

    if cfg.get("clear_after_import", True):
        delete_items(session, items, debug)

if __name__ == "__main__":
    main()
