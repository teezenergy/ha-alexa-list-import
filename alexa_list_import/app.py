#!/usr/bin/env python3
import requests, argparse, time, json, os, sys
from pathlib import Path

SESSION_FILE = "/data/amazon_session.json"

def dbg(msg):
    print(f"[DEBUG] {msg}", flush=True)

def save_session(cookies):
    try:
        d = requests.utils.dict_from_cookiejar(cookies)
        with open(SESSION_FILE, "w") as f:
            json.dump(d, f)
        dbg(f"Saved session to {SESSION_FILE}")
    except Exception as e:
        dbg(f"Failed to save session: {e}")

def load_session():
    if Path(SESSION_FILE).exists():
        try:
            with open(SESSION_FILE, "r") as f:
                d = json.load(f)
            cj = requests.utils.cookiejar_from_dict(d)
            s = requests.Session()
            s.cookies = cj
            dbg("Loaded session from disk")
            return s
        except Exception as e:
            dbg(f"Failed to load session: {e}")
            return None
    dbg("No session file found")
    return None

def amazon_login(email, password, otp, region, debug=False):
    dbg("Starting login flow")
    s = requests.Session()
    # Note: This is a simplified POST flow. Amazon login flows are more complex in reality.
    signin_url = f"https://www.amazon.{region}/ap/signin"
    dbg(f"Preparing to POST credentials to {signin_url} (this is a simplified flow)")

    # Minimal payload — may not succeed depending on Amazon's actual tokens/hidden fields
    payload = {"email": email, "password": password}
    try:
        r = s.post(signin_url, data=payload, allow_redirects=True, timeout=15)
        dbg(f"POST {signin_url} -> status {r.status_code}")
    except Exception as e:
        dbg(f"HTTP error during login POST: {e}")
        return None, "http_error"

    # Heuristics: check page for 2FA prompt or successful redirect
    text = r.text.lower()
    if "two-step verification" in text or "one-time password" in text or "enter the code" in text:
        dbg("Amazon is asking for 2FA / OTP")
        # instruct user how to provide the OTP
        return s, "need_2fa"

    if r.status_code != 200:
        dbg(f"Login returned status {r.status_code}")
        return None, "login_failed"

    # crude check for successful login: presence of 'sign out' or account strings
    if "sign out" in text or "hello" in text:
        save_session(s.cookies)
        dbg("Login appears successful (heuristic matched). Session saved.")
        return s, "ok"

    dbg("Unable to determine login success; treating as 'maybe_ok'")
    save_session(s.cookies)
    return s, "maybe_ok"

def get_shopping_list(s, region):
    dbg("Fetching shopping list (HTML scrape)")
    url = f"https://www.amazon.{region}/gp/huc/view.html?ie=UTF8&ref_=xx_shs_dpxx"
    try:
        r = s.get(url, timeout=15)
        dbg(f"GET {url} -> {r.status_code}")
    except Exception as e:
        dbg(f"HTTP error when fetching shopping list: {e}")
        return []
    if r.status_code != 200:
        dbg(f"Non-200 response fetching list: {r.status_code}")
        return []
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    # This selector is a best-effort; Amazon markup varies per region/time.
    items = []
    for el in soup.select("li"):
        text = el.get_text(strip=True)
        if text:
            items.append(text)
    dbg(f"Parsed {len(items)} candidate items (raw).")
    # De-duplicate and filter
    clean = []
    for it in items:
        if len(it) > 2 and it.lower() not in [x.lower() for x in clean]:
            clean.append(it)
    dbg(f"Filtered to {len(clean)} list items.")
    return clean

def delete_items(s, region):
    dbg("delete_items called — this is a placeholder. Implement if you want actual deletion.")
    return True

def send_webhook(url, items):
    if not url:
        dbg("No webhook configured; skipping webhook send.")
        return
    dbg(f"Sending webhook to {url} with {len(items)} items.")
    try:
        r = requests.post(url, json={"items": items}, timeout=10)
        dbg(f"Webhook response: {r.status_code} {r.text}")
    except Exception as e:
        dbg(f"Webhook POST failed: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--twofa", default="")
    parser.add_argument("--region", default="de")
    parser.add_argument("--webhook", default="")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--clear", default="false")
    parser.add_argument("--mode", default="daemon")  # daemon or oneshot
    parser.add_argument("--debug", default="false")
    args = parser.parse_args()

    dbg("Starting app.py")
    dbg(f"Mode: {args.mode}, Region: {args.region}, Interval: {args.interval}")

    session = load_session()

    if session is None:
        dbg("No existing session — performing login")
        session, status = amazon_login(args.email, args.password, args.twofa, args.region, debug=(args.debug=="true"))
        if status == "http_error":
            dbg("Login HTTP error: check network or Amazon blocking")
            if args.mode == "oneshot":
                sys.exit(2)
        if status == "need_2fa":
            dbg("Login requires 2FA. Please open the Add-on configuration in Home Assistant, set 'amazon_2fa' to the received OTP code and restart the add-on in 'oneshot' mode.")
            dbg("How to proceed (step-by-step):")
            dbg(" 1) Get the OTP from your authenticator or SMS")
            dbg(" 2) In Home Assistant: Add-ons -> Alexa List Import -> Configuration -> amazon_2fa set the code")
            dbg(" 3) Set mode to 'oneshot' (in options) and restart the add-on")
            dbg("When you restart in oneshot mode the add-on will finish login and save session.")
            sys.exit(3)
        if status in ("login_failed", None):
            dbg("Login failed. Check email/password. Exiting.")
            sys.exit(4)
        dbg(f"Login status: {status}")

    else:
        dbg("Using loaded session.")

    if args.mode == "oneshot":
        dbg("Oneshot mode: perform single fetch -> show items -> exit")
        items = get_shopping_list(session, args.region)
        dbg(f"Found items: {items}")
        if items:
            send_webhook(args.webhook, items)
            if str(args.clear).lower() == "true":
                delete_items(session, args.region)
        dbg("Oneshot finished. Exiting.")
        sys.exit(0)

    # Daemon mode: loop forever
    while True:
        dbg("Polling loop iteration: fetching list")
        items = get_shopping_list(session, args.region)
        dbg(f"Items: {items}")
        if items:
            send_webhook(args.webhook, items)
            if str(args.clear).lower() == "true":
                delete_items(session, args.region)
        dbg(f"Sleeping for {args.interval} seconds")
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    main()
