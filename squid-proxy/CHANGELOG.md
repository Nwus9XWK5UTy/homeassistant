# Changelog

## 1.0.6
- **Fix**: Resolved permission issue where Squid could not read Let's Encrypt certificates.
- **Improved**: Enhanced logging for certificate renewals; errors are no longer suppressed.

## 1.0.5
- **Fix**: Resolved issue where expired certificates were not refreshed at startup.
- **Fix**: Reordered renewal monitor loop to perform an immediate check upon startup.

## 1.0.4
- **Feature**: Added background monitor for automated Let's Encrypt renewal with zero-downtime configuration reloads.
- **Improved**: Added multi-architecture support for amd64, aarch64, armhf, and armv7.
- **Security**: Implemented dynamic port security; port 80 is now restricted to only when HTTP proxying or Let's Encrypt is enabled.

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
