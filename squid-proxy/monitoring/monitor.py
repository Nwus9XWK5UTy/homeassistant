import os
import sys
import json
import socket
import struct
import ssl
import re
from flask import Flask, render_template, jsonify

# Resolve template dir relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
app = Flask(__name__, template_folder=TEMPLATE_DIR)

# Constants
SQUID_PORTS = [3128, 3129]  # 3128=HTTP, 3129=HTTPS

def hex_to_ip(hex_ip):
    """Convert hex IP string to dotted decimal (IPv4) or colon-separated (IPv6)."""
    try:
        # IPv4: 8 hex chars (Little Endian)
        if len(hex_ip) == 8:
            ip_addr = int(hex_ip, 16)
            return socket.inet_ntoa(struct.pack("<L", ip_addr))
            
        # IPv6: 32 hex chars (Four 32-bit Little Endian words)
        elif len(hex_ip) == 32:
            parts = [int(hex_ip[i:i+8], 16) for i in range(0, 32, 8)]
            ip_bytes = b''.join(struct.pack("<L", x) for x in parts)
            ip_str = socket.inet_ntop(socket.AF_INET6, ip_bytes)
            
            if ip_str.startswith("::ffff:") and "." in ip_str:
                return ip_str.replace("::ffff:", "")
            return ip_str
    except Exception:
        pass
    return hex_ip

def get_connected_clients():
    """Get connection statistics separated by protocol."""
    res = {
        "http": {"conn": 0, "ips": set()},
        "https": {"conn": 0, "ips": set()}
    }

    try:
        for proc_file in ["/proc/net/tcp", "/proc/net/tcp6"]:
            if not os.path.exists(proc_file):
                continue
                
            with open(proc_file, "r") as f:
                next(f) # Skip header
                for line in f:
                    try:
                        parts = line.split()
                        if len(parts) < 4: continue
                        
                        state = parts[3]
                        # 01=ESTABLISHED, 06=TIME_WAIT, 08=CLOSE_WAIT
                        if state not in ['01', '06', '08']:
                            continue

                        # Local Address IP:PORT
                        _, local_port_hex = parts[1].split(':')
                        try:
                            local_port = int(local_port_hex, 16)
                        except ValueError:
                            continue
                        
                        if local_port in SQUID_PORTS:
                            # Remote Address IP:PORT
                            rem_ip_hex, _ = parts[2].split(':')
                            client_ip = hex_to_ip(rem_ip_hex)
                            
                            # Filtering localhost
                            if client_ip in ['127.0.0.1', '::1'] or client_ip.startswith('::ffff:127.0.0.1'):
                                continue
                                
                            if local_port == 3128:
                                res["http"]["conn"] += 1
                                res["http"]["ips"].add(client_ip)
                            elif local_port == 3129:
                                res["https"]["conn"] += 1
                                res["https"]["ips"].add(client_ip)
                    except Exception:
                        continue
    except Exception as e:
        sys.stderr.write(f"Monitor: Error reading network stats: {e}\n")
    
    return {
        "http_connections": res["http"]["conn"],
        "http_clients": list(res["http"]["ips"]),
        "https_connections": res["https"]["conn"],
        "https_clients": list(res["https"]["ips"])
    }

def get_squid_uptime():
    """Calculate the uptime of the Squid process in seconds."""
    try:
        pid_file = "/var/run/squid.pid"
        if not os.path.exists(pid_file):
            return 0
        with open(pid_file, "r") as f:
            pid = f.read().strip()
        with open(f"/proc/{pid}/stat", "r") as f:
            stat_content = f.read()
        rpar_index = stat_content.rfind(')')
        if rpar_index == -1: return 0
        stat_fields = stat_content[rpar_index+2:].split()
        starttime_ticks = int(stat_fields[19])
        with open("/proc/uptime", "r") as f:
            system_uptime_sec = float(f.read().split()[0])
        clk_tck = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        return int(max(0, system_uptime_sec - (starttime_ticks / clk_tck)))
    except Exception:
        return 0

def get_squid_stats():
    """Query Squid manager info for request rates."""
    info = {"requests_total": 0}
    request = b"GET /squid-internal-mgr/info HTTP/1.0\r\nHost: localhost\r\nAccept: */*\r\n\r\n"
    
    response_data = None
    # Try HTTP 3128
    try:
        with socket.create_connection(("127.0.0.1", 3128), timeout=0.5) as s:
            s.sendall(request)
            response_data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk: break
                response_data += chunk
    except Exception:
        pass

    # Try HTTPS 3129 fallback
    if not response_data:
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with socket.create_connection(("127.0.0.1", 3129), timeout=1) as sock:
                with context.wrap_socket(sock, server_hostname="localhost") as ssock:
                    ssock.sendall(request)
                    response_data = b""
                    while True:
                        chunk = ssock.recv(4096)
                        if not chunk: break
                        response_data += chunk
        except Exception:
            pass

    if response_data:
        try:
            resp = response_data.decode('utf-8', errors='ignore')
            for line in resp.splitlines():
                if "Number of HTTP requests received" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        info["requests_total"] = int(parts[1].strip())
                elif "Cache Hits:" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        # Format: Cache Hits:          0 (  0%)
                        val = parts[1].strip().split()[0]
                        info["cache_hits"] = int(val)
                elif "Cache Misses:" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        val = parts[1].strip().split()[0]
                        info["cache_misses"] = int(val)
                elif "Byte Hit Ratio:" in line:
                    # Format: Byte Hit Ratio:       0.0%  5.0%
                    # We take the 5-min average (usually second value, or first if only one)
                    # Actually standard output: Byte Hit Ratio:       5min: 0.0%, 60min: 0.0%
                    # OR just: Byte Hit Ratio:       0.0%
                    # Let's simple scrape the first percentage found
                    import re
                    match = re.search(r'([\d\.]+)%', line)
                    if match:
                        info["byte_hit_ratio"] = float(match.group(1))
        except Exception:
            pass
            
    # Defaults if not found
    if "cache_hits" not in info: info["cache_hits"] = 0
    if "cache_misses" not in info: info["cache_misses"] = 0
    if "byte_hit_ratio" not in info: info["byte_hit_ratio"] = 0.0
    
    return info

def get_system_stats():
    """Gather all stats."""
    net = get_connected_clients()
    squid = get_squid_stats()
    
    # Calculate Memory
    memory_mb = 0
    try:
        if os.path.exists("/sys/fs/cgroup/memory.current"):
            with open("/sys/fs/cgroup/memory.current", "r") as f:
                memory_mb = round(int(f.read()) / 1024 / 1024, 1)
        elif os.path.exists("/sys/fs/cgroup/memory/memory.usage_in_bytes"):
            with open("/sys/fs/cgroup/memory/memory.usage_in_bytes", "r") as f:
                memory_mb = round(int(f.read()) / 1024 / 1024, 1)
    except Exception:
        pass

    return {
        "total_connections": net["http_connections"] + net["https_connections"],
        "http_connections": net["http_connections"],
        "https_connections": net["https_connections"],
        "http_clients": net["http_clients"],
        "https_clients": net["https_clients"],
        "uptime": get_squid_uptime(),
        "memory_mb": memory_mb,
        "squid": squid
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    return jsonify(get_system_stats())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8099, debug=False, use_reloader=False)
