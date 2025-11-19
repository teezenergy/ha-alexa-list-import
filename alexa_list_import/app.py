import os
import time
import requests

print("Alexa List Import Add-on started!")
print(f"[DEBUG] Add-on Version: {os.getenv('ADDON_VERSION')}")

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

def log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

# Eingaben laden
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

# Fake Login
def login():
    log("Starting login flow…")
    try:
        r = requests.get(f"https://www.amazon.{REGION}")
        log(f"Login status: {r.status_code}")
        return True
    except Exception as e:
        log(f"Login error: {e}")
        return False

def fetch_items():
    log("Fetching list…")
    return []

def send_webhook(items):
    if not WEBHOOK:
        log("Webhook missing.")
        return
    log(f"Sending {len(items)} items to webhook.")
    try:
        requests.post(WEBHOOK, json={"items": items})
    except Exception as e:
        log(f"Webhook error: {e}")

if not login():
    log("Login failed.")
else:
    log("Login OK.")

while True:
    print(f"[INFO] Polling — Version {os.getenv('ADDON_VERSION')}")
    items = fetch_items()
    send_webhook(items)
    time.sleep(INTERVAL)
