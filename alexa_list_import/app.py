import requests
import argparse
import time
import json
import os

SESSION_FILE = "/data/amazon_session.json"


def save_session(cookies):
    with open(SESSION_FILE, "w") as f:
        json.dump(requests.utils.dict_from_cookiejar(cookies), f)


def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return requests.utils.cookiejar_from_dict(json.load(f))
    return None


def amazon_login(email, password, otp, region):
    print("Logging in to Amazon...")
    s = requests.Session()

    login_data = {
        "email": email,
        "password": password,
    }

    # Optional 2FA
    if otp:
        login_data["otp"] = otp

    url = f"https://www.amazon.{region}/ap/signin"
    r = s.post(url, data=login_data)

    if r.status_code != 200:
        print("Login failed:", r.status_code)
        return None

    save_session(s.cookies)
    print("Amazon login successful.")
    return s


def get_session(region):
    cookies = load_session()
    if not cookies:
        return None
    s = requests.Session()
    s.cookies = cookies
    return s


def get_shopping_list(s, region):
    url = f"https://www.amazon.{region}/alist/print-view/shopping"
    r = s.get(url)

    if r.status_code != 200:
        print("Error loading list:", r.status_code)
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    items = [i.text.strip() for i in soup.select(".a-list-item")]
    return items


def delete_items(s, region):
    # This is a mock delete since Amazon’s delete endpoint differs per region.
    # Adjust if needed.
    print("Clearing list on Amazon (simulated)...")
    return True


def send_webhook(url, items):
    if not url:
        return
    print("Sending webhook...")
    requests.post(url, json={"items": items})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument("--twofa")
    parser.add_argument("--region")
    parser.add_argument("--webhook")
    parser.add_argument("--interval", type=int)
    parser.add_argument("--clear")
    args = parser.parse_args()

    session = get_session(args.region)

    if not session:
        session = amazon_login(args.email, args.password, args.twofa, args.region)

    while True:
        print("Polling Alexa list...")

        items = get_shopping_list(session, args.region)

        print("Found:", items)

        if items:
            send_webhook(args.webhook, items)

            if args.clear.lower() == "true":
                delete_items(session, args.region)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
