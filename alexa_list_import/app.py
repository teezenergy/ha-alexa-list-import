import time
import yaml
import json
import requests
import os

def log(msg):
    print(f"[app.py] {msg}", flush=True)

def load_settings():
    with open("/data/options.json", "r") as f:
        return json.load(f)

def main():
    version = os.getenv("ADDON_VERSION", "unknown")
    log(f"Starting Alexa List Import Add-on v{version}")

    cfg = load_settings()
    interval = int(cfg.get("interval", 180))

    while True:
        log(f"Polling Alexa (Add-on v{version}) ...")

        # --- Hier würdest du den Alexa-API-Aufruf machen ---
        # Dummy print:
        log("Importing Alexa shopping list...")

        time.sleep(interval)


if __name__ == "__main__":
    main()
