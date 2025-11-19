import time
import requests
import json
import yaml

from flask import Flask

app = Flask(__name__)

with open("/data/options.json", "r") as f:
    options = json.load(f)

EMAIL = options["amazon_email"]
PASSWORD = options["amazon_password"]
TWOFA = options["amazon_2fa"]
REGION = options["region"]
WEBHOOK = options["webhook_url"]
INTERVAL = int(options["interval"])
CLEAR = options["clear_after_import"]
DEBUG = options["debug"]

def log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

def get_items():
    """Fake test data — hier kannst du später echten Alexa API Code einfügen."""
    return ["Milch", "Butter", "Käse"]

def clear_items():
    log("Alexa Liste gelöscht.")

def send_to_webhook(items):
    payload = {"items": items}
    r = requests.post(WEBHOOK, json=payload)
    log(f"Webhook Antwort: {r.text}")

@app.route("/")
def root():
    return "Alexa Import läuft"

if __name__ == "__main__":
    log("Addon gestartet und aktiv.")
    while True:
        items = get_items()

        if items:
            log(f"Gefundene Items: {items}")
            send_to_webhook(items)

            if CLEAR:
                clear_items()

        time.sleep(INTERVAL)
