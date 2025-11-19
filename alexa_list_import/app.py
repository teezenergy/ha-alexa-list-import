import os
import time
import requests

print("Alexa List Import Add-on started!")
print(f"[INFO] Add-on Version: {os.getenv('ADDON_VERSION')}")

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

def log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

EMAIL = os.getenv("AMAZON_EMAIL")
PASSWORD = os.getenv("AMAZON_PASSWORD")
TFA = os.getenv("AMAZON_2FA")
REGION = os.getenv("REGION", "de")
WEBHOOK = os.getenv("WEBHOOK")
INTERVAL = int(os.getenv("INTERVAL", "180"))
CLEAR = os.getenv("CLEAR", "false").lower() == "true"

log(f"Email: {EMAIL}")
log("Password: ********")
log(f"2FA: {TFA}")
log(f"Region: {REGION}")
log(f"Interval: {INTERVAL}")
log(f"Webhook: {WEBHOOK}")
log(f"Clear after import: {CLEAR}")

def login():
    log("Login check…")
    try:
        r = requests.get(f"https://www.amazon.{REGION}")
        log(f"Amazon response: {r.status_code}")
        return True
    except Exception as e:
        log(f"Login error: {e}")
        return False

def fetch_items():
    return []

def send_webhook(items):
    if not WEBHOOK:
        log("No webhook URL configured.")
        return
    try:
        log(f"Sending {len(items)} items to webhook")
        requests.post(WEBHOOK, json={"items": items})
    except Exception as e:
        log(f"Webhook error: {e}")

if login():
    log("Login OK")
else:
    log("Login FAILED")

while True:
    print(f"[INFO] Polling — Add-on Version {os.getenv('ADDON_VERSION')}")
    items = fetch_items()
    send_webhook(items)
    time.sleep(INTERVAL)
