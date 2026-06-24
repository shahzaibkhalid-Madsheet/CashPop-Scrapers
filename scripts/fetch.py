import requests
import json
import os
import sys
import time

LOTTERY_URL   = os.environ["LOTTERY_URL"]
WEBAPP_URL    = os.environ["WEBAPP_URL"]
SHARED_SECRET = os.environ["SHARED_SECRET"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Step 1 — Fetch HTML (with retry) ─────────────────────────────────────────
print(f"Fetching: {LOTTERY_URL}")
resp = None
for attempt in range(1, 4):
    try:
        resp = requests.get(LOTTERY_URL, headers=headers, timeout=15)
        if resp.status_code == 200:
            print(f"✅ Fetch success — Status: {resp.status_code} | Length: {len(resp.text)}")
            break
        print(f"⚠️ Attempt {attempt} — HTTP {resp.status_code}, retrying in 30s...")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Attempt {attempt} — {e}, retrying in 30s...")
    if attempt < 3:
        time.sleep(30)

if not resp or resp.status_code != 200:
    print("❌ Fetch failed after 3 attempts")
    sys.exit(1)

# ── Step 2 — POST to Apps Script (with retry) ─────────────────────────────────
print("POSTing to Apps Script...")
payload = { "secret": SHARED_SECRET, "html": resp.text }

post_resp = None
for attempt in range(1, 4):
    try:
        post_resp = requests.post(
            WEBAPP_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        if post_resp.status_code == 200:
            print(f"✅ POST success — {post_resp.text}")
            break
        print(f"⚠️ POST attempt {attempt} — HTTP {post_resp.status_code}, retrying in 15s...")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ POST attempt {attempt} — {e}, retrying in 15s...")
    if attempt < 3:
        time.sleep(15)

if not post_resp or post_resp.status_code != 200:
    print("❌ POST failed after 3 attempts")
    sys.exit(1)
