# -*- coding: utf-8 -*-
"""
Alexa List Import with Selenium (Chromium headless)
- performs browser login to Amazon (email -> password -> TOTP)
- extracts cookies and uses them with requests to fetch Alexa shopping list
- sends items to configured webhook
- optionally clears items after import
Note: password and 2FA secret are masked in logs.
"""

import os
import time
import json
import logging
import requests
import pyotp
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# logging
LOG_LEVEL = logging.INFO
if os.environ.get("debug", "false").lower() == "true":
    LOG_LEVEL = logging.DEBUG

logging.basicConfig(level=LOG_LEVEL, format='[app.py] %(message)s')
logger = logging.getLogger("app")

# Config from env (run.sh exports)
AMAZON_EMAIL = os.environ.get("amazon_email", "")
AMAZON_PASSWORD = os.environ.get("amazon_password", "")
AMAZON_2FA = os.environ.get("amazon_2fa", "")
REGION = os.environ.get("region", "de")
WEBHOOK_URL = os.environ.get("webhook_url", "")
CLEAR_AFTER = os.environ.get("clear_after_import", "true").lower() == "true"
INTERVAL = int(os.environ.get("interval", "180"))
DEBUG = os.environ.get("debug", "false").lower() == "true"

SHOPPING_LIST_URL = "https://www.amazon.{}/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1".format(REGION)
DELETE_URL = "https://www.amazon.{}/alexaquantum/sp/deleteListItem".format(REGION)

# Alexa device-like headers to help acceptance
ALEXA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 9) Alexa/3.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}


def mask(s, visible=2):
    if not s:
        return ""
    s = str(s)
    if visible <= 0:
        return "*" * 4
    if len(s) <= visible:
        return "*" * len(s)
    return s[:visible] + "*" * (len(s) - visible)


def start_browser():
    """Start headless chromium and return webdriver."""
    chrome_options = Options()
    # Use new headless mode if available (Chrome 109+)
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=de-DE")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # avoid detection headers
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # point to system chromedriver (provided by apk)
    driver = webdriver.Chrome(options=chrome_options)
    # try to reduce selenium footprint
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """
    })
    return driver


def perform_browser_login(driver):
    """Perform Amazon login in the browser; returns True on success."""
    logger.info("Opening amazon homepage to fetch signin link")
    driver.get(f"https://www.amazon.{REGION}/")
    time.sleep(1.2)

    # try locate account link / signin button
    try:
        # many Amazon pages have #nav-link-accountList
        link = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.ID, "nav-link-accountList"))
        )
        href = link.get_attribute("href")
        logger.debug("Found nav-link-accountList href: %s", href)
        signin_url = href
    except Exception:
        # fallback: look for any signin link
        tags = driver.find_elements(By.TAG_NAME, "a")
        signin_url = None
        for a in tags:
            h = a.get_attribute("href")
            if h and ("/ap/signin" in h or "nav_ya_signin" in h):
                signin_url = h
                break

    if not signin_url:
        logger.error("Amazon login link not found in page")
        return False

    logger.debug("Navigating to signin URL")
    driver.get(signin_url)
    # wait for page
    time.sleep(1.0)

    # Enter email (some flows are two-step)
    try:
        # typical id is ap_email
        email_input = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.ID, "ap_email"))
        )
        email_input.clear()
        email_input.send_keys(AMAZON_EMAIL)
        # press continue if present
        try:
            cont = driver.find_element(By.ID, "continue")
            cont.click()
        except Exception:
            # sometimes submit via form
            email_input.submit()
        logger.debug("Email submitted (masked): %s", mask(AMAZON_EMAIL))
    except Exception:
        # maybe email field not shown, proceed
        logger.debug("Email field not found; continuing to password step")

    # Wait a bit then find password
    time.sleep(1.0)
    try:
        pass_input = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.ID, "ap_password"))
        )
        pass_input.clear()
        pass_input.send_keys(AMAZON_PASSWORD)
        # submit form
        try:
            signbtn = driver.find_element(By.ID, "signInSubmit")
            signbtn.click()
        except Exception:
            pass_input.submit()
        logger.debug("Password submitted (masked)")
    except Exception as exc:
        logger.error("Password field not found or error: %s", exc)
        # sometimes the site asks additional steps; still continue

    # wait for potential MFA page or account landing
    time.sleep(2.5)

    # Detect MFA prompt (otp input)
    try:
        otp_input = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.NAME, "otpCode"))
        )
        # generate TOTP
        try:
            code = pyotp.TOTP(AMAZON_2FA).now()
        except Exception as e:
            logger.error("Failed generating TOTP: %s", e)
            return False
        otp_input.clear()
        otp_input.send_keys(code)
        # submit MFA form: look for Continue or Verify button
        try:
            submit_btn = driver.find_element(By.XPATH, "//input[@type='submit' or @id='auth-signin-button' or @id='a-autoid-0']")
            submit_btn.click()
        except Exception:
            otp_input.submit()
        logger.debug("Submitted MFA (masked): %s", mask(code, visible=0))
        time.sleep(2.0)
    except Exception:
        # no otp prompt found — maybe MFA not required
        logger.debug("No MFA prompt detected")

    # Final check: try to open account page
    try:
        driver.get(f"https://www.amazon.{REGION}/gp/your-account/home")
        time.sleep(1.0)
        if "Anmelden" in driver.title or "Sign-In" in driver.title or "Einloggen" in driver.title:
            logger.error("Post-login check shows still on signin page")
            return False
    except Exception:
        logger.debug("Could not access account page to validate login")

    # if session cookies exist, assume logged in
    cookies = driver.get_cookies()
    cookie_names = [c['name'] for c in cookies]
    logger.debug("Browser cookies: %s", cookie_names)
    if not cookies:
        logger.error("No cookies set by browser after login")
        return False

    # good: return True and let caller extract cookies
    return True


def cookies_to_requests_session(driver):
    """Convert selenium cookies to requests.Session() with cookies and headers."""
    s = requests.Session()
    # add Alexa headers
    s.headers.update(ALEXA_HEADERS)
    for c in driver.get_cookies():
        s.cookies.set(c['name'], c['value'], domain=c.get('domain', None))
    return s


def fetch_shopping_list_with_session(session):
    """Try to fetch shopping list JSON by requests using given session."""
    try:
        r = session.get(SHOPPING_LIST_URL, timeout=20, allow_redirects=True)
    except Exception as e:
        logger.error("Network error fetching shopping list: %s", e)
        return None

    # If redirected to sign-in, session not accepted for Alexa API
    if "/ap/signin" in r.url:
        logger.error("Alexa shoppinglist request was redirected to signin: session not accepted")
        return None

    # Try JSON
    try:
        data = r.json()
        return data
    except Exception:
        # fallback: try to find embedded JSON in page
        text = r.text or ""
        # attempt to find items array
        import re
        m = re.search(r'("items"\s*:\s*\[.*?\])', text, re.S)
        if m:
            js = "{" + m.group(1) + "}"
            try:
                parsed = json.loads(js)
                return parsed
            except Exception:
                pass

    logger.error("Could not parse shopping list response")
    return None


def send_to_webhook(items):
    if not WEBHOOK_URL:
        logger.info("No webhook configured; skipping send")
        return
    payload = {"items": items, "count": len(items)}
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        logger.info("Webhook response code: %s", r.status_code)
    except Exception as e:
        logger.error("Webhook error: %s", e)


def delete_items_after_import(session, items):
    if not items:
        return
    for it in items:
        if isinstance(it, dict):
            item_id = it.get("itemId") or it.get("id") or it.get("item_id")
        else:
            item_id = None
        if not item_id:
            logger.debug("Skipping delete for item missing id: %s", it)
            continue
        try:
            session.post(DELETE_URL, json={"itemId": item_id}, timeout=10)
            logger.debug("Requested deletion for item id: %s", item_id)
        except Exception:
            logger.debug("Failed to send delete for: %s", item_id)


def main():
    logger.info("Loaded config (sanitized): email=%s, password=%s, 2fa=%s, region=%s, interval=%s, clear_after_import=%s, webhook=%s",
                mask(AMAZON_EMAIL), "****", mask(AMAZON_2FA, visible=2), REGION, INTERVAL, CLEAR_AFTER, bool(WEBHOOK_URL))

    # Start browser and login
    try:
        driver = start_browser()
    except Exception as e:
        logger.error("Failed to start browser: %s", e)
        return

    try:
        ok = perform_browser_login(driver)
        if not ok:
            logger.error("Browser login failed - aborting this cycle")
            driver.quit()
            return

        # Convert cookies to requests session
        req_sess = cookies_to_requests_session(driver)
        driver.quit()

        # Try to fetch shopping list by requests using cookies and Alexa headers
        data = fetch_shopping_list_with_session(req_sess)
        if not data:
            logger.error("Fetching shopping list failed")
            return

        # Normalize items list
        items = []
        # many responses include top-level 'items' or nested 'lists'
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                items = data["items"]
            elif "lists" in data and isinstance(data["lists"], list) and len(data["lists"]) > 0:
                # structure may be lists -> [ { "items": [...] } ]
                first = data["lists"][0]
                if isinstance(first, dict) and "items" in first:
                    items = first.get("items", [])
        # else attempt to coerce
        if not isinstance(items, list):
            logger.error("Items payload not a list")
            return

        logger.info("Found %d items", len(items))
        if DEBUG:
            for it in items:
                logger.debug("Item: %s", str(it))

        # Send to webhook
        if WEBHOOK_URL:
            send_to_webhook(items)

        # Optionally clear items
        if CLEAR_AFTER:
            delete_items_after_import(req_sess, items)

    except Exception as e:
        logger.exception("Unhandled exception during import: %s", e)
        try:
            driver.quit()
        except Exception:
            pass
        return


if __name__ == "__main__":
    main()
