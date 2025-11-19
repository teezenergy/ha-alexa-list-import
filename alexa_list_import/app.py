import requests
import time
import json
import os
from bs4 import BeautifulSoup

print("Alexa List Import Add-on started!")

EMAIL = os.getenv("amazon_email", "").strip()
PASSWORD = os.getenv("amazon_password", "").strip()
TWOFA = os.getenv("amazon_2fa", "").strip()
REGION = os.getenv("region", "de").strip()
WEBHOOK = os.getenv("webhook_url", "").strip()
INTERVAL = int(os.getenv("interval", "180"))
CLEAR = os.getenv("clear_after_import", "true").lower() == "true"
DEBUG = os.getenv("debug", "false").lower() == "true"

BASE_URL = f"https://www.amazon.{REGION}"
LOGIN_URL = f"{BASE_URL}/ap/signin"
LIST_URL = f"{BASE_URL}/gp/aw/ls/ref=navm_hdr_lists"

SESSION_FILE = "/data/session.json"
session = requests.Session()


def safe(v):
    return "*" * len(v) if v else "(empty)"


def log(msg):
    if DEBUG:
        print("[DEBUG]", msg)


def save_session():
    with open(SESSION_FILE, "w") as f:
        json.dump(session.cookies.get_dict(), f)
    log("Session saved.")


def load_session():
    if not os.path.exists(SESSION_FILE):
        return False

    try:
        cookies = json.load(open(SESSION_FILE))
        session.cookies.update(cookies)
        log("Session loaded.")
        return True
    except:
        log("Failed to load session.")
        return False


def amazon_login():
    log(f"Login URL: {LOGIN_URL}")
    log(f"Using Amazon email: {EMAIL}")
    log(f"Amazon password: {safe(PASSWORD)}")
    log(f"Amazon 2FA: {safe(TWOFA)}")

    payload = {"email": EMAIL, "password": PASSWORD}

    try:
        r = session.post(LOGIN_URL, data=payload, timeout=10)
    except Exception as e:
        log(f"Login HTTP error: {e}")
        return False

    # 2FA handling
    if TWOFA:
        try:
            session.post(f"{BASE_URL}/ap/mfa", data={"otpCode": TWOFA}, timeout=10)
        except Exception as e:
            log(f"2FA error: {e}")
            return False

    if "Einkaufen" in r.text or "Your Orders" in r.text:
        log("Login successful!")
        save_session()
        return True

    log("Login failed — page did not contain success markers.")
    return False


def fetch_list():
    log(f"Fetching list from {LIST_URL}")

    try:
        r = session.get(LIST_URL, timeout=10)
    except Exception as e:
        log(f"List fetch error: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    for li in soup.find_all("span", {"class": "a-list-item"}):
        text = li.get_text(strip=True)
        if text:
            items.append(text)

    log(f"Items found: {items}")
    return items


def main():
    if not load_session():
        if not amazon_login():
            log("First login failed — retry next interval.")

    while True:
        items = fetch_list()

        if items:
            log(f"Fetched items: {items}")
        else:
            log("No items found.")

        log(f"Sleeping {INTERVAL} seconds...")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
