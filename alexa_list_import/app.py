import requests
import time
import os
import json
from bs4 import BeautifulSoup

print("Alexa List Import Add-on started!")

EMAIL = os.getenv("amazon_email", "").strip()
PASSWORD = os.getenv("amazon_password", "").strip()
TWOFA = os.getenv("amazon_2fa", "").strip()

REGION = os.getenv("region", "de").strip().replace(" ", "")
WEBHOOK = os.getenv("webhook_url", "").strip()
INTERVAL = int(os.getenv("interval", 180))
CLEAR = os.getenv("clear_after_import", "true").lower() == "true"
DEBUG = os.getenv("debug", "false").lower() == "true"

BASE_URL = f"https://www.amazon.{REGION}"
LOGIN_URL = f"{BASE_URL}/ap/signin"
LIST_URL = f"{BASE_URL}/gp/aw/ls/ref=navm_hdr_lists"

SESSION_FILE = "/data/session.json"
session = requests.Session()


def debug(msg):
    if DEBUG:
        print("[DEBUG]", msg)


def safe(v):
    return "*" * len(v) if v else "(empty)"


def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            cookies = json.load(open(SESSION_FILE))
            session.cookies.update(cookies)
            debug("Session loaded.")
            return True
        except:
            debug("Failed to load session.")
    return False


def save_session():
    with open(SESSION_FILE, "w") as f:
        json.dump(session.cookies.get_dict(), f)
    debug("Session saved.")


def amazon_login():
    debug(f"Login URL: {LOGIN_URL}")
    debug(f"Email: {EMAIL}")
    debug(f"Password: {safe(PASSWORD)}")

    try:
        r = session.post(LOGIN_URL, data={"email": EMAIL, "password": PASSWORD}, timeout=10)
    except Exception as e:
        debug(f"HTTP login error: {e}")
        return False

    if r.status_code == 200:
        debug("Login page fetched.")

    if TWOFA:
        debug("Sending 2FA code...")
        try:
            session.post(f"{BASE_URL}/ap/mfa", data={"otpCode": TWOFA}, timeout=10)
        except Exception as e:
            debug(f"2FA error: {e}")
            return False

    save_session()
    return True


def fetch_list():
    debug(f"Fetching list from {LIST_URL}")

    try:
        r = session.get(LIST_URL, timeout=10)
    except Exception as e:
        debug(f"List fetch error: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items = [span.get_text(strip=True) for span in soup.find_all("span", {"class": "a-list-item"})]
    return items


def main():
    if not load_session():
        amazon_login()

    while True:
        debug("Polling list...")
        items = fetch_list()
        debug(f"Items: {items}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
