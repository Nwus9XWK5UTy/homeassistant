# Home Assistant Add-on: Squid Proxy v1.0.3

[![Version](https://img.shields.io/badge/version-v1.0.3-blue.svg)](https://github.com/Nwus9XWK5UTy/homeassistant/releases/latest)
![Project Stage](https://img.shields.io/badge/project%20stage-production%20ready-brightgreen.svg)
![Maintained](https://img.shields.io/badge/maintained-yes-brightgreen.svg)

A high-performance, security-focused Squid proxy designed for power users, automation scripts, and privacy-conscious setups. This add-on is specifically optimized for scraping and bypassing bot-detection while maintaining a minimal footprint on your Home Assistant system.

## Key Features

- **🚀 Dual-Protocol Support**: Run a standard HTTP proxy (Port 3128) and a Secure HTTPS-to-HTTPS (Port 3129) proxy simultaneously.
- **🛡️ TLS Stealth**: Automatically strips proxy-identifying headers (`Via`, `X-Forwarded-For`) and mimics modern browser behavior to stay undetected.
- **📊 Real-time Dashboard**: Built-in Ingress UI with live graphs showing active connections split by protocol (HTTP vs HTTPS).
- **🔒 Security Focused**: Caching disabled by default (`cache deny all`) for maximum privacy, with optional Smart Caching for performance.
- **📜 Native Let's Encrypt**: Trusted SSL certificate management with automatic self-signed fallback.
- **🔐 Secure Authentication**: Mandatory username/password protection for all ports.
- **🌐 Network Control**: Fine-grained IP filtering (ACLs) to restrict access to trusted ranges.

## Security Features

This add-on implements **minimal access principle** - it runs with only the essential permissions needed for proxy functionality:

- **Network-Only Access**: The proxy only has network access and persistent storage - no hardware, no host namespaces, no system APIs.
- **Isolated Container**: Disabled host IPC, D-Bus, and PID namespaces to prevent cross-container attacks.
- **No Hardware Access**: All hardware devices (GPIO, USB, UART, video, audio) are explicitly disabled.
- **Volatile Storage**: Logs and cache are stored in memory-backed tmpfs mounts, leaving no persistent traces.
- **Custom AppArmor Profile**: Enforces mandatory access control policies to limit process capabilities.
- **Strict Input Validation**: All configuration inputs are validated with regex patterns to prevent injection attacks.
- **No Kernel Modules**: Cannot load kernel modules, reducing attack surface.
- **Production Ready**: Marked as stable stage with comprehensive security hardening.

> **Note**: This add-on uses a custom AppArmor profile. If your host system does not support it (e.g. certain NAS installs), it may fall back to the default Docker profile or fail to load. Check Supervisor logs if startup issues occur.

## Quick Start

1. Install the **Squid Proxy** add-on from the local store.
2. Go to the **Configuration** tab and set your `proxy_user` and `proxy_password` (minimum 8 chars).
3. (Optional) Set `enable_https: true` and provide your `proxy_domain` if you want Secure Proxying.
4. **Start** the add-on.
5. Click **Open Web UI** to monitor your traffic in real-time.

## Connection Summary

| Port | Type | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| **3128** | HTTP | Yes | Standard proxy for general usage. |
| **3129** | HTTPS | Yes | Secure Proxy (Encrypted tunnel from client to proxy). |
| **8099** | Ingress | HA Web UI | Internal Monitoring Dashboard (not exposed). |

## Caching Configuration
By default, caching is **disabled** to protect user privacy and minimize disk I/O. However, for bandwidth-constrained environments, you can enable volatile caching (RAM-backed via tmpfs).

| Option | Default | Description |
| :--- | :--- | :--- |
| `cache_enabled` | `false` | Enable/Disable caching. |
| `cache_mem_size_mb` | 64 | RAM reserved for hot objects. |
| `cache_disk_size_mb` | 512 | Volatile disk cache size (on `/tmp` tmpfs). |
| `cache_max_object_size_mb` | 10 | Max size of a single cached file. |

> **Important**: Caching **only works for HTTP** traffic (Port 3128). HTTPS traffic (Port 3129) is encrypted and tunneled, so Squid cannot cache it without complex SSL Bumping (not configured here). If you only use HTTPS, keep caching **disabled** to save resources.

> **Note**: Cache is stored in `/tmp` (tmpfs). It is **not persistent** and will be wiped when the add-on stops. This prevents SD card wear on Raspberry Pi systems.

## Detailed Documentation

For advanced setup (Let's Encrypt, ACLs, and code examples), see the **Documentation** tab.

## Support

- **Source Code**: [https://github.com/Nwus9XWK5UTy/homeassistant](https://github.com/Nwus9XWK5UTy/homeassistant)
- **Changelog**: [Full Changelog](CHANGELOG.md)
- **Issues**: [Report a Bug](https://github.com/Nwus9XWK5UTy/homeassistant/issues)
