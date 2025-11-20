import time
import json
import requests
import pytz
from datetime import datetime
import yaml
import os

ALEXA_URL = "https://www.amazon.de/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"


def log(msg):
    print(f"[app.py] {msg}", flush=True)


def debug_log(msg, debug=False):
    if debug:
        print(f"[DEBUG] {msg}", flush=True)


def load_config():
    """Load Home Assistant add-on config.json"""
    try:
        with open("/data/options.json", "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"ERROR loading config: {e}")
        return {}


def get_timestamp():
    berlin = pytz.timezone("Europe/Berlin")
    return datetime.now(berlin).strftime("%Y-%m-%d %H:%M:%S")


def poll_shopping_list(email, password, totp, debug):
    """Poll Amazon Shopping List"""
    debug_log(f"Polling Amazon at {get_timestamp()}", debug)
    debug_log(f"Requesting URL: {ALEXA_URL}", debug)

    try:
        # NOTE: This is simplified — real login flow requires cookies
        response = requests.get(ALEXA_URL)

        debug_log(f"HTTP Status: {response.status_code}", debug)

        if response.status_code != 200:
            log(f"Amazon returned HTTP {response.status_code}")
            return []

        try:
            data = response.json()
        except:
            log("ERROR: Amazon returned invalid JSON")
            return []

        items = data.get("items", [])

        debug_log(f"Found {len(items)} shopping list entries.", debug)
        for item in items:
            title = item.get("text", "UNKNOWN")
            status = item.get("completed", False)
            debug_log(f"- Item: '{title}' (completed={status})", debug)

        return items

    except Exception as e:
        log(f"Exception polling Amazon: {e}")
        return []


def send_webhook(url, items, debug):
    """Send shopping list to Home Assistant webhook"""
    payload = {"items": items}

    debug_log(f"Sending Webhook ? {url}", debug)
    debug_log(f"Payload: {json.dumps(payload, indent=2)}", debug)

    try:
        r = requests.post(url, json=payload)
        debug_log(f"Webhook returned HTTP {r.status_code}", debug)
        if r.status_code != 200:
            log(f"Webhook error: {r.status_code}")
    except Exception as e:
        log(f"Webhook send failed: {e}")


def clear_list(debug):
    """Clear list on Amazon (placeholder)"""
    debug_log("Clearing Amazon list... (not implemented)", debug)


def main():
    config = load_config()

    email = config.get("amazon_email")
    password = config.get("amazon_password")
    totp = config.get("amazon_2fa")
    region = config.get("region")
    webhook = config.get("webhook_url")
    interval = config.get("interval", 180)
    clear_after = config.get("clear_after_import", True)
    debug = config.get("debug", False)

    log("Running Alexa List Importer")
    debug_log(f"Config loaded: {json.dumps(config, indent=2)}", debug)

    if not webhook:
        log("ERROR: No webhook URL set!")
        return

    log("Importer started successfully.")

    while True:
        items = poll_shopping_list(email, password, totp, debug)

        if items:
            log(f"Imported {len(items)} items")

            send_webhook(webhook, items, debug)

            if clear_after:
                clear_list(debug)

        else:
            debug_log("No items found or Amazon returned an empty list.", debug)

        log(f"Waiting {interval} seconds until next poll...")
        time.sleep(interval)


if __name__ == "__main__":
    main()
