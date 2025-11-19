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
log("Password: ******** (hidden)")
log(f"2FA: {TFA}")
log(f"Region: {REGION}")
log(f"Interval: {INTERVAL}")
log(f"Webhook: {WEBHOOK}")
log(f"Clear after import: {CLEAR}")

# Fake Login-System
def login():
    log("Starting login flow…")
    log(f"Preparing request to https://www.amazon.{REGION}/ap/signin")

    try:
        # Fake-Login, denn Amazon blockt diese Requests sowieso
        r = requests.get(f"https://www.amazon.{REGION}")
        log(f"Login HTTP status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        log(f"Login error: {e}")
        return False

# Fake List-Fetcher
def fetch_items():
    log("Fetching shopping list...")
    # Wir simulieren leere Liste, bis echte API implementiert wird
    return []

def send_webhook(items):
    if not WEBHOOK:
        log("No webhook provided.")
        return

    log(f"Sending {len(items)} items to webhook...")

    try:
        requests.post(WEBHOOK, json={"items": items})
    except Exception as e:
        log(f"Webhook error: {e}")

# Main Loop
if not login():
    log("Login failed.")
else:
    log("Login OK")

while True:
    print(f"[INFO] Polling — Add-on Version {os.getenv('ADDON_VERSION')}")
    log("Polling loop iteration")

    items = fetch_items()
    log(f"Fetched {len(items)} items.")

    send_webhook(items)

    if CLEAR:
        log("Clearing imported items (not implemented).")

    log(f"Sleeping for {INTERVAL} seconds…")
    time.sleep(INTERVAL)
