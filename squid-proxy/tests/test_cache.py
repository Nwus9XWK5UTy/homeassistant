
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

PROXY_IP = os.getenv("PROXY_IP", "127.0.0.1")
PROXY_PORT = 3128  # HTTP Proxy Port
PROXY_USER = os.getenv("PROXY_USER", "squidadmin")
PROXY_PASS = os.getenv("PROXY_PASSWORD", "password")

proxies = {
    "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_IP}:{PROXY_PORT}",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_IP}:{PROXY_PORT}",
}

# Use a cacheable HTTP target (httpbin)
TARGET_URL = "http://httpbin.org/cache/60" # Cache for 60 seconds

print(f"Testing caching via proxy: {proxies['http']} -> {TARGET_URL}")
print("-" * 50)

def make_request(i):
    start = time.time()
    try:
        resp = requests.get(TARGET_URL, proxies=proxies, timeout=10)
        elapsed = time.time() - start
        print(f"Req #{i}: Status={resp.status_code}, Time={elapsed:.4f}s")
        # Check specific headers if Squid is configured to show them (it might not be due to stealth)
        # But time difference is key. A cache HIT is nearly instant (<0.1s). A MISS takes time (>0.5s).
        return elapsed
    except Exception as e:
        print(f"Req #{i}: Failed - {e}")
        return None

# 1. First Request (Should be MISS)
print("1. Sending first request (Expect MISS)...")
time_miss = make_request(1)

time.sleep(1)

# 2. Second Request (Should be HIT)
print("2. Sending second request (Expect HIT)...")
time_hit = make_request(2)

print("-" * 50)
if time_miss and time_hit:
    print(f"Time Diff: {time_miss:.4f}s (Miss) vs {time_hit:.4f}s (Hit)")
    if time_hit < time_miss * 0.5: # 50% faster is a strong indicator
        print("SUCCESS: Cache appears operational (Significant speedup detected).")
    else:
        print("WARNING: No significant speedup. Cache missed or network jitter?")
else:
    print("Test failed due to connection errors.")
