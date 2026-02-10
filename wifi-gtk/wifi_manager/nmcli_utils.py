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
