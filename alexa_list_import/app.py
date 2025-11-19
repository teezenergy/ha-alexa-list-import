import os
import time
import json
import urllib.request

print("=== Alexa List Import Add-on ===")
print(f"Version: {os.getenv('ADDON_VERSION')}")
print("Starting...")

def debug(msg):
    if os.getenv("DEBUG", "false").lower() == "true":
        print("[DEBUG]", msg)

def send_webhook(payload):
    url = os.getenv("WEBHOOK_URL")
    if not url:
        print("[ERROR] Kein Webhook konfiguriert!")
        return
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        urllib.request.urlopen(req)
        print("[INFO] Webhook gesendet.")
    except Exception as e:
        print("[ERROR] Webhook Fehler:", e)

def poll_loop():
    interval = int(os.getenv("INTERVAL", "180"))
    clear_after = os.getenv("CLEAR_AFTER_IMPORT", "false").lower() == "true"

    while True:
        print(f"[INFO] Polling läuft... (Addon {os.getenv('ADDON_VERSION')})")

        # Hier später echte Amazon-API-Abfragen einbauen
        dummy_list = ["Testeintrag 1", "Testeintrag 2"]

        send_webhook({"items": dummy_list})

        if clear_after:
            print("[INFO] Würde Amazon-Liste leeren (noch nicht implementiert).")

        time.sleep(interval)

print("[INFO] Starte Polling...")
poll_loop()
