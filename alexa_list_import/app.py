import time
import requests
import yaml

OPTIONS_FILE = "/data/options.json"

def load_options():
    with open(OPTIONS_FILE, "r") as f:
        return yaml.safe_load(f)

def log(msg):
    print(f"[APP] {msg}", flush=True)

def main():
    opts = load_options()

    region = opts.get("region", "de")
    interval = int(opts.get("interval", 180))
    webhook = opts.get("webhook_url")
    clear_after = opts.get("clear_after_import", True)
    debug = opts.get("debug", False)

    log(f"Running Alexa Importer (region={region}, interval={interval}s)")

    while True:
        log("Polling Alexa list… (Dummy)")

        items = ["Test 1", "Test 2"]

        if webhook:
            requests.post(webhook, json={"items": items})

        time.sleep(interval)

if __name__ == "__main__":
    main()
