#!/usr/bin/env python3
import os
import time
import json
import hashlib
import hmac
import base64
import requests
from urllib.parse import urlencode


# ---------------------------------------------------------
# HA CONFIG
# ---------------------------------------------------------

CONFIG_FILE = "/data/options.json"

with open(CONFIG_FILE, "r") as f:
    cfg = json.load(f)

EMAIL = cfg["amazon_email"]
PASSWORD = cfg["amazon_password"]
TOTP_SECRET = cfg["amazon_2fa"]
REGION = cfg.get("region", "de")
WEBHOOK_URL = cfg["webhook_url"]
CLEAR_AFTER = cfg.get("clear_after_import", True)
DEBUG = cfg.get("debug", False)
INTERVAL = cfg.get("interval", 180)

REGION_HOST = {
    "de": "www.amazon.de",
    "com": "www.amazon.com",
    "co.uk": "www.amazon.co.uk",
}.get(REGION, "www.amazon.de")


session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Mobile Safari/537.36",
})

# ---------------------------------------------------------
# TOTP
# ---------------------------------------------------------

def generate_totp(secret):
    secret = secret.replace(" ", "").replace("-", "")
    missing_padding = len(secret) % 8
    if missing_padding:
        secret += "=" * (8 - missing_padding)

    key = base64.b32decode(secret.upper())

    timestep = int(time.time() / 30)
    msg = timestep.to_bytes(8, "big")

    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 15
    token = (int.from_bytes(h[o:o+4], "big") & 0x7fffffff) % 1000000
    return f"{token:06d}"


# ---------------------------------------------------------
# Amazon Login (Mobile API Emulation)
# ---------------------------------------------------------

def amazon_mobile_login():
    print("[B] Starting Amazon mobile API login...")

    login_url = f"https://{REGION_HOST}/ap/signin"

    # 1) GET login page → capture hidden form fields
    r = session.get(login_url)
    if DEBUG:
        print("[B] login page status:", r.status_code)

    # Extract session specific fields
    # Amazon 2025 login still uses appActionToken + appAction
    import re

    token = re.search(r'name="appActionToken" value="([^"]+)"', r.text)
    action = re.search(r'name="appAction" value="([^"]+)"', r.text)

    if not token or not action:
        print("❌ Could not extract Amazon login tokens")
        return False

    appActionToken = token.group(1)
    appAction = action.group(1)

    totp_code = generate_totp(TOTP_SECRET)

    payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "rememberMe": "true",
        "appActionToken": appActionToken,
        "appAction": appAction,
        "metadata1": "",
        "openid.pape.max_auth_age": "0",
        "enableLoginAccessibility": "true",
        "language": "de_DE",
        "create": "0",
        "continue": f"https://{REGION_HOST}/alexaquantum/sp/alexaShoppingList",
        "forceMobileLayout": "1",
        "otpCode": totp_code,
        "mfaType": "TOTP",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14)",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    r = session.post(login_url, data=payload, headers=headers, allow_redirects=True)

    if DEBUG:
        print("[B] login POST:", r.status_code)
        print("[B] Redirected to:", r.url)
        print("[B] Cookies after login:", list(session.cookies.keys()))

    # Check if login succeeded
    if "session-token" in session.cookies:
        print("✅ Amazon login successful")
        return True

    print("❌ Amazon login failed")
    return False


# ---------------------------------------------------------
# Fetch Alexa Shopping List
# ---------------------------------------------------------

def fetch_shopping_list():
    url = f"https://{REGION_HOST}/alexa-apis/alexa/v2/lists?type=SHOPPING_ITEM"

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14)",
        "Accept": "application/json",
        "x-amzn-sessionid": session.cookies.get("session-id", ""),
    }

    r = session.get(url, headers=headers)

    if DEBUG:
        print("[B] GET list:", r.status_code, r.text[:300])

    if r.status_code != 200:
        print("❌ Could not fetch Alexa shopping list")
        return None

    j = r.json()

    if "lists" not in j or not j["lists"]:
        print("⚠ No items found")
        return []

    items = j["lists"][0].get("items", [])
    names = [i["value"] for i in items]

    print("🛒 Items:", names)
    return names


# ---------------------------------------------------------
# Clear Alexa list items
# ---------------------------------------------------------

def clear_list():
    print("[B] Clearing Alexa list...")
    # Amazon does not provide delete-all → delete one-by-one

    url = f"https://{REGION_HOST}/alexa-apis/alexa/v2/lists?type=SHOPPING_ITEM"
    r = session.get(url)

    j = r.json()
    items = j["lists"][0].get("items", [])
    for item in items:
        del_url = item["links"]["self"]
        session.delete(del_url)
        time.sleep(0.3)

    print("🧽 Alexa list cleared.")


# ---------------------------------------------------------
# Webhook
# ---------------------------------------------------------

def send_webhook(items):
    print("[B] Sending items to HA webhook:", items)
    session.post(WEBHOOK_URL, json={"items": items})
    print("Webhook sent.")


# ---------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------

while True:
    print("\n[B] ======= NEW POLL =======")

    if not amazon_mobile_login():
        print("[B] Login failed, retrying in next cycle")
        time.sleep(INTERVAL)
        continue

    items = fetch_shopping_list()
    if items is None:
        time.sleep(INTERVAL)
        continue

    if items:
        send_webhook(items)

        if CLEAR_AFTER:
            clear_list()

    time.sleep(INTERVAL)
