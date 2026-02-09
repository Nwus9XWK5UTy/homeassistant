# Full Documentation: Squid Proxy v1.0.3

This add-on provides a robust Squid-based proxy server tailored for the Home Assistant ecosystem. It focuses on **Stealth**, **Security**, and **Visibility**.

## 1. Core Functionality

### Stealth Mode
The proxy is pre-configured to be as "silent" as possible. It:
*   Strips `X-Forwarded-For`, `Via`, and `Proxy-Connection` headers.
*   Disables `Forwarded-For` logic.
*   Suppresses `Cache-Control` and `Proxy-Authorization` headers from reaching the destination server.
*   Uses modern TLS profiles to blend in with standard browser traffic.

### Zero Caching
Unlike standard Squid setups, object caching is **explicitly disabled**. 
*   **Reason**: Maximum privacy and prevention of "stale content" errors during automation/scraping.
*   **System Benefit**: Prevents the add-on from consuming significant disk space or causing excessive writes to SD cards/SSDs.

### Security Architecture (Minimal Access Principle)
This add-on follows the **principle of least privilege** - it runs with only the bare minimum permissions required for proxy functionality:

**What the proxy HAS access to:**
*   ✅ Network connectivity (required for proxying)
*   ✅ Persistent storage in `/data` (for SSL certificates only)
*   ✅ Tmpfs volatile storage (for configs, logs, cache)
*   ✅ AppArmor mandatory access control

**What the proxy does NOT have access to:**
*   ❌ Host namespaces (IPC, D-Bus, PID) - Complete container isolation
*   ❌ Hardware devices (GPIO, USB, UART, video, audio) - No physical device access
*   ❌ Kernel modules - Cannot load system modules
*   ❌ Stdin - No interactive access
*   ❌ Legacy APIs - Modern security only

This minimal access approach ensures that even if the proxy is compromised, the attacker cannot access hardware, host processes, or system APIs.

---

## 2. Configuration Guide

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `enable_http` | `bool` | `true` | Enables Port 3128 for standard proxying. |
| `enable_https` | `bool` | `false` | Enables Port 3129 for Secure Proxying. |
| `proxy_user` | `str` | `squidadmin` | Username (Alphanumeric, 8-32 chars). |
| `proxy_password` | `str` | - | Password (Minimum 8 chars). |
| `proxy_domain` | `str` | - | External domain (e.g., `proxy.example.com`). Must be a valid FQDN. Required for HTTPS. |
| `use_letsencrypt` | `bool` | `false` | Enable automated SSL via Let's Encrypt. |
| `letsencrypt_email` | `str` | - | Email for renewal notifications. |
| `allow_all` | `bool` | `true` | If `true`, any IP can connect (still requires auth). |
| `allowed_networks` | `list` | `[...]` | CIDR ranges (e.g. `192.168.1.0/24`) allowed if `allow_all` is false. |
| `debug` | `bool` | `false` | Enables verbose Squid logging in the HA supervisor. |

---

## 3. SSL/TLS Setup (Secure Proxy)

When `enable_https` is true, you can connect to the proxy using an encrypted tunnel.

### Mode A: Let's Encrypt (Recommended)
1.  Set `use_letsencrypt: true`.
2.  Set `letsencrypt_email` to your email.
3.  Set `proxy_domain` to your public domain.
4.  **Critical**: Ensure **Port 80** is forwarded on your router to your Home Assistant IP. The add-on uses standard HTTP-01 challenges to verify ownership.

### Mode B: Self-Signed (Legacy/Local)
If Let's Encrypt is off, a self-signed certificate is generated. Most clients (like `curl` or Python `requests`) will require `verify=False` to connect.

---

## 4. Monitoring Dashboard

The add-on includes an integrated real-time dashboard accessible via the **Sidebar** (if enabled) or the **Open Web UI** button.

### Key Metrics
*   **Active Connections Graph**: Displays a real-time history of traffic.
*   **Protocol Split**: Separate lines for **HTTP (3128)** and **HTTPS (3129)** so you can see exactly which interface is being used.
*   **Burst Capture**: The monitor tracks `TIME_WAIT` states, ensuring that even very fast requests (under 1 second) are accurately reflected as spikes on the graph.
*   **Connected Source IPs**: A live list of client IPs currently using the proxy, separated by port.

---

## 5. Developer Examples

### Python (`requests`) - Standard HTTP Proxy (Port 3128)
```python
import requests

# Standard HTTP proxy on port 3128
proxies = {
    "http": "http://user:password@YOUR_HA_IP:3128",
    "https": "http://user:password@YOUR_HA_IP:3128"
}

# Proxying to a destination
r = requests.get("https://httpbin.org/ip", proxies=proxies)
print(r.json())
```

### Python (`curl_cffi`) - Secure HTTPS Proxy (Port 3129)
Used for bypassing modern bot protections (Cloudflare, etc.) using encrypted proxy connection.
```python
from curl_cffi.requests import Session

# Secure HTTPS proxy on port 3129 (requires enable_https: true)
# Note: Use 'https://' protocol for the proxy URL itself
proxy = "https://user:password@YOUR_DOMAIN:3129"

with Session(impersonate="chrome120", proxy=proxy, verify=True) as s:
    r = s.get("https://www.google.com")
    print(f"Status: {r.status_code}")
```

### Linux / CLI - Standard HTTP Proxy (Port 3128)
```bash
# Using standard HTTP proxy on port 3128
export http_proxy="http://user:password@YOUR_HA_IP:3128"
export https_proxy="http://user:password@YOUR_HA_IP:3128"
curl https://httpbin.org/ip
```

### Linux / CLI - Secure HTTPS Proxy (Port 3129)
```bash
# Using secure HTTPS proxy on port 3129 (requires enable_https: true)
export http_proxy="https://user:password@YOUR_DOMAIN:3129"
export https_proxy="https://user:password@YOUR_DOMAIN:3129"
curl https://httpbin.org/ip
```

---

## 6. Troubleshooting

### "Access Denied" (403/407)
*   Check your `proxy_user` and `proxy_password`.
*   If `allow_all` is `false`, verify that your client IP is inside one of the `allowed_networks`.

### "Let's Encrypt generation failed"
*   Check that **Port 80** is open and accurately forwarded.
*   Ensure no other service is binding to Port 80 on your host.

### "Dashboard is empty"
*   Ensure the add-on is started.
*   Wait 2-5 seconds for the first live data poll to hit the dashboard.

---

## 7. Testing

The add-on includes test scripts in the `tests/` directory for validating functionality.

### Setup Test Environment

1. **Install dependencies:**
   ```bash
   pip install python-dotenv curl-cffi requests
   ```

2. **Configure credentials:**
   ```bash
   cd tests
   cp .env.example .env
   ```

3. **Edit `.env` with your credentials:**
   ```bash
   PROXY_USER=your_username
   PROXY_PASSWORD=your_password
   PROXY_URL=https://your-domain.com:3129
   ```

### Run Tests

```bash
python test_proxy.py
```

This creates 10 concurrent connections to test proxy functionality and generate traffic visible in the monitoring dashboard.

**Security Note:** The `.env` file is automatically ignored by git to prevent credential leaks.
