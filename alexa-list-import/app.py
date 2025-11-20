#!/usr/bin/env python3
import json, time, re, sys
import requests
from urllib.parse import urljoin
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

BASE = "https://www.amazon.de"
LOGIN_URL = BASE + "/ap/signin"
LIST_URL = BASE + "/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"

SESS = requests.Session()
SESS.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1"
    )
})


def debug(msg):
    if DEBUG:
        print("[DEBUG]", msg)


def safe_action(base, action):
    """Normalize Amazon form action URLs safely."""
    if not action:
        return None
    action = action.strip()

    # fix weird trailing garbage like "get"
    action = re.sub(r"(get|post)$", "", action, flags=re.IGNORECASE).strip()

    if action.startswith("http"):
        return action

    return urljoin(base + "/", action.lstrip("/"))


def extract_form(form):
    data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        val = inp.get("value", "")
        if name:
            data[name] = val
    return data


def mobile_login():
    print("[B] ======= NEW POLL =======")
    print("[B] Starting Amazon mobile login...")

    # STEP 1 — Load login page
    r = SESS.get(LOGIN_URL)
    debug("login page status: " + str(r.status_code))

    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        print("[B] ERROR: login form not found")
        return False

    action1 = safe_action(BASE, form.get("action"))
    debug("action1 = " + str(action1))

    payload1 = extract_form(form)
    payload1["email"] = EMAIL

    # STEP 2 — Submit email
    r2 = SESS.post(action1, data=payload1)
    debug("email submit status: " + str(r2.status_code))

    soup2 = BeautifulSoup(r2.text, "html.parser")
    form2 = soup2.find("form")
    if not form2:
        print("[B] ERROR: password form not found")
        return False

    action2 = safe_action(BASE, form2.get("action"))
    debug("action2 = " + str(action2))

    payload2 = extract_form(form2)
    payload2["password"] = PASSWORD

    # STEP 3 — Submit password
    r3 = SESS.post(action2, data=payload2)
    debug("password submit status: " + str(r3.status_code))

    # Check if 2FA is required
    if any(txt in r3.text for txt in ["Two-Step Verification", "Bestätigung benötigt"]):
        print("[B] 2FA required → submitting TOTP")

        soup3 = BeautifulSoup(r3.text, "html.parser")
        form3 = soup3.find("form")
        if not form3:
            print("[B] ERROR: 2FA form not found")
            return False

        action3 = safe_action(BASE, form3.get("action"))
        debug("action3 = " + str(action3))

        payload3 = extract_form(form3)
        payload3["otpCode"] = TOTP

        r4 = SESS.post(action3, data=payload3)
        debug("2FA submit status: " + str(r4.status_code))

        if "signin" in r4.url:
            print("[B] ERROR: 2FA failed")
            return False

    # Final check
    if "signin" in r3.url:
        print("[B] ERROR: login failed")
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

    return r.json()


def main_loop():
    while True:
        if not mobile_login():
            time.sleep(180)
            continue

        data = fetch_list()
        if data:
            print("[B] List OK")
            print(data)

        time.sleep(180)


if __name__ == "__main__":
    main_loop()
