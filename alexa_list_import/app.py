import json
import time
import requests
import os
import yaml

# -------------------------------
# Version aus config.yaml laden
# -------------------------------
def get_addon_version():
    try:
        with open("/etc/hassio/addons/data/" + os.listdir("/etc/hassio/addons/data/")[0] + "/config.yaml", "r") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("version", "unknown")
    except:
        return "unknown"

ADDON_VERSION = get_addon_version()
print(f"[app.py] Alexa List Import Add-on started (version {ADDON_VERSION})")

# -------------------------------
# Optionen laden
# -------------------------------
with open("/data/options.json", "r") as f:
    options = json.load(f)

EMAIL = options.get("amazon_email")
PASSWORD = options.get("amazon_password")
TWOFA = options.get("amazon_2fa")
REGION = options.get("region", "de")
WEBHOOK = options.get("webhook_url", "")
INTERVAL = int(options.get("interval", 180))
CLEAR = bool(options.get("clear_after_import", True))
DEBUG = bool(options.get("debug", False))

def log(msg):
    print(f"[DEBUG v{ADDON_VERSION}] {msg}")

log("Add-on options loaded (password hidden)")

# -------------------------------
# Platzhalter Login
# -------------------------------

def amazon_login():
    log("Login attempt (placeholder logic)")
    # echtes Login folgt später
    return True

# -------------------------------
# Platzhalter Shopping-List Fetch
# -------------------------------

def fetch_shopping():
    log("Fetching shopping list (placeholder logic)")
    return []

# -------------------------------
# Main Loop
# -------------------------------

if amazon_login():
    log("Login successful (placeholder)")
else:
    log("Login failed")

while True:
    log("Polling iteration started")
    log(f"Add-on Version: {ADDON_VERSION}")

    items = fetch_shopping()
    log(f"Fetched {len(items)} items")

    if CLEAR:
        log("Clear after import = True")

    log(f"Sleeping {INTERVAL} seconds")
    time.sleep(INTERVAL)
