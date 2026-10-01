import requests
import json
import os
import sys
import time
import random
import socket
from urllib.parse import urlparse

LOTTERY_URL   = os.environ["LOTTERY_URL"]
WEBAPP_URL    = os.environ["WEBAPP_URL"]
SHARED_SECRET = os.environ["SHARED_SECRET"]
PROXY_URL     = os.environ.get("PROXY_URL", "").strip()   # e.g. http://user:pass@host:port (optional)

TIMEOUT = (8, 20)          # (connect, read) seconds — fail fast on dropped connections
DIRECT_ATTEMPTS = 2
PROXY_ATTEMPTS  = 3

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def scrub(text):
    """Never print proxy credentials in logs."""
    return str(text).replace(PROXY_URL, "***") if PROXY_URL else str(text)


def log_diagnostics():
    host = urlparse(LOTTERY_URL).hostname
    try:
        runner_ip = requests.get("https://api.ipify.org", timeout=5).text
    except Exception:
        runner_ip = "unknown"
    try:
        resolved = sorted({r[4][0] for r in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})
    except Exception as e:
        resolved = [f"DNS error: {e}"]
    print(f"🔎 Runner IP: {runner_ip} | {host} resolves to: {resolved}")


def looks_valid(text):
    # Guards against block/challenge pages that still return HTTP 200
    return len(text) > 5000 and "cash pop" in text.lower()


def try_fetch(label, proxies, attempts):
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(LOTTERY_URL, headers=headers, timeout=TIMEOUT, proxies=proxies)
            if r.status_code == 200 and looks_valid(r.text):
                print(f"✅ [{label}] success — Status: {r.status_code} | Length: {len(r.text)}")
                return r
            print(
                f"⚠️ [{label}] attempt {attempt} — HTTP {r.status_code} | "
                f"server={r.headers.get('server')} cf-ray={r.headers.get('cf-ray')} | "
                f"body: {r.text[:200]!r}"
            )
        except requests.exceptions.RequestException as e:
            print(f"⚠️ [{label}] attempt {attempt} — {type(e).__name__}: {scrub(e)[:200]}")
        if attempt < attempts:
            time.sleep(random.uniform(3, 6))
    return None


# ── Step 1 — Fetch HTML: direct first, then residential proxy ────────────────
print(f"Fetching: {LOTTERY_URL}")
log_diagnostics()

resp = try_fetch("direct", None, DIRECT_ATTEMPTS)

if resp is None and PROXY_URL:
    print("↪️ Direct failed — falling back to proxy")
    resp = try_fetch("proxy", {"http": PROXY_URL, "https": PROXY_URL}, PROXY_ATTEMPTS)
elif resp is None:
    print("↪️ Direct failed and no PROXY_URL configured")

if resp is None:
    print("❌ Fetch failed on all paths")
    sys.exit(1)

# ── Step 2 — POST to Apps Script (with retry) — unchanged ────────────────────
print("POSTing to Apps Script...")
payload = {"secret": SHARED_SECRET, "html": resp.text}

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
            print(f"POST response — {post_resp.text}")
            try:
                result = post_resp.json()
            except ValueError:
                result = {}
            if result.get("status") != "ok":
                print("❌ Apps Script reported failure")
                sys.exit(1)
            print("✅ POST success")
            break
        print(f"⚠️ POST attempt {attempt} — HTTP {post_resp.status_code}, retrying in 15s...")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ POST attempt {attempt} — {e}, retrying in 15s...")
    if attempt < 3:
        time.sleep(15)

if not post_resp or post_resp.status_code != 200:
    print("❌ POST failed after 3 attempts")
    sys.exit(1)
