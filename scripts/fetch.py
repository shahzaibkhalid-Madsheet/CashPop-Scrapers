import requests
import json
import os
import sys

LOTTERY_URL   = os.environ["LOTTERY_URL"]
WEBAPP_URL    = os.environ["WEBAPP_URL"]
SHARED_SECRET = os.environ["SHARED_SECRET"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

print(f"Fetching: {LOTTERY_URL}")
resp = requests.get(LOTTERY_URL, headers=headers, timeout=15)
print(f"Status: {resp.status_code} | Length: {len(resp.text)}")

if resp.status_code != 200:
    print("❌ Fetch failed")
    sys.exit(1)

print("POSTing to Apps Script...")
payload  = { "secret": SHARED_SECRET, "html": resp.text }
post_resp = requests.post(
    WEBAPP_URL,
    data=json.dumps(payload),
    headers={"Content-Type": "application/json"},
    timeout=30
)

print(f"Response status: {post_resp.status_code}")
print(f"Response body:   {post_resp.text}")

if post_resp.status_code != 200:
    sys.exit(1)
