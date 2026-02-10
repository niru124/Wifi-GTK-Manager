"""nmcli utility functions for WiFi management"""

import subprocess

QR_FILE = "/tmp/wifi_qr.png"

def run_cmd(args, timeout=10):
    """Run a command and return output"""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return "", False

def parse_wifi_line(line):
    """Parse nmcli wifi line handling escaped colons in BSSID"""
    placeholder = "\x00"
    line = line.replace("\\:", placeholder)
    parts = line.split(":")
    parts = [p.replace(placeholder, ":") for p in parts]
    return parts

def get_current_connection_name():
    """Get the name of the currently active WiFi connection"""
    output, _ = run_cmd(["nmcli", "-t", "connection", "show", "--active"])
    for line in output.split("\n"):
        if "802-11-wireless" in line:
            return line.split(":")[0]
    return ""

def get_current_ssid():
    """Get the SSID of the currently connected network"""
    conn_name = get_current_connection_name()
    if not conn_name:
        return ""
    
    output, _ = run_cmd(["nmcli", "-t", "connection", "show", conn_name])
    for line in output.split("\n"):
        if "802-11-wireless.ssid:" in line:
            return line.split(":")[1]
    return ""

def get_networks():
    """Get list of available WiFi networks"""
    output, _ = run_cmd(["nmcli", "-t", "device", "wifi", "list"])
    current = get_current_ssid()
    networks = []
    
    for line in output.split("\n"):
        if not line.strip():
            continue
        
        parts = parse_wifi_line(line)
        if len(parts) >= 9:
            ssid = parts[2]
            signal = parts[6]
            security = parts[8]
            
            if not ssid:
                ssid = "Hidden Network"
            
            connected = (ssid == current)
            networks.append({
                'ssid': ssid,
                'signal': signal,
                'security': security,
                'connected': connected
            })
    
    return networks

def get_security(ssid):
    """Get the security type of a network"""
    networks = get_networks()
    for net in networks:
        if net['ssid'] == ssid:
            return net['security']
    return "WPA2"

def get_password(ssid):
    """Get the saved password for a network"""
    output, _ = run_cmd(["nmcli", "-s", "-t", "connection", "show", ssid])
    for line in output.split("\n"):
        if "802-11-wireless-security.psk:" in line:
            parts = line.split(":", 1)
            if len(parts) >= 2 and parts[1] and parts[1] != "<hidden>":
                return parts[1]
    return ""

def get_auto_connect(ssid):
    """Check if auto-connect is enabled for a network"""
    output, _ = run_cmd(["nmcli", "-t", "connection", "show", ssid])
    for line in output.split("\n"):
        if "connection.autoconnect:" in line:
            return line.split(":")[1] == "yes"
    return False

def set_auto_connect(ssid, enabled):
    """Set auto-connect for a network"""
    value = "yes" if enabled else "no"
    run_cmd(["nmcli", "connection", "modify", ssid, "connection.autoconnect", value])

def forget_network(ssid):
    """Remove a saved network profile"""
    result, _ = run_cmd(["nmcli", "connection", "delete", ssid])
    return result == ""

def connect_network(ssid, password, security):
    """Connect to a WiFi network"""
    cmd = ["nmcli", "device", "wifi", "connect", ssid]
    if security != "Open" and password:
        cmd.extend(["password", password])
    
    output, success = run_cmd(cmd)
    return success

def disconnect_network():
    """Disconnect from the current network"""
    conn_name = get_current_connection_name()
    if conn_name:
        run_cmd(["nmcli", "connection", "down", conn_name])
        return True
    return False

def rescan_networks():
    """Trigger a network rescan"""
    run_cmd(["nmcli", "device", "wifi", "rescan"])

def get_connection_speed():
    """Get current connection speed and signal"""
    current = get_current_ssid()
    if not current:
        return "N/A", "N/A"
    
    output, _ = run_cmd(["nmcli", "-t", "device", "wifi", "list"])
    for line in output.split("\n"):
        parts = parse_wifi_line(line)
        if len(parts) >= 7 and parts[2] == current:
            rate = parts[5]
            signal = parts[6]
            return rate, signal
    return "N/A", "N/A"

def get_connection_details():
    """Get detailed connection information"""
    conn_name = get_current_connection_name()
    if not conn_name:
        return {}
    
    details = {}
    output, _ = run_cmd(["nmcli", "-t", "connection", "show", conn_name])
    
    for line in output.split("\n"):
        if "ipv4.addresses:" in line:
            details["ip"] = line.split(":")[1]
        elif "ipv4.gateway:" in line:
            details["gateway"] = line.split(":")[1]
        elif "ipv4.dns:" in line:
            details["dns"] = line.split(":")[1]
        elif "GENERAL.STATE:" in line:
            details["state"] = line.split(":")[1]
        elif "GENERAL.DEVICES:" in line:
            details["device"] = line.split(":")[1]
        elif "802-11-wireless.signal:" in line:
            details["signal_dbm"] = line.split(":")[1]
        elif "connection.autoconnect:" in line:
            details["autoconnect"] = line.split(":")[1] == "yes"
    
    return details

def get_ip_info():
    """Get comprehensive IP information"""
    info = {
        "local_ip": "N/A",
        "gateway": "N/A",
        "dns1": "N/A",
        "dns2": "N/A",
        "subnet": "N/A",
        "interface": "N/A"
    }
    
    # Get default route info
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "default" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "dev" and i + 1 < len(parts):
                        info["interface"] = parts[i + 1]
                    elif p == "via" and i + 1 < len(parts):
                        info["gateway"] = parts[i + 1]
    except:
        pass
    
    # Get IP address for interface
    iface = info["interface"]
    if iface:
        try:
            result = subprocess.run(
                ["ip", "addr", "show", iface],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "inet " in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        info["local_ip"] = parts[1]
                        break
        except:
            pass
    
    # Get DNS servers
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        if info["dns1"] == "N/A":
                            info["dns1"] = parts[1]
                        elif info["dns2"] == "N/A":
                            info["dns2"] = parts[1]
                            break
    except:
        pass
    
    # Get from nmcli as fallback
    details = get_connection_details()
    if details.get("ip") and info["local_ip"] == "N/A":
        info["local_ip"] = details.get("ip", "N/A")
    if details.get("gateway") and info["gateway"] == "N/A":
        info["gateway"] = details.get("gateway", "N/A")
    if details.get("dns") and info["dns1"] == "N/A":
        dns = details.get("dns", "")
        dns_parts = dns.split(",")
        if len(dns_parts) >= 1:
            info["dns1"] = dns_parts[0].strip()
        if len(dns_parts) >= 2:
            info["dns2"] = dns_parts[1].strip()
    
    return info

# Live speed monitoring
_last_rx = 0
_last_tx = 0
_last_time = 0

def get_live_speed():
    """Get live TX/RX speed in bytes per second"""
    global _last_rx, _last_tx, _last_time
    
    iface = get_network_interface()
    if not iface:
        return 0, 0
    
    rx_path = f"/sys/class/net/{iface}/statistics/rx_bytes"
    tx_path = f"/sys/class/net/{iface}/statistics/tx_bytes"
    
    try:
        with open(rx_path, "r") as f:
            rx = int(f.read().strip())
        with open(tx_path, "r") as f:
            tx = int(f.read().strip())
    except:
        return 0, 0
    
    import time
    current_time = time.time()
    
    if _last_time == 0:
        _last_rx = rx
        _last_tx = tx
        _last_time = current_time
        return 0, 0
    
    time_delta = current_time - _last_time
    if time_delta < 0.1:
        return 0, 0
    
    rx_speed = int((rx - _last_rx) / time_delta)
    tx_speed = int((tx - _last_tx) / time_delta)
    
    _last_rx = rx
    _last_tx = tx
    _last_time = current_time
    
    return rx_speed, tx_speed

def format_speed(bytes_per_sec):
    """Format speed to human readable"""
    if bytes_per_sec >= 1073741824:
        return f"{bytes_per_sec / 1073741824:.1f} GB/s"
    elif bytes_per_sec >= 1048576:
        return f"{bytes_per_sec / 1048576:.1f} MB/s"
    elif bytes_per_sec >= 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec} B/s"

def get_network_interface():
    """Get the active network interface"""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "default" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "dev" and i + 1 < len(parts):
                        return parts[i + 1]
    except:
        pass
    return None

def is_wifi_enabled():
    """Check if WiFi is enabled"""
    output, _ = run_cmd(["nmcli", "-t", "radio", "wifi"])
    return output == "enabled"

def set_wifi_enabled(enabled):
    """Enable or disable WiFi"""
    if enabled:
        return run_cmd(["nmcli", "radio", "wifi", "on"])[1]
    else:
        return run_cmd(["nmcli", "radio", "wifi", "off"])[1]
