"""
keep_alive.py
Visits the live app in a real (headless) browser -- not just a plain HTTP
request -- because Streamlit only counts a real page load/session as
"traffic" for its sleep timer, and only a real page load actually runs
app.py (which touches the Postgres database, resetting Supabase's
inactivity timer too).

If the app is already asleep, it also finds and clicks the "get this app
back up" button so the visit fully wakes it, not just pings a dead page.
"""

import os
import sys
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL")

if not APP_URL:
    print("APP_URL secret is not set -- add it in GitHub repo Settings > "
          "Secrets and variables > Actions.")
    sys.exit(1)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(APP_URL, timeout=60000)

    # Give the page a moment to render, whether it's the live app or the
    # "app is sleeping" page.
    page.wait_for_timeout(5000)

    try:
        wake_button = page.get_by_text("get this app back up", exact=False)
        if wake_button.count() > 0 and wake_button.first.is_visible():
            print("App was asleep -- clicking wake-up button.")
            wake_button.first.click()
            page.wait_for_timeout(20000)  # give it time to fully wake and load
        else:
            print("App was already awake.")
    except Exception as e:
        print(f"No wake-up button found (app likely already awake): {e}")

    browser.close()

print(f"Visited {APP_URL} successfully.")
