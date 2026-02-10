"""Hotspot configuration and management utilities"""

import subprocess

def run_cmd(args, timeout=10):
    """Run a command and return output"""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return "", False

def get_wifi_interface():
    """Get available WiFi interfaces"""
    output, _ = run_cmd(["nmcli", "-t", "device"])
    interfaces = []
    for line in output.split("\n"):
        if "wifi" in line or "wlan" in line.lower():
            parts = line.split(":")
            if len(parts) >= 1:
                interfaces.append(parts[0])
    return interfaces

def get_current_hotspot():
    """Check if hotspot is currently active"""
    output, _ = run_cmd(["nmcli", "-t", "connection", "show", "--active"])
    for line in output.split("\n"):
        if "802-11-wireless-hotspot" in line or "hotspot" in line.lower():
            conn = line.split(":")[0]
            ssid = run_cmd(["nmcli", "-t", "connection", "show", conn])
            for l in ssid[0].split("\n"):
                if "802-11-wireless.ssid:" in l:
                    return conn, l.split(":")[1]
    return None, None

def stop_hotspot(connection_name):
    """Stop the active hotspot"""
    if connection_name:
        run_cmd(["nmcli", "connection", "down", connection_name])
        return True
    return False

def create_hotspot(ssid, password, interface=None, band="bg", channel=0):
    """Create and start a hotspot"""
    cmd = ["nmcli", "device", "wifi", "hotspot"]
    
    if interface:
        cmd.extend(["ifname", interface])
    if ssid:
        cmd.extend(["ssid", ssid])
    if password:
        cmd.extend(["password", password])
    
    success = run_cmd(cmd)
    return success[1]

def save_hotspot_profile(ssid, password, interface=None, band="bg"):
    """Save hotspot as a connection profile"""
    cmd = [
        "nmcli", "connection", "add",
        "type", "wifi",
        "ifname", interface or "wlan0",
        "con-name", f"hotspot-{ssid}",
        "wifi.ssid", ssid,
        "wifi.mode", "ap",
        "wifi-sec.key-mgmt", "wpa-psk",
        "wifi-sec.psk", password,
        "ipv4.method", "shared"
    ]
    
    return run_cmd(cmd)[1]

def get_saved_hotspots():
    """Get list of saved hotspot profiles"""
    output, _ = run_cmd(["nmcli", "-t", "connection", "show"])
    hotspots = []
    for line in output.split("\n"):
        if "hotspot" in line.lower() or "ap" in line.lower():
            parts = line.split(":")
            if len(parts) >= 1:
                hotspots.append(parts[0])
    return hotspots

def delete_hotspot_profile(name):
    """Delete a saved hotspot profile"""
    return run_cmd(["nmcli", "connection", "delete", name])[1]

def get_available_channels(band="bg"):
    """Get available WiFi channels for a band"""
    output, _ = run_cmd(["nmcli", "-t", "device", "wifi", "list"])
    channels = set()
    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 4:
            chan = parts[3]
            if band in ["bg", "2.4"]:
                try:
                    c = int(chan)
                    if 1 <= c <= 14:
                        channels.add(c)
                except:
                    pass
            elif band in ["a", "5"]:
                try:
                    c = int(chan)
                    if c >= 36:
                        channels.add(c)
                except:
                    pass
    return sorted(list(channels))

def get_wifi_device_status():
    """Get WiFi device status"""
    output, _ = run_cmd(["nmcli", "-t", "device", "status"])
    for line in output.split("\n"):
        if "wifi" in line.lower():
            parts = line.split(":")
            if len(parts) >= 3:
                return parts[2]
    return "unknown"
