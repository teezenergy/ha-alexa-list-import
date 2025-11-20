# -*- coding: utf-8 -*-
"""
Complete app.py for Alexa List Import Add-on (Selenium + Chromium)
- Full flow: browser login (2025-compatible), cookie extraction, Alexa shopping list fetch,
  webhook send, optional clear-after-import.
- Config is read from environment variables (exported by run.sh).
- Sensitive values are masked in logs.
"""

import os
import time
import json
import logging
import requests
import pyotp
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------------
# Logging
# ------------------------
DEBUG = os.environ.get("debug", "false").lower() == "true"
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(level=LOG_LEVEL, format='[app.py] %(message)s')
logger = logging.getLogger("alexa_list_import")

# ------------------------
# Config (from run.sh exports / addon env)
# ------------------------
AMAZON_EMAIL = os.environ.get("amazon_email", "").strip()
AMAZON_PASSWORD = os.environ.get("amazon_password", "").strip()
AMAZON_2FA = os.environ.get("amazon_2fa", "").strip()
REGION = os.environ.get("region", "de").strip()
WEBHOOK_URL = os.environ.get("webhook_url", "").strip()
CLEAR_AFTER = os.environ.get("clear_after_import", "true").lower() == "true"
INTERVAL = int(os.environ.get("interval", "180"))
# user-agent + headers for Alexa API requests
ALEXA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 9) Alexa/3.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}

SHOPPING_LIST_URL = f"https://www.amazon.{REGION}/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"
DELETE_URL = f"https://www.amazon.{REGION}/alexaquantum/sp/deleteListItem"

# The 2025-compatible login URL (OpenID query parameters)
AMAZON_LOGIN_URL = (
    "https://www.amazon." + REGION + "/ap/signin?"
    "openid.pape.max_auth_age=0&"
    "openid.return_to=https%3A%2F%2Fwww.amazon." + REGION + "%2F%3Fref_%3Dnav_signin&"
    "openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&"
    "openid.assoc_handle=deflex&"
    "openid.mode=checkid_setup&"
    "openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&"
    "openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
)

# ------------------------
# Helpers
# ------------------------
def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def mask(value, visible=2):
    if not value:
        return ""
    s = str(value)
    if visible <= 0:
        return "*" * 4
    if len(s) <= visible:
        return "*" * len(s)
    return s[:visible] + "*" * (len(s) - visible)

def safe_log_config():
    cfg = {
        "amazon_email": mask(AMAZON_EMAIL, visible=3),
        "amazon_password": "****",
        "amazon_2fa": mask(AMAZON_2FA, visible=2),
        "region": REGION,
        "webhook_url": WEBHOOK_URL,
        "interval": INTERVAL,
        "clear_after_import": CLEAR_AFTER,
        "debug": DEBUG,
    }
    logger.debug("Loaded config (sanitized): %s", json.dumps(cfg))

# ------------------------
# Selenium / Chrome setup
# ------------------------
def start_chrome_driver():
    """
    Start headless Chromium via Selenium. Assumes chromium & chromedriver exist in path.
    """
    chrome_options = Options()
    # Use new headless mode when available; fallback to classic if not.
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=de-DE")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Try to create driver
    try:
        driver = webdriver.Chrome(options=chrome_options)
        # hide webdriver property
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            })
        except Exception:
            pass
        return driver
    except WebDriverException as e:
        logger.error("Failed to start Chrome WebDriver: %s", e)
        raise

# ------------------------
# Login flow (Selenium)
# ------------------------
def perform_login_with_browser(driver):
    """
    Perform Amazon login using direct /ap/signin URL.
    Returns True on success, False on failure.
    The driver is left open (caller must quit).
    """
    logger.info("Starting Amazon login sequence at %s", now_ts())
    logger.debug("Login URL: %s", AMAZON_LOGIN_URL)

    try:
        driver.get(AMAZON_LOGIN_URL)
    except Exception as e:
        logger.error("Failed to open login URL: %s", e)
        return False

    time.sleep(1.2)

    # Input email
    try:
        email_el = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.ID, "ap_email")))
        email_el.clear()
        email_el.send_keys(AMAZON_EMAIL)
        # click continue button if present
        try:
            cont = driver.find_element(By.ID, "continue")
            cont.click()
        except Exception:
            email_el.submit()
        logger.debug("Email submitted (masked): %s", mask(AMAZON_EMAIL))
    except TimeoutException:
        # email input not found - maybe already on password step or different flow
        logger.debug("Email input not found, proceeding to password step if present")

    time.sleep(1.0)

    # Input password
    try:
        pwd_el = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.ID, "ap_password")))
        pwd_el.clear()
        pwd_el.send_keys(AMAZON_PASSWORD)
        # click sign-in
        try:
            signin_btn = driver.find_element(By.ID, "signInSubmit")
            signin_btn.click()
        except Exception:
            pwd_el.submit()
        logger.debug("Password submitted (masked)")
    except TimeoutException:
        logger.error("Password input not found on signin page")
        # proceed to check whether logged in

    time.sleep(2.0)

    # 2FA (TOTP) handling
    try:
        # Amazon sometimes uses name 'otpCode' or id 'auth-mfa-otpcode'
        otp_el = None
        try:
            otp_el = driver.find_element(By.ID, "auth-mfa-otpcode")
        except NoSuchElementException:
            try:
                otp_el = driver.find_element(By.NAME, "otpCode")
            except NoSuchElementException:
                otp_el = None

        if otp_el and AMAZON_2FA:
            # generate totp
            try:
                code = pyotp.TOTP(AMAZON_2FA).now()
            except Exception as e:
                logger.error("Failed to generate TOTP: %s", e)
                return False
            otp_el.clear()
            otp_el.send_keys(code)
            # find submit
            try:
                submit_btn = driver.find_element(By.ID, "auth-signin-button")
                submit_btn.click()
            except Exception:
                otp_el.submit()
            logger.debug("Submitted TOTP (masked): %s", mask(code, visible=0))
            time.sleep(2.5)
        else:
            logger.debug("No TOTP prompt detected")
    except Exception as e:
        logger.debug("2FA step error (non-fatal): %s", e)

    # Final verification: try to open account page
    try:
        driver.get(f"https://www.amazon.{REGION}/gp/your-account/home")
        time.sleep(1.0)
        page_text = driver.page_source.lower()
        if ("anmelden" in page_text and "passwort" in page_text) or ("sign-in" in page_text):
            logger.error("Post-login check indicates still on signin page")
            return False
    except Exception:
        # it's ok if account page cannot be loaded; continue to check cookies
        pass

    # Collect cookies and check for typical session cookies
    cookies = driver.get_cookies()
    cookie_names = [c.get("name") for c in cookies if c.get("name")]
    logger.debug("Browser cookies after login: %s", cookie_names)

    # Heuristic: presence of session tokens like 'session-id' or 'session-token' or 'ubid' or 'at-main'
    success_tokens = {"session-id", "session-token", "ubid-main", "ubid-acbde", "at-main"}
    if any(tok in cookie_names for tok in success_tokens):
        logger.info("Detected session cookies, assuming login success")
        return True

    # As fallback, if any cookie exists treat as success (best-effort)
    if cookies:
        logger.info("Cookies present after login (no obvious session cookie names) — proceeding")
        return True

    logger.error("No cookies set after login; login appears to have failed")
    return False

# ------------------------
# Cookies -> requests.Session
# ------------------------
def cookies_to_requests_session(driver):
    sess = requests.Session()
    sess.headers.update(ALEXA_HEADERS)
    for c in driver.get_cookies():
        # ensure cookie domain formatting
        name = c.get("name")
        value = c.get("value")
        domain = c.get("domain", None)
        try:
            sess.cookies.set(name, value, domain=domain)
        except Exception:
            # fallback: set without domain
            sess.cookies.set(name, value)
    return sess

# ------------------------
# Fetch shopping list
# ------------------------
def fetch_shopping_list(session):
    logger.debug("Fetching shopping list from: %s", SHOPPING_LIST_URL)
    try:
        r = session.get(SHOPPING_LIST_URL, timeout=20, allow_redirects=True)
    except Exception as e:
        logger.error("Network error fetching shopping list: %s", e)
        return None

    # If redirected to signin page, session not accepted by Alexa API
    if "/ap/signin" in r.url:
        logger.error("Alexa shopping list request redirected to signin (session not accepted)")
        return None

    # try JSON
    try:
        data = r.json()
        logger.debug("Shopping list response JSON parsed")
        return data
    except Exception:
        # fallback: attempt to extract embedded JSON
        text = r.text or ""
        # try several tokens
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'("items"\s*:\s*\[.*?\])',
            r'({"lists"\s*:\s*\[.*?\]})'
        ]
        for p in patterns:
            m = re.search(p, text, re.S)
            if m:
                txt = m.group(1)
                # try to wrap if needed
                try:
                    parsed = json.loads(txt)
                    return parsed
                except Exception:
                    # try to trim trailing semicolons or script endings
                    js = txt.strip().rstrip(";")
                    try:
                        parsed = json.loads(js)
                        return parsed
                    except Exception:
                        continue
    logger.error("Could not parse shopping list response")
    return None

# ------------------------
# Normalize items
# ------------------------
def extract_items_from_data(data):
    if not data:
        return []
    items = []
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            items = data["items"]
        elif "lists" in data and isinstance(data["lists"], list) and len(data["lists"]) > 0:
            first = data["lists"][0]
            if isinstance(first, dict):
                items = first.get("items", first.get("Items", []))
    elif isinstance(data, list):
        items = data
    # ensure list
    return items if isinstance(items, list) else []

# ------------------------
# Webhook
# ------------------------
def send_to_webhook(items):
    if not WEBHOOK_URL:
        logger.info("No webhook configured; skipping webhook send")
        return
    payload = {"items": items, "count": len(items)}
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        logger.info("Webhook HTTP %s", r.status_code)
    except Exception as e:
        logger.error("Webhook POST failed: %s", e)

# ------------------------
# Delete items
# ------------------------
def delete_items(session, items):
    if not items:
        return
    for it in items:
        if isinstance(it, dict):
            item_id = it.get("itemId") or it.get("id") or it.get("item_id")
        else:
            item_id = None
        if not item_id:
            logger.debug("Skipping delete for item without id: %s", str(it))
            continue
        try:
            session.post(DELETE_URL, json={"itemId": item_id}, timeout=10)
            logger.debug("Requested deletion for item id: %s", item_id)
        except Exception:
            logger.debug("Failed deletion request for item id: %s", item_id)

# ------------------------
# Main
# ------------------------
def main():
    safe_log_config()
    logger.info("Polling at %s", now_ts())

    driver = None
    try:
        driver = start_chrome_driver()
    except Exception:
        logger.error("Cannot start browser; aborting cycle")
        return

    try:
        ok = perform_login_with_browser(driver)
        if not ok:
            logger.error("Browser login failed - aborting this cycle")
            return

        # convert cookies to requests session
        req_sess = cookies_to_requests_session(driver)

        # attempt to fetch shopping list
        data = fetch_shopping_list(req_sess)
        if data is None:
            logger.error("Fetching shopping list failed")
            return

        items = extract_items_from_data(data)
        logger.info("Found %d items on Alexa shopping list", len(items))
        if DEBUG:
            for i, it in enumerate(items):
                logger.debug("Item %d: %s", i + 1, str(it))

        # send webhook
        if WEBHOOK_URL:
            send_to_webhook(items)

        # optionally delete items after import
        if CLEAR_AFTER:
            delete_items(req_sess, items)

    except Exception as e:
        logger.exception("Unhandled exception during cycle: %s", e)

    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

# ------------------------
# Run once (run.sh controls loop)
# ------------------------
if __name__ == "__main__":
    main()
