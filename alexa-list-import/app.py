#!/usr/bin/env python3
import json, time, re, sys
import requests
from bs4 import BeautifulSoup

CFG_PATH = "/data/options.json"

def load_cfg():
    with open(CFG_PATH, "r") as f:
        return json.load(f)

cfg = load_cfg()

EMAIL = cfg["amazon_email"]
PASSWORD = cfg["amazon_password"]
TOTP = cfg["amazon_2fa"]
WEBHOOK = cfg["webhook_url"]
CLEAR_AFTER = cfg.get("clear_after_import", True)
DEBUG = cfg.get("debug", False)

SESS = requests.Session()
SESS.headers.update({
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1"
})

LOGIN_URL = "https://www.amazon.de/ap/signin"
LIST_URL = "https://www.amazon.de/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"


def debug(msg):
    if DEBUG:
        print("[DEBUG]", msg)


def mobile_login():
    print("[B] ======= NEW POLL =======")
    print("[B] Starting Amazon mobile login...")

    r = SESS.get(LOGIN_URL)
    debug("login page status: " + str(r.status_code))

    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        print("[B] ERROR: login form not found")
        return False

    action = form.get("action")
    if not action.startswith("http"):
        action = "https://www.amazon.de" + action

    payload = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        val = inp.get("value", "")
        if name:
            payload[name] = val

    payload["email"] = EMAIL

    r2 = SESS.post(action, data=payload)
    debug("email submit status: " + str(r2.status_code))

    soup2 = BeautifulSoup(r2.text, "html.parser")
    form2 = soup2.find("form")
    if not form2:
        print("[B] ERROR: password form not found")
        return False

    action2 = form2.get("action")
    if not action2.startswith("http"):
        action2 = "https://www.amazon.de" + action2

    payload2 = {}
    for inp in form2.find_all("input"):
        name = inp.get("name")
        val = inp.get("value", "")
        if name:
            payload2[name] = val

    payload2["password"] = PASSWORD

    r3 = SESS.post(action2, data=payload2)
    debug("password submit status: " + str(r3.status_code))

    if "Two-Step Verification" in r3.text or "Bestätigung benötigt" in r3.text:
        print("[B] 2FA required → submitting TOTP")
        soup3 = BeautifulSoup(r3.text, "html.parser")
        form3 = soup3.find("form")
        if not form3:
            print("[B] ERROR: 2FA form not found")
            return False

        action3 = form3.get("action")
        if not action3.startswith("http"):
            action3 = "https://www.amazon.de" + action3

        payload3 = {}
        for inp in form3.find_all("input"):
            name = inp.get("name")
            val = inp.get("value", "")
            if name:
                payload3[name] = val

        payload3["otpCode"] = TOTP

        r4 = SESS.post(action3, data=payload3)
        debug("2FA submit status: " + str(r4.status_code))

        if "ap/signin" in r4.url:
            print("[B] ERROR: 2FA failed")
            return False

    if "ap/signin" in r3.url:
        print("[B] Login failed")
        return False

    print("[B] Login success")
    return True


def fetch_list():
    print("[B] Fetching Alexa list...")
    r = SESS.get(LIST_URL, allow_redirects=True)
    if "signin" in r.url:
        print("[B] ERROR: session rejected")
        return None

    if not r.text.strip().startswith("{"):
        print("[B] ERROR: list is not JSON")
        return None

    data = r.json()
    return data


def main_loop():
    while True:
        if not mobile_login():
            print("[B] Login failed, retry next interval")
            time.sleep(180)
            continue

        lst = fetch_list()
        if lst:
            print("[B] List OK:", lst)

        time.sleep(180)


if __name__ == "__main__":
    main_loop()
