# -*- coding: utf-8 -*-
"""
Complete app.py for Alexa List Import Add-on (Selenium-only approach)
- Uses headless Chromium (Selenium) to perform the full flow:
  1) Browser login (2025-compatible / openid signin URL)
  2) Optional TOTP (2FA) submission
  3) Navigate to Alexa shopping list page and extract items
  4) Send items to configured webhook
  5) Optionally clear items from Alexa (via browser UI)
- Configuration is read from environment variables (exported by run.sh).
- Sensitive values are masked in logs.
- Designed to be run repeatedly by run.sh (run.sh controls the loop/timing).
"""

import os
import time
import json
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Optional

import pyotp
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------------------------
# Configuration & logging
# -------------------------
DEBUG = os.environ.get("debug", "false").lower() == "true"
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(level=LOG_LEVEL, format="[app.py] %(message)s")
logger = logging.getLogger("alexa_list_import")

AMAZON_EMAIL = os.environ.get("amazon_email", "").strip()
AMAZON_PASSWORD = os.environ.get("amazon_password", "").strip()
AMAZON_2FA = os.environ.get("amazon_2fa", "").strip()  # TOTP seed (base32)
REGION = os.environ.get("region", "de").strip()
WEBHOOK_URL = os.environ.get("webhook_url", "").strip()
CLEAR_AFTER = os.environ.get("clear_after_import", "true").lower() == "true"
INTERVAL = int(os.environ.get("interval", "180"))
# Alexa shopping list URL (as requested)
SHOPPING_LIST_URL = f"https://www.amazon.{REGION}/alexaquantum/sp/alexaShoppingList?ref_=list_d_wl_ys_list_1"

# 2025-compatible signin URL (OpenID query params)
AMAZON_LOGIN_URL = (
    f"https://www.amazon.{REGION}/ap/signin?"
    "openid.pape.max_auth_age=0&"
    "openid.return_to=https%3A%2F%2Fwww.amazon.{region}%2F%3Fref_%3Dnav_signin&"
    "openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&"
    "openid.assoc_handle=deflex&"
    "openid.mode=checkid_setup&"
    "openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&"
    "openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
).replace("{region}", REGION)

# timeouts
SHORT_WAIT = 5
MEDIUM_WAIT = 10
LONG_WAIT = 25

# -------------------------
# Helper functions
# -------------------------
def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def mask(value: str, visible: int = 2) -> str:
    if not value:
        return ""
    v = str(value)
    if visible <= 0:
        return "*" * 4
    if len(v) <= visible:
        return "*" * len(v)
    return v[:visible] + "*" * (len(v) - visible)


def safe_log_config() -> None:
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


# -------------------------
# Selenium: start/stop driver
# -------------------------
def start_chrome_driver() -> webdriver.Chrome:
    """
    Start a headless Chromium webdriver.
    Assumes chromium & chromedriver are available in the image.
    """
    chrome_options = Options()
    # Use the newer headless mode when available
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=de-DE")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # instantiate driver
    try:
        driver = webdriver.Chrome(options=chrome_options)
        # reduce selenium fingerprint
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            })
        except Exception:
            # not fatal
            pass
        return driver
    except WebDriverException as e:
        logger.error("Failed to start Chrome WebDriver: %s", e)
        raise


def safe_quit(driver: Optional[webdriver.Chrome]) -> None:
    try:
        if driver:
            driver.quit()
    except Exception:
        pass


# -------------------------
# Amazon login (Selenium)
# -------------------------
def browser_login(driver: webdriver.Chrome) -> bool:
    """
    Perform login using the 2025-compatible signin URL.
    Returns True on success (session cookies present), False otherwise.
    """
    logger.info("Starting Amazon login sequence at %s", now_ts())
    logger.debug("Navigating to signin URL: %s", AMAZON_LOGIN_URL)

    try:
        driver.get(AMAZON_LOGIN_URL)
    except Exception as e:
        logger.error("Failed to open signin URL: %s", e)
        return False

    time.sleep(1.2)

    # email step (some flows show password directly)
    try:
        email_input = WebDriverWait(driver, SHORT_WAIT).until(
            EC.presence_of_element_located((By.ID, "ap_email"))
        )
        email_input.clear()
        email_input.send_keys(AMAZON_EMAIL)
        # click continue if present
        try:
            cont = driver.find_element(By.ID, "continue")
            cont.click()
            logger.debug("Clicked continue after email")
        except Exception:
            try:
                email_input.submit()
            except Exception:
                pass
        logger.debug("Email used: %s", mask(AMAZON_EMAIL))
    except TimeoutException:
        logger.debug("Email input not found; continuing (maybe single-step flow)")

    time.sleep(0.8)

    # password step
    try:
        pwd_input = WebDriverWait(driver, SHORT_WAIT).until(
            EC.presence_of_element_located((By.ID, "ap_password"))
        )
        pwd_input.clear()
        pwd_input.send_keys(AMAZON_PASSWORD)
        # submit
        try:
            sign_btn = driver.find_element(By.ID, "signInSubmit")
            sign_btn.click()
        except Exception:
            try:
                pwd_input.submit()
            except Exception:
                pass
        logger.debug("Password submitted (masked)")
    except TimeoutException:
        logger.error("Password input not found on signin page")
        # proceed; maybe already logged in (rare)
        pass

    time.sleep(1.8)

    # handle possible MFA (TOTP)
    try:
        # common element ids/names for Amazon MFA
        otp_el = None
        try:
            otp_el = driver.find_element(By.ID, "auth-mfa-otpcode")
        except NoSuchElementException:
            try:
                otp_el = driver.find_element(By.NAME, "otpCode")
            except NoSuchElementException:
                otp_el = None

        if otp_el is not None:
            if not AMAZON_2FA:
                logger.error("MFA required but no TOTP seed provided")
                return False
            # generate TOTP
            try:
                code = pyotp.TOTP(AMAZON_2FA).now()
            except Exception as e:
                logger.error("Failed to generate TOTP code: %s", e)
                return False
            otp_el.clear()
            otp_el.send_keys(code)
            # submit MFA
            try:
                sub = driver.find_element(By.ID, "auth-signin-button")
                sub.click()
            except Exception:
                try:
                    otp_el.submit()
                except Exception:
                    pass
            logger.debug("Submitted TOTP (masked): %s", mask(code, visible=0))
            time.sleep(2.0)
        else:
            logger.debug("No TOTP prompt detected")
    except Exception as e:
        logger.debug("MFA step raised: %s", e)

    # final check: look for session cookies
    cookies = driver.get_cookies()
    names = [c.get("name") for c in cookies if c.get("name")]
    logger.debug("Browser cookies after login: %s", names)

    # check for expected session cookie names
    expected_tokens = {"session-id", "session-token", "ubid-main", "ubid-acbde", "at-main"}
    if any(tok in names for tok in expected_tokens):
        logger.info("Detected session cookies, assuming login success")
        return True

    # fallback: if any cookie present, try
    if cookies:
        logger.info("Cookies present after login (no obvious session token names) — proceeding")
        return True

    logger.error("No cookies set after login; login appears to have failed")
    return False


# -------------------------
# Get shopping list via browser
# -------------------------
def fetch_shopping_list_via_browser(driver: webdriver.Chrome) -> Optional[List[Dict]]:
    """
    Navigates to the Alexa shopping list page in the same browser session and extracts items.
    Returns a list of items (dicts) or None on failure.
    """
    logger.info("Fetching shopping list from: %s", SHOPPING_LIST_URL)
    try:
        driver.get(SHOPPING_LIST_URL)
    except Exception as e:
        logger.error("Failed to load shopping list URL: %s", e)
        return None

    # allow redirects & page load
    time.sleep(2.0)

    # If Amazon redirects to signin, abort
    current_url = driver.current_url or ""
    if "/ap/signin" in current_url:
        logger.error("Alexa shopping list request redirected to signin (session not accepted)")
        return None

    # page source
    html = driver.page_source or ""
    # attempt 1: try to extract JSON embedded or API response via network
    # attempt to find direct JSON in page
    try:
        # look for obvious JSON structures
        import re
        # try "lists" object
        m = re.search(r'("lists"\s*:\s*\[.*?\])', html, re.S)
        if m:
            txt = "{" + m.group(1) + "}"
            try:
                parsed = json.loads(txt)
                # items likely at parsed['lists'][0]['items']
                try:
                    items = parsed.get("lists", [])[0].get("items", [])
                    logger.debug("Found items via embedded JSON (lists). Count=%d", len(items))
                    return items
                except Exception:
                    pass
            except Exception:
                pass

        # try "items" directly
        m2 = re.search(r'("items"\s*:\s*\[.*?\])', html, re.S)
        if m2:
            try:
                txt2 = "{" + m2.group(1) + "}"
                parsed2 = json.loads(txt2)
                items = parsed2.get("items", [])
                logger.debug("Found items via embedded JSON (items). Count=%d", len(items))
                return items
            except Exception:
                pass
    except Exception as e:
        logger.debug("Error while trying to parse embedded JSON: %s", e)

    # attempt 2: parse HTML list entries (works with typical Alexa shopping list UI)
    try:
        soup = BeautifulSoup(html, "html.parser")
        # common container classes/ids (attempts)
        candidates = []
        # find list item elements that look like shopping list entries
        # heuristics: elements with data-item-id or role=listitem and text content
        for el in soup.find_all(attrs={"data-item-id": True}):
            candidates.append(el)

        if not candidates:
            # fallback: find role=listitem and text
            for el in soup.find_all(attrs={"role": "listitem"}):
                # skip nav items by checking for long text
                text = el.get_text(" ", strip=True)
                if text and len(text) < 200:
                    candidates.append(el)

        items = []
        for el in candidates:
            text = el.get_text(" ", strip=True)
            # try to extract an id
            item_id = el.get("data-item-id", None)
            # build item dict
            it = {"value": text}
            if item_id:
                it["itemId"] = item_id
            items.append(it)

        if items:
            logger.debug("Found %d items by HTML parsing", len(items))
            return items
    except Exception as e:
        logger.debug("HTML parsing step failed: %s", e)

    logger.error("Could not extract shopping list items from page")
    return None


# -------------------------
# Delete items (via browser UI)
# -------------------------
def clear_shopping_list_via_browser(driver: webdriver.Chrome, items: List[Dict]) -> None:
    """
    Attempt to delete items via browser UI.
    This uses best-effort heuristics: find delete buttons near items and click them.
    """
    if not items:
        logger.debug("No items to clear")
        return

    logger.info("Attempting to clear %d items from Alexa list", len(items))

    # Reload shopping list to ensure DOM elements are fresh
    try:
        driver.get(SHOPPING_LIST_URL)
    except Exception as e:
        logger.error("Failed to reload shopping list page for clearing: %s", e)
        return

    time.sleep(1.5)

    # Try per-item deletion by matching visible text
    page_html = driver.page_source
    soup = BeautifulSoup(page_html, "html.parser")

    # Build map of visible text -> list of candidate element ids or indices
    visible_map = {}
    for el in soup.find_all(attrs={"data-item-id": True}):
        txt = el.get_text(" ", strip=True)
        idv = el.get("data-item-id")
        if txt:
            visible_map.setdefault(txt, []).append(idv)

    # For each item we found earlier attempt to click delete for matching text
    for it in items:
        visible_text = it.get("value") or ""
        item_id = it.get("itemId")
        matched = False

        # Preferred: match by itemId if available
        if item_id:
            # attempt to find element by data-item-id attribute using Selenium
            try:
                sel = driver.find_element(By.CSS_SELECTOR, f'[data-item-id="{item_id}"]')
                # find a delete button within or nearby
                try:
                    # common patterns: button with aria-label containing 'Delete' or a checkbox then delete
                    btn = sel.find_element(By.XPATH, ".//button[contains(translate(., 'DELETE', 'delete'), 'delete') or contains(@aria-label,'Löschen') or contains(@aria-label,'Delete') or contains(@class,'delete')]")
                    btn.click()
                    logger.debug("Clicked delete button for itemId %s", item_id)
                    matched = True
                    time.sleep(0.5)
                except Exception:
                    # try context menu / overflow menu then delete
                    try:
                        menu = sel.find_element(By.XPATH, ".//button[contains(@class,'menu') or contains(@aria-label,'Mehr')]")
                        menu.click()
                        time.sleep(0.3)
                        # find delete in menu
                        try:
                            delete_item = driver.find_element(By.XPATH, "//a[contains(., 'Delete') or contains(., 'Löschen') or contains(., 'Remove')]")
                            delete_item.click()
                            logger.debug("Clicked delete via menu for itemId %s", item_id)
                            matched = True
                            time.sleep(0.5)
                        except Exception:
                            pass
                    except Exception:
                        pass
            except NoSuchElementException:
                pass
            except Exception:
                logger.debug("Error when trying to delete by itemId: %s", traceback.format_exc())

        # Fallback: match by visible text (exact or contains)
        if not matched and visible_text:
            # try exact matches from visible_map
            keys = [k for k in visible_map.keys() if k.strip() == visible_text.strip()]
            if not keys:
                # try contains
                keys = [k for k in visible_map.keys() if visible_text.strip() in k or k in visible_text]
            if keys:
                # try to click delete for first matched id
                candidate_id = visible_map[keys[0]][0] if visible_map[keys[0]] else None
                if candidate_id:
                    try:
                        sel = driver.find_element(By.CSS_SELECTOR, f'[data-item-id="{candidate_id}"]')
                        try:
                            btn = sel.find_element(By.XPATH, ".//button[contains(translate(., 'DELETE', 'delete'), 'delete') or contains(@aria-label,'Löschen') or contains(@aria-label,'Delete') or contains(@class,'delete')]")
                            btn.click()
                            logger.debug("Clicked delete button for matched visible text (candidate id=%s)", candidate_id)
                            matched = True
                            time.sleep(0.5)
                        except Exception:
                            pass
                    except Exception:
                        pass

        if not matched:
            logger.debug("Could not find delete UI for item: %s (id=%s)", visible_text, item_id)

    # small wait after deletions
    time.sleep(1.0)
    logger.info("Clear-after-import attempt finished (best-effort)")


# -------------------------
# Webhook posting
# -------------------------
def send_to_webhook(items: List[Dict]) -> None:
    if not WEBHOOK_URL:
        logger.info("No webhook configured, skipping send")
        return

    payload = {"items": items, "count": len(items), "timestamp": now_ts()}
    try:
        import requests  # local import to avoid top-level dependency if unused
        r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        logger.info("Webhook response: %s", r.status_code)
    except Exception as e:
        logger.error("Webhook post failed: %s", e)


# -------------------------
# Main single-run function
# -------------------------
def single_run_cycle() -> None:
    safe_log_config()
    logger.info("Polling at %s", now_ts())

    driver = None
    try:
        driver = start_chrome_driver()
    except Exception:
        logger.error("Could not start browser driver; aborting cycle")
        return

    try:
        ok = browser_login(driver)
        if not ok:
            logger.error("Browser login failed - aborting this cycle")
            return

        # fetch shopping list items via same browser session
        items = fetch_shopping_list_via_browser(driver)
        if items is None:
            logger.error("Fetching shopping list failed")
            return

        # Normalize items: ensure list of dicts with at least 'value'
        normalized = []
        for it in items:
            if isinstance(it, dict):
                # some responses use 'value' or 'text' or nested structures
                value = it.get("value") or it.get("text") or it.get("name") or str(it)
                normalized.append({"value": value, "raw": it})
            else:
                normalized.append({"value": str(it), "raw": it})

        logger.info("Found %d items", len(normalized))
        if DEBUG:
            for idx, it in enumerate(normalized, start=1):
                logger.debug("Item %d: %s", idx, it.get("value"))

        # send webhook
        if WEBHOOK_URL:
            send_to_webhook(normalized)

        # optionally clear
        if CLEAR_AFTER:
            try:
                clear_shopping_list_via_browser(driver, items if isinstance(items, list) else [])
            except Exception as e:
                logger.debug("Clear-after-import raised exception: %s", e)

    except Exception as e:
        logger.exception("Unhandled exception during cycle: %s", e)
    finally:
        safe_quit(driver)


# -------------------------
# Entrypoint (run once; run.sh controls loop)
# -------------------------
if __name__ == "__main__":
    single_run_cycle()
