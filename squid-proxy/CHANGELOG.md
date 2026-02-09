# Changelog

## 1.0.3
- **Schema**: Adjusted configuration schema order for better logical grouping of network settings.

## 1.0.2
- **Update**: Reorganized configuration options for better readability.

## 1.0.1
- **Fix**: Resolved UI localization issues for Caching Configuration by flattening nested keys (e.g. `caching.enabled` -> `cache_enabled`). NOTE: You may need to re-enter your caching settings.
- **Improved**: Documentation explicitly states caching is HTTP-only.

## 1.0.0
- **Initial Release**: Comprehensive Squid Proxy add-on with HTTPS support, Stealth Mode, Let's Encrypt integration, Volatile Caching (HTTP only), and Real-time Monitoring Dashboard.
- **Features**: 
    - Full HTTPS/SSL Support (Secure Proxy on port 3129).
    - Automated Let's Encrypt Certificate Management.
    - TLS Stealth Mode for avoiding bot detection.
    - Volatile Caching Engine (RAM/Tmpfs) for high performance and SD card preserverance.
    - Real-time Monitoring Dashboard with traffic stats and cache efficiency.
- **Security**: 
    - Hardened AppArmor profile.
    - Strict access control lists (ACLs).
    - Privilege dropping to non-root `squid` user.
