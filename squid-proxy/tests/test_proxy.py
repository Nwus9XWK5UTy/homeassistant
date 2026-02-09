import requests
import warnings
import os
import json
from dotenv import load_dotenv
from urllib3.exceptions import InsecureRequestWarning

# warnings.simplefilter('ignore', InsecureRequestWarning)

# Load credentials from .env file (required)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Get credentials from environment (no defaults for security)
PROXY_USER = os.getenv('PROXY_USER')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')
PROXY_URL = os.getenv('PROXY_URL')

if not PROXY_USER or not PROXY_PASSWORD or not PROXY_URL:
    raise ValueError(
        "Missing required environment variables!\n"
        "Please create a .env file in the tests/ directory with:\n"
        "  PROXY_USER=your_username\n"
        "  PROXY_PASSWORD=your_password\n"
        "  PROXY_URL=https://your_domain:port\n"
    )

try:
    from curl_cffi.requests import AsyncSession
    from curl_cffi import CurlOpt
except ImportError:
    AsyncSession = None
    CurlOpt = None

async def test_url(url, label):
    # Authenticated Secure Proxy URL from environment
    proxy_url = f"{PROXY_URL.rstrip('/')}"
    if '@' not in proxy_url:
        # Add credentials if not already in URL
        proxy_url = proxy_url.replace('://', f'://{PROXY_USER}:{PROXY_PASSWORD}@')
    
    print(f"\n--- Testing {label}: {url} ---")
    
    try:
        if AsyncSession:
            print("Using curl_cffi.requests.AsyncSession (impersonate='chrome120')")
            
            # Enable SSL verification for Let's Encrypt
            verify_ssl = True
            c_opts = {
                CurlOpt.PROXY_SSL_VERIFYPEER: 1,
                CurlOpt.PROXY_SSL_VERIFYHOST: 2
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
                "Connection": "close",
            }

            async with AsyncSession(
                impersonate="chrome120",
                proxy=proxy_url,
                verify=verify_ssl,
                curl_options=c_opts,
                headers=headers,
                timeout=20
            ) as session:
                response = await session.get(url)
        else:
            print("Using standard requests (no TLS impersonation)")
            proxies = {"http": proxy_url, "https": proxy_url}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
                "Connection": "close",
            }
            response = requests.get(
                url, 
                proxies=proxies, 
                headers=headers, 
                verify=True
            )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Response Body (first 200 chars): {response.text[:200]}")
        else:
            print(f"Error Status: {response.status_code}")
            print(f"Server Header: {response.headers.get('Server')}")
            if 'cloudflare' in str(response.headers.get('Server')).lower():
                print("!!! Blocked by Cloudflare !!!")
        
        # Keep connection open for 2 seconds to be visible in dashboard
        import asyncio
        await asyncio.sleep(2)

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("Starting 10 concurrent connections to generate traffic...")
        
        tasks = []
        for i in range(10):
            # Alternate targets
            url = "https://www.google.com" if i % 2 == 0 else "https://www.rewe.de/"
            label = f"Connection #{i+1}"
            tasks.append(test_url(url, label))
            
        await asyncio.gather(*tasks)
        print("\nAll connections completed!")

    asyncio.run(main())
