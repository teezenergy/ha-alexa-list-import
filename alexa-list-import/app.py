# -*- coding: utf-8 -*-
"""
Alexa List Import - app.py
Robust dynamic Amazon login (form token extraction), TOTP MFA, fetch Alexa shopping list,
send to webhook, optional clear after import.
Sensitive values (password, 2FA secret) are masked in logs.
"""

import time
import json
import requests
import pyotp
from bs4 import BeautifulSoup
import logging
from datetime import datetime

# Logging
logging.basicConfig(level=logging.DEBUG, format='[app.py] %(message)s')

# URLs
SHOPPING_LIST_URL = "https://www.amazon.de/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"
DELETE_URL = "https://www.amazon.de/alexaquantum/sp/deleteListItem"

# Browser-like headers to reduce bot detection
BASE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
}

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def mask(value, visible=2):
    """Return a masked representation of a sensitive value."""
    if value is None:
        return ""
    s = str(value)
    if visible <= 0:
        return "*" * 4
    if len(s) <= visible:
        return "*" * len(s)
    return s[:visible] + "****"

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
def read_config(path="/data/options.json"):
    """Read JSON config from Home Assistant add-on options."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

# ---------------------------------------------------------------------
# Amazon login - dynamic extraction and submit
# ---------------------------------------------------------------------
def amazon_login(email, password, secret, region, debug):
    """
    Try a dynamic login:
    - Load amazon.de homepage
    - Find account/login link
    - Load login page and extract form action + hidden inputs
    - Post credentials to action
    - Handle MFA (TOTP) if required
    Returns: requests.Session() on success, None on failure
    """
    session = requests.Session()
    session.headers.update(BASE_HEADERS)

    # Step 1: Load amazon homepage to find dynamic login link
    try:
        if debug:
            logging.debug("Loading amazon homepage to locate login link")
        r_home = session.get(f"https://www.amazon.{region}/", timeout=20)
    except Exception as exc:
        logging.error("Network error loading homepage: " + str(exc))
        return None

    if r_home.status_code != 200:
        logging.error("Homepage HTTP status != 200: " + str(r_home.status_code))
        return None

    soup_home = BeautifulSoup(r_home.text, "html.parser")

    # Try several strategies to find the login link: id nav-link-accountList or text 'Anmelden'
    login_href = None
    a = soup_home.find("a", {"id": "nav-link-accountList"})
    if a and a.get("href"):
        login_href = a.get("href")
    else:
        # fallback: find links containing 'signin' path
        for link in soup_home.find_all("a", href=True):
            href = link.get("href")
            if "ap/signin" in href or "/signin" in href or "nav_signin" in href:
                login_href = href
                break

    if not login_href:
        logging.error("Could not find login link on amazon homepage")
        return None

    # Produce absolute URL if necessary
    if not login_href.startswith("http"):
        login_url = f"https://www.amazon.{region}{login_href}"
    else:
        login_url = login_href

    if debug:
        logging.debug("Dynamic login URL: " + login_url)

    # Step 2: Load login page
    try:
        r_signin = session.get(login_url, timeout=20)
    except Exception as exc:
        logging.error("Network error loading signin page: " + str(exc))
        return None

    if r_signin.status_code != 200:
        logging.error("Signin page HTTP status != 200: " + str(r_signin.status_code))
        return None

    soup_signin = BeautifulSoup(r_signin.text, "html.parser")

    # Find the sign-in form. Amazon sometimes uses name="signIn" or id 'ap_signin_form'
    form = soup_signin.find("form", {"name": "signIn"}) or soup_signin.find("form", id="ap_signin_form")
    if not form:
        # Attempt to find any form that posts to amazon signin endpoints
        for f in soup_signin.find_all("form"):
            action = f.get("action", "")
            if "signin" in action or "ap/signin" in action or "/ap/signin" in action:
                form = f
                break

    if not form:
        logging.error("Signin form not found on signin page")
        return None

    action = form.get("action", "")
    if not action:
        logging.error("Signin form action attribute is empty")
        return None

    # Normalize action to absolute URL
    if action.startswith("//"):
        action = "https:" + action
    elif action.startswith("/"):
        action = f"https://www.amazon.{region}" + action
    elif not action.startswith("http"):
        # relative path fallback
        action = f"https://www.amazon.{region}/{action}"

    # Collect hidden inputs and existing fields
    post_data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        value = inp.get("value", "")
        post_data[name] = value

    # Determine if site expects email first (two-step) or email+password together
    # If 'email' field exists, fill; if only 'username' or 'email' field missing, still set common keys
    # Fill credentials - do not log password
    # Replace common field names used by Amazon
    possible_email_keys = ["email", "emailType", "username"]
    possible_pass_keys = ["password", "passwd"]

    # Insert email
    inserted_email = False
    for k in possible_email_keys:
        if k in post_data:
            post_data[k] = email
            inserted_email = True
            break
    if not inserted_email:
        # try common name
        post_data["email"] = email

    # Insert password if present in form
    inserted_pass = False
    for k in possible_pass_keys:
        if k in post_data:
            post_data[k] = password
            inserted_pass = True
            break
    if not inserted_pass:
        # If no password field present, we still include password key - some forms accept it
        post_data["password"] = password

    if debug:
        logging.debug("Submitting login form to action: " + action)
        logging.debug("Email used: " + email)
        logging.debug("Password used: ****")
        logging.debug("Masked 2FA secret: " + mask(secret, visible=2))

    # Step 3: Submit credentials
    try:
        r_post = session.post(action, data=post_data, timeout=20)
    except Exception as exc:
        logging.error("Network error posting signin form: " + str(exc))
        return None

    # Detect common failures or redirects that indicate need for additional steps
    post_text = r_post.text or ""

    # Quick wrong password detection
    if "Your password is incorrect" in post_text or "Passwort ist falsch" in post_text:
        logging.error("Login failed: wrong password")
        return None

    # Detect if page asks for email confirmation / another step
    if "auth-password" in post_text and "Enter your password" in post_text:
        # still asking for password - failure
        logging.error("Login did not accept credentials, still asks for password")
        return None

    # Detect MFA / TOTP requirement - look for 'auth-mfa' markers or form with otpCode
    if "auth-mfa-form" in post_text or "otpCode" in post_text or "verification code" in post_text or "enter the code" in post_text:
        if debug:
            logging.debug("MFA step detected; preparing TOTP code")

        # parse form for MFA
        soup_mfa = BeautifulSoup(post_text, "html.parser")
        mfa_form = soup_mfa.find("form") or soup_mfa.find("form", id=True)
        if not mfa_form:
            logging.error("MFA form not found")
            return None

        mfa_action = mfa_form.get("action", "")
        if mfa_action.startswith("//"):
            mfa_action = "https:" + mfa_action
        elif mfa_action.startswith("/"):
            mfa_action = f"https://www.amazon.{region}" + mfa_action
        elif not mfa_action.startswith("http"):
            mfa_action = f"https://www.amazon.{region}/{mfa_action}"

        mfa_data = {}
        for inp in mfa_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            mfa_data[name] = inp.get("value", "")

        # Add totp
        try:
            totp_code = pyotp.TOTP(secret).now()
        except Exception as exc:
            logging.error("Failed to generate TOTP: " + str(exc))
            return None

        # possible field names for OTP
        otp_field_candidates = ["otpCode", "code", "otp", "mfaCode"]
        placed = False
        for candidate in otp_field_candidates:
            if candidate in mfa_data:
                mfa_data[candidate] = totp_code
                placed = True
                break
        if not placed:
            # Just place into otpCode
            mfa_data["otpCode"] = totp_code

        # Remember device if possible
        if "rememberDevice" in mfa_data:
            mfa_data["rememberDevice"] = "true"
        else:
            mfa_data["rememberDevice"] = "true"

        if debug:
            logging.debug("Submitting MFA form to: " + mfa_action)
            logging.debug("TOTP (masked): " + mask(totp_code, visible=0))

        try:
            r_mfa = session.post(mfa_action, data=mfa_data, timeout=20)
        except Exception as exc:
            logging.error("Network error submitting MFA form: " + str(exc))
            return None

        # Check MFA response
        if "auth-error-message-box" in (r_mfa.text or "") or "verification failed" in (r_mfa.text or ""):
            logging.error("MFA verification failed")
            return None

        if debug:
            logging.debug("MFA succeeded, login complete")

        return session

    # If not MFA and not explicit failure, assume login could be successful if we have cookies or redirect to account pages
    # Heuristic: presence of 'your account' or nav link to account with username or cookies set
    if "auth-error-message-box" in post_text:
        logging.error("Login failed, unknown auth error")
        return None

    # check cookies for session identifiers that indicate login
    cookie_keys = [c.name for c in session.cookies]
    if debug:
        logging.debug("Session cookies after login: " + ", ".join(cookie_keys))

    # a successful login often sets 'ubid-main' or 'session-id' or 'x-main'
    success_cookies = ["ubid-main", "session-id", "sso_session", "csm-hit"]
    if any(k in cookie_keys for k in success_cookies):
        if debug:
            logging.debug("Detected login cookies, assuming login success")
        return session

    # Another heuristic: try to access account page
    try:
        acct = session.get(f"https://www.amazon.{region}/gp/your-account/home", timeout=20)
        if acct.status_code == 200 and ("Hello" in acct.text or "Meine Bestellungen" in acct.text or "Ihr Konto" in acct.text):
            if debug:
                logging.debug("Account page accessible, login appears successful")
            return session
    except Exception:
        pass

    # If we reached here, we cannot be sure login succeeded
    logging.error("Unable to confirm login success; Amazon may require additional anti-bot handling")
    return None

# ---------------------------------------------------------------------
# Fetch shopping list
# ---------------------------------------------------------------------
def get_shopping_list(session, debug):
    if debug:
        logging.debug("Fetching shopping list from: " + SHOPPING_LIST_URL)
    try:
        r = session.get(SHOPPING_LIST_URL, timeout=20)
    except Exception as exc:
        logging.error("Network error fetching shopping list: " + str(exc))
        return None

    if r.status_code != 200:
        logging.error("Shopping list HTTP status != 200: " + str(r.status_code))
        return None

    # Amazon often returns JSON; attempt to parse. If not JSON, try to find JSON in page.
    try:
        data = r.json()
        items = data.get("items", []) if isinstance(data, dict) else []
        if debug:
            logging.debug("Shopping list JSON parsed, items count: " + str(len(items)))
        return items
    except Exception:
        # Fallback: search for JSON blob in HTML (some pages embed data in <script>)
        text = r.text or ""
        # common approach: look for "window.__INITIAL_STATE__" or "var awsData"
        start_tokens = ['window.__INITIAL_STATE__ =', 'var awsData =', 'window.AppCache =']
        for token in start_tokens:
            idx = text.find(token)
            if idx != -1:
                try:
                    part = text[idx + len(token):]
                    # naive cut at semicolon
                    end = part.find(";</")
                    if end == -1:
                        end = part.find(";")
                    js = part[:end].strip()
                    # sanitize
                    if js.endswith(";"):
                        js = js[:-1]
                    parsed = json.loads(js)
                    items = parsed.get("items", [])
                    if debug:
                        logging.debug("Found shopping list JSON in page (token: " + token + ")")
                    return items
                except Exception:
                    continue
        logging.error("Could not parse shopping list JSON")
        return None

# ---------------------------------------------------------------------
# Send webhook
# ---------------------------------------------------------------------
def send_to_webhook(items, url, debug):
    if not url:
        return
    payload = {"items": items, "count": len(items)}
    if debug:
        logging.debug("Sending webhook payload (count=" + str(len(items)) + ")")
    try:
        r = requests.post(url, json=payload, timeout=15)
        if debug:
            logging.debug("Webhook response code: " + str(r.status_code))
    except Exception as exc:
        logging.error("Webhook send failed: " + str(exc))

# ---------------------------------------------------------------------
# Delete items after import (optional)
# ---------------------------------------------------------------------
def delete_items(session, items, debug):
    if not items:
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("itemId") or item.get("id") or item.get("item_id")
        if not item_id:
            if debug:
                logging.debug("No itemId for item; skipping: " + str(item))
            continue
        if debug:
            logging.debug("Deleting item id: " + str(item_id))
        try:
            session.post(DELETE_URL, json={"itemId": item_id}, timeout=10)
        except Exception:
            pass

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    cfg = read_config()
    debug = bool(cfg.get("debug", False))

    # sanitize config for logs
    safe_cfg = cfg.copy()
    safe_cfg["amazon_password"] = "****"
    safe_cfg["amazon_2fa"] = mask(cfg.get("amazon_2fa"), visible=2)
    if debug:
        logging.debug("Loaded config (sanitized): " + json.dumps(safe_cfg))

    logging.info("Polling at " + now_ts())

    session = amazon_login(
        cfg.get("amazon_email", ""),
        cfg.get("amazon_password", ""),
        cfg.get("amazon_2fa", ""),
        cfg.get("region", "de"),
        debug
    )

    if session is None:
        logging.error("Login failed, will retry on next interval")
        return

    items = get_shopping_list(session, debug)
    if items is None:
        logging.error("Fetching shopping list failed")
        return

    logging.info("Found " + str(len(items)) + " items on shopping list")

    if debug:
        for it in items:
            logging.debug("Item: " + str(it))

    # Send webhook
    webhook = cfg.get("webhook_url", "")
    if webhook:
        send_to_webhook(items, webhook, debug)

    # clear after import
    if bool(cfg.get("clear_after_import", True)):
        delete_items(session, items, debug)

# ---------------------------------------------------------------------
# If executed directly (the run.sh will call this once per run)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()
