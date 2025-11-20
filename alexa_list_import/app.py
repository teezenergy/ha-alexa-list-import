import requests
import json
import time
import pytz
from bs4 import BeautifulSoup
from datetime import datetime

CONFIG_PATH = "/data/options.json"

def debug_print(debug, msg):
    if debug:
        print("[DEBUG]", msg)

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def fetch_list(debug):
    url = "https://www.amazon.de/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"
    debug_print(debug, f"Fetching: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    r = requests.get(url, headers=headers)
    
    if r.status_code != 200:
        debug_print(debug, f"ERROR: HTTP {r.status_code}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items = [i.get_text(strip=True) for i in soup.find_all("span")]

    debug_print(debug, f"Extracted items: {items}")
    
    return items

def send_to_webhook(webhook_url, items, debug):
    payload = {"items": items}

    debug_print(debug, f"Sending to webhook: {payload}")

    r = requests.post(webhook_url, json=payload)

    debug_print(debug, f"Webhook status: {r.status_code}")

def clear_list(debug):
    debug_print(debug, f"Simulated clearing of shopping list (TODO: implement login + deletion)")

def main():
    cfg = load_config()

    email = cfg["amazon_email"]
    password = cfg["amazon_password"]
    twofa = cfg["amazon_2fa"]
    webhook_url = cfg["webhook_url"]
    interval = int(cfg["interval"])
    clear_after = bool(cfg["clear_after_import"])
    debug = bool(cfg["debug"])

    print("[app.py] Alexa List Import running")
    print(f"[app.py] Polling every {interval} seconds")

    while True:
        try:
            items = fetch_list(debug)

            if items:
                send_to_webhook(webhook_url, items, debug)

                if clear_after:
                    clear_list(debug)
            else:
                debug_print(debug, "No items found")

        except Exception as e:
            print("[ERROR]", e)

        time.sleep(interval)

if __name__ == "__main__":
    main()
