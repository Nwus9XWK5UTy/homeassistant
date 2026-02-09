#!/usr/bin/with-contenv bashio

echo "Starting Squid Proxy Add-on..."

# 1. SSL Management (For HTTPS Proxy)
ENABLE_HTTPS=$(bashio::config 'enable_https')
USE_LETSENCRYPT=$(bashio::config 'use_letsencrypt')
LE_EMAIL=$(bashio::config 'letsencrypt_email')
PROXY_DOMAIN=$(bashio::config 'proxy_domain')
HTTPS_LISTENER=""

SQUID_CERT="/tmp/squid.crt"
SQUID_KEY="/tmp/squid.key"

# Ensure persistence directories exist
mkdir -p /data/letsencrypt/work /data/letsencrypt/logs /data/self-signed
# Let's Encrypt dirs must be root-owned for Certbot, but world-readable for Squid to access certs
chown -R root:root /data/letsencrypt
chmod -R 755 /data/letsencrypt
chown -R squid:squid /data/self-signed

if [ "$ENABLE_HTTPS" = "true" ]; then
    if [ "$PROXY_DOMAIN" = "homeassistant.local" ] || [ -z "$PROXY_DOMAIN" ]; then
        bashio::log.warning "HTTPS Proxy enabled but no valid Domain provided. Falling back to HTTP only."
        ENABLE_HTTPS="false"
    else
        # --- MODE A: Let's Encrypt ---
        if [ "$USE_LETSENCRYPT" = "true" ]; then
            bashio::log.info "Mode: Let's Encrypt (Automated)"
            
            if [ -z "$LE_EMAIL" ]; then
                bashio::log.error "Let's Encrypt enabled but no Email provided. Using self-signed fallback."
                USE_LETSENCRYPT="false"
            else
                # Define Certbot directories
                CB_OPTS="--config-dir /data/letsencrypt --work-dir /data/letsencrypt/work --logs-dir /data/letsencrypt/logs"
                
                bashio::log.info "Checking for existing certificates for ${PROXY_DOMAIN}..."
                # Dynamic discovery: Find the actual path (handles -0001 suffixes). 
                # We add '|| true' inside the subshell to prevent exit on no match.
                certbot certificates ${CB_OPTS} > /tmp/certs.txt 2>/dev/null || true
                FOUND_PATH=$(grep -A 12 "Certificate Name: ${PROXY_DOMAIN}" /tmp/certs.txt 2>/dev/null | grep "Certificate Path:" | sed 's/.*Certificate Path: //' | xargs || true)
                
                if [ -n "$FOUND_PATH" ] && [ -r "$FOUND_PATH" ]; then
                    bashio::log.info "Found valid Let's Encrypt certificate at: $FOUND_PATH"
                    LE_CERT_FILE="$FOUND_PATH"
                    LE_KEY_FILE=$(dirname "$FOUND_PATH")/privkey.pem
                else
                    bashio::log.info "Certificate not found. Requesting from Let's Encrypt..."
                    certbot certonly --standalone \
                        ${CB_OPTS} \
                        --non-interactive --agree-tos --email "${LE_EMAIL}" \
                        -d "${PROXY_DOMAIN}" \
                        --preferred-challenges http \
                        --keep-until-expiring || bashio::log.warning "Certbot request failed."
                    
                    # Re-discover after attempt
                    certbot certificates ${CB_OPTS} > /tmp/certs.txt 2>/dev/null || true
                    LE_CERT_FILE=$(grep -A 12 "Certificate Name: ${PROXY_DOMAIN}" /tmp/certs.txt 2>/dev/null | grep "Certificate Path:" | sed 's/.*Certificate Path: //' | xargs || true)
                    if [ -n "$LE_CERT_FILE" ]; then
                        LE_KEY_FILE=$(dirname "$LE_CERT_FILE")/privkey.pem
                    fi
                fi
                
                # Final check and link
                if [ -n "$LE_CERT_FILE" ] && [ -r "$LE_CERT_FILE" ]; then
                    bashio::log.info "Success: Linking Let's Encrypt certs to Squid..."
                    ln -sf "${LE_CERT_FILE}" "${SQUID_CERT}"
                    ln -sf "${LE_KEY_FILE}" "${SQUID_KEY}"
                else
                    bashio::log.warning "Let's Encrypt setup failed. Falling back to self-signed."
                    USE_LETSENCRYPT="false"
                fi
            fi
        fi

        # --- MODE B: Self-Signed (Fallback or Default) ---
        if [ "$USE_LETSENCRYPT" != "true" ]; then
            echo "Mode: Self-Signed Certificate"
            
            SELF_CERT_DIR="/data/self-signed"
            mkdir -p "${SELF_CERT_DIR}"
            PERS_CRT="${SELF_CERT_DIR}/squid.crt"
            PERS_KEY="${SELF_CERT_DIR}/squid.key"

            # Check if existing persistent cert matches domain and is readable
            if [ -r "${PERS_CRT}" ]; then
                CURRENT_CN=$(openssl x509 -noout -subject -in "${PERS_CRT}" | sed -n 's/.*CN[ =]*//p' | sed 's/[, ].*//')
                if [ "$CURRENT_CN" != "$PROXY_DOMAIN" ]; then
                    echo "Domain changed from ${CURRENT_CN} to ${PROXY_DOMAIN}. Regenerating self-signed certificate..."
                    rm -f "${PERS_CRT}" "${PERS_KEY}"
                fi
            fi

            if [ ! -r "${PERS_CRT}" ]; then
                echo "Generating self-signed certificate for ${PROXY_DOMAIN}..."
                openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
                    -keyout "${PERS_KEY}" -out "${PERS_CRT}" \
                    -subj "/C=DE/ST=Berlin/L=Berlin/O=HomeAssistant/OU=Squid/CN=${PROXY_DOMAIN}"
            fi
            
            # Link to runtime path
            ln -sf "${PERS_CRT}" "${SQUID_CERT}"
            ln -sf "${PERS_KEY}" "${SQUID_KEY}"
        fi
        
        HTTPS_LISTENER="https_port 3129 cert=${SQUID_CERT} key=${SQUID_KEY}"
    fi
fi

# 2. Setup Authentication
echo "Setting up authentication..."
PROXY_USER=$(bashio::config 'proxy_user')
PROXY_PASSWORD=$(bashio::config 'proxy_password')
htpasswd -bc /tmp/passwd "${PROXY_USER}" "${PROXY_PASSWORD}"
chown squid:squid /tmp/passwd

# 3. Dynamic Network Configuration
ALLOW_ALL=$(bashio::config 'allow_all')
NETWORK_ACL_LINES=""
ACCESS_RULES=""

if [ "$ALLOW_ALL" = "true" ]; then
    echo "Configuring for: ALLOW ALL (Internet Access)"
    ACCESS_RULES="http_access allow authenticated"
else
    echo "Configuring for: RESTRICTED NETWORKS"
    # Build ACL entries for each network
    for network in $(bashio::config 'allowed_networks'); do
        echo " Adding ACL for: $network"
        NETWORK_ACL_LINES="${NETWORK_ACL_LINES}acl allowed_net src $network\n"
    done
    ACCESS_RULES="http_access allow authenticated allowed_net"
fi

# 4. Global Port Selection
ENABLE_HTTP=$(bashio::config 'enable_http' 'true')
HTTP_LISTENER=""
if [ "$ENABLE_HTTP" = "true" ]; then
    HTTP_LISTENER="http_port 3128"
fi

if [ "$ENABLE_HTTP" != "true" ] && [ "$ENABLE_HTTPS" != "true" ]; then
    bashio::log.error "Neither HTTP nor HTTPS remains enabled. Standardizing on HTTP 3128."
    HTTP_LISTENER="http_port 3128"
fi

# 5. Logging Configuration (Conditional)
DEBUG_MODE=$(bashio::config 'debug')
# Ensure logging directory exists and is writable by squid
mkdir -p /var/log/squid
touch /var/log/squid/access.log /var/log/squid/cache.log
chown -R squid:squid /var/log/squid

if [ "$DEBUG_MODE" = "true" ]; then
    bashio::log.info "Logging: VERBOSE (Tailing to Console)"
    ACCESS_LOG="access_log /var/log/squid/access.log combined"
    DEBUG_OPTIONS="debug_options ALL,1" 
    
    # Start background tailing only in debug mode
    tail -f /var/log/squid/access.log /var/log/squid/cache.log &
else
    bashio::log.info "Logging: MINIMAL"
    ACCESS_LOG="access_log none"
    DEBUG_OPTIONS=""
fi

# Point to real files to satisfy Squid's directory-writability check
CACHE_LOG="cache_log /var/log/squid/cache.log"

# 6. Generate Squid Config
echo "Generating Squid configuration..."
NEW_SQUID_CONF="/tmp/squid.conf"

# Prepare Caching Configuration (Calculated before writing file)
CACHE_CONFIG_LINES=""
# Caching Configuration
if [ "$(bashio::config 'cache_enabled')" = "true" ]; then
    echo "Caching: ENABLED (Volatile)"
    
    # Get parameters
    CACHE_MEM=$(bashio::config 'cache_mem_size_mb')
    CACHE_DISK=$(bashio::config 'cache_disk_size_mb')
    CACHE_OBJ_MAX=$(bashio::config 'cache_max_object_size_mb')
    
    echo "Caching: ENABLED (Mem: ${CACHE_MEM}MB, Disk: ${CACHE_DISK}MB)"
    
    # Ensure cache directory exists (Volatile /tmp for Pi health)
    mkdir -p /tmp/squid_cache
    chown -R squid:squid /tmp/squid_cache
    
    CACHE_CONFIG_LINES="# Caching: ENABLED
cache_mem ${CACHE_MEM} MB
maximum_object_size_in_memory 512 KB
maximum_object_size ${CACHE_OBJ_MAX} MB
cache_dir ufs /tmp/squid_cache ${CACHE_DISK} 16 256
minimum_object_size 0 KB
cache_swap_low 90
cache_swap_high 95"
else
    echo "Caching: DISABLED (Privacy Mode)"
    CACHE_CONFIG_LINES="# Caching: DISABLED
cache deny all"
fi

printf "# Squid Proxy Config (Auto-generated)
acl SSL_ports port 443
acl Safe_ports port 443
acl CONNECT method CONNECT

# Auth Setup
auth_param basic program /usr/lib/squid/basic_ncsa_auth /tmp/passwd
auth_param basic realm Squid Proxy
auth_param basic credentialsttl 2 hours
auth_param basic casesensitive on
acl authenticated proxy_auth REQUIRED

# Access Control Logic

# Allow localhost manager access (stats) - MUST BE FIRST (before Safe_ports)
http_access allow manager localhost
http_access deny manager

http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports

${NETWORK_ACL_LINES}

${ACCESS_RULES}

http_access deny all

# Listeners
${HTTP_LISTENER}
${HTTPS_LISTENER}

# Performance & Stealth
${CACHE_CONFIG_LINES}

via on
forwarded_for off
request_header_access X-Forwarded-For deny all
request_header_access Proxy-Connection deny all
request_header_access Proxy-Authorization deny all
request_header_access Cache-Control deny all

# Logging & Debugging
${ACCESS_LOG}
${CACHE_LOG}
${DEBUG_OPTIONS}

# Process Management
pid_filename /var/run/squid.pid
cache_effective_user squid
cache_effective_group squid
" > "${NEW_SQUID_CONF}"

# Atomically update config only if changed
if [ -f /tmp/squid.conf ] && diff "${NEW_SQUID_CONF}" /tmp/squid.conf > /dev/null; then
    echo "Configuration unchanged. Skipping update."
else
    echo "Applying new configuration..."
    mv "${NEW_SQUID_CONF}" /tmp/squid.conf
fi

# Ensure Cache Structure Exists (Run AFTER config is valid)
if [ "$(bashio::config 'cache_enabled')" = "true" ]; then
    if [ ! -d "/tmp/squid_cache/00" ]; then
        echo "Initializing Squid cache structure..."
        # Must run as squid user or fix permissions after? AppArmor profile allows this?
        # Standard squid -z works usually.
        squid -z -N -f /tmp/squid.conf 2>/dev/null
    fi
    # Fix ownership because squid -z ran as root
    chown -R squid:squid /tmp/squid_cache
fi

# Permissions and Dirs
mkdir -p /var/cache/squid
chown -R squid:squid /var/cache/squid /var/log/squid

# Final initialization and Launch
echo "----------------------------------------------------"
if [ "$ENABLE_HTTP" = "true" ]; then
    echo "  Standard Proxy (HTTP)  : [ENABLED] on port 3128"
fi
if [ "$ENABLE_HTTPS" = "true" ]; then
    echo "  Secure Proxy (HTTPS)   : [ENABLED] on port 3129"
    echo "  SSL Mode               : $([ "$USE_LETSENCRYPT" = "true" ] && echo "Let's Encrypt (Trusted)" || echo "Self-Signed")"
    echo "  SSL Certificate CN     : ${PROXY_DOMAIN}"
fi
echo "  Authentication         : [ENABLED] for user ${PROXY_USER}"
echo "  Anonymity/Stealth      : [ENABLED]"
echo "  Logging Mode           : $([ "$DEBUG_MODE" = "true" ] && echo "VERBOSE" || echo "MINIMAL")"
echo "Done! Squid is up and running. Happy proxying!"

# Start Monitor (Ingress Dashboard)
echo "Starting Squid Monitor on port 8099 (Gunicorn)..."
gunicorn -w 1 --chdir /monitoring -b "[::]:8099" monitor:app &

# Start Squid in the foreground
# We removed -d 1 to keep the console clean in minimal mode.
# Critical errors will still be captured by the container's stderr.
exec squid -N -f /tmp/squid.conf