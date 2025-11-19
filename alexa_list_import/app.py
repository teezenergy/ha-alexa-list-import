import requests
import time
import json
import os
from bs4 import BeautifulSoup

print("Alexa List Import Add-on started!")

# Load env vars from run.sh
EMAIL = os.getenv("amazon_email", "").strip()
PASSWORD = os.getenv("amazon_password", "").strip()
TWOFA = os.getenv("amazon_2fa", "").strip()
REGION = os.getenv("region", "de").strip()
WEBHOOK = os.getenv("webhook_url", "").strip()
INTERVAL = int(os.getenv("interval", "180"))
CLEAR = os.getenv("clear_after_import", "true").lower() == "true"
DEBUG = os.getenv("debug", "false").lower() == "true"

SESSION_FILE = "/data/session.json"
session = requests.Session()

def log(msg):
    if DEBUG:
        print("[DEBUG]", msg)

def save_session():
    with open(SESSION_FILE, "w") as f:
        json.dump(session.cookies.get_dict(), f)
    log("Session saved")

def load_session():
    if not os.path.exists(SESSION_FILE):
        return False
    try:
        cookies = json.load(open(SESSION_FILE))
        session.cookies.update(cookies)
        log("Session loaded")
        return True
    except:
        return False

def amazon_login():
    log("Starting Amazon login")

    login_url = f"https://www.amazon.{REGION}/ap/signin"
    log(f"Login URL: {login_url}")

    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }

    try:
        r = session.post(login_url, data=payload)
    except Exception as e:
        log(f"HTTP login error: {e}")
        return False

    if TWOFA:
        log("Sending 2FA code")
        try:
            session.post(f"https://www.amazon.{REGION}/ap/mfa", data={"otpCode": TWOFA})
        except Exception as e:
            log(f"2FA error: {e}")
            return False

    if "Your Orders" in r.text or "Einkaufen" in r.text:
        log("Login successful")
        save_session()
        return True

    log("Login failed")
    return False

def fetch_list():
    url = f"https://www.amazon.{REGION}/gp/aw/ls/ref=navm_hdr_lists"
    log(f"Fetching list: {url}")

    try:
        r = session.get(url)
    except Exception as e:
        log(f"HTTP error fetching list: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items = []

    for li in soup.find_all("span", {"class": "a-list-item"}):
        text = li.get_text(strip=True)
        if text:
            items.append(text)

    log(f"Items found: {items}")
    return items

def send_to_webhook(items):
    if not WEBHOOK:
        log("No webhook defined")
        return

    for item in items:
        try:
            requests.post(WEBHOOK, json={"item": item})
            log(f"Sent: {item}")
        except:
            log(f"Webhook failed for {item}")

def clear_list():
    log("Clearing list (not implemented — placeholder)")

def main():
    if not load_session():
        log("No session — logging in")
        if not amazon_login():
            log("Login failed — retrying in next cycle")

    while True:
        items = fetch_list()

        if items:
            send_to_webhook(items)
        else:
            log("No items found")

        if CLEAR:
            clear_list()

        log(f"Sleeping {INTERVAL}s...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
