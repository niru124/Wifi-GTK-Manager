"""Hotspot configuration using linux-router or linux-wifi-hotspot

Supports WiFi-to-WiFi sharing (same adapter for internet + hotspot)
"""

import subprocess
import os
import signal

HOTSPOT_PROCESS = None

def run_cmd(args, timeout=10):
    """Run a command and return output"""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return "", False

def get_tool():
    """Check which hotspot tool is available"""
    # Check for linux-router (lnxrouter) first - more features
    result = subprocess.run(["which", "lnxrouter"], capture_output=True, text=True)
    if result.returncode == 0:
        return "lnxrouter", result.stdout.strip()
    
    # Check for linux-wifi-hotspot (create_ap)
    result = subprocess.run(["which", "create_ap"], capture_output=True, text=True)
    if result.returncode == 0:
        return "create_ap", result.stdout.strip()
    
    return None, None

def get_wifi_interface():
    """Get available WiFi interfaces"""
    output, _ = run_cmd(["nmcli", "-t", "device"])
    interfaces = []
    for line in output.split("\n"):
        if "wifi" in line.lower():
            parts = line.split(":")
            if len(parts) >= 1:
                iface = parts[0].strip()
                if iface and iface not in interfaces:
                    interfaces.append(iface)
    return interfaces

def get_default_interface():
    """Get the default WiFi interface"""
    interfaces = get_wifi_interface()
    if interfaces:
        return interfaces[0]
    return "wlan0"

def get_hotspot_status():
    """Check if hotspot is currently running"""
    global HOTSPOT_PROCESS
    
    tool, _ = get_tool()
    
    # Check our process
    if HOTSPOT_PROCESS and HOTSPOT_PROCESS.poll() is None:
        return True, HOTSPOT_PROCESS.pid, tool
    
    # Check for running processes
    for proc_name in ["lnxrouter", "create_ap"]:
        result = subprocess.run(
            ["pgrep", "-f", proc_name],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            if pids and pids[0]:
                return True, int(pids[0]), tool
    
    return False, None, tool

def stop_hotspot():
    """Stop the running hotspot"""
    global HOTSPOT_PROCESS
    
    tool, _ = get_tool()
    
    # Stop our process
    if HOTSPOT_PROCESS and HOTSPOT_PROCESS.poll() is None:
        try:
            os.killpg(os.getpgid(HOTSPOT_PROCESS.pid), signal.SIGTERM)
            HOTSPOT_PROCESS.wait()
        except:
            pass
        HOTSPOT_PROCESS = None
    
    # Kill any hotspot processes
    for proc_name in ["lnxrouter", "create_ap"]:
        subprocess.run(
            ["sudo", "pkill", "-f", proc_name],
            capture_output=True
        )
    
    return True

def create_hotspot(ssid, password, interface=None, band="2.4", channel=0):
    """
    Create and start a hotspot using available tool
    Supports WiFi-to-WiFi sharing (same adapter for internet + hotspot)
    """
    global HOTSPOT_PROCESS
    
    # Stop any existing hotspot
    stop_hotspot()
    
    tool, tool_path = get_tool()
    if not tool:
        return False, "No hotspot tool found. Install linux-router or linux-wifi-hotspot"
    
    iface = interface or get_default_interface()
    
    if tool == "lnxrouter":
        return _create_lnxrouter(ssid, password, iface, band, channel)
    elif tool == "create_ap":
        return _create_ap(ssid, password, iface, band, channel)
    else:
        return False, f"Unknown tool: {tool}"

def _create_lnxrouter(ssid, password, interface, band, channel):
    """Create hotspot using lnxrouter (linux-router)"""
    global HOTSPOT_PROCESS
    
    # Build lnxrouter command
    cmd = ["sudo", "lnxrouter"]
    
    # AP interface and SSID
    cmd.extend(["--ap", interface, ssid])
    
    # Password
    if password:
        cmd.extend(["-p", password])
    else:
        cmd.append("")  # Open network
    
    # Frequency band
    if band == "5":
        cmd.extend(["--freq-band", "5"])
    else:
        cmd.extend(["--freq-band", "2.4"])
    
    # Channel
    if channel > 0:
        cmd.extend(["-c", str(channel)])
    
    # Use same interface for internet and AP (WiFi-to-WiFi)
    cmd.extend(["--no-virt"])
    
    # NATed sharing (will use current internet connection)
    # lnxrouter automatically uses the default route for internet
    
    # Run lnxrouter
    try:
        HOTSPOT_PROCESS = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait to check if it started
        import time
        time.sleep(3)
        
        if HOTSPOT_PROCESS.poll() is None:
            return True, f"Hotspot '{ssid}' started on {interface}"
        else:
            _, stderr = HOTSPOT_PROCESS.communicate()
            return False, f"Failed: {stderr.decode()[:200]}"
    
    except Exception as e:
        return False, f"Error: {str(e)}"

def _create_ap(ssid, password, interface, band, channel):
    """Create hotspot using create_ap (linux-wifi-hotspot)"""
    global HOTSPOT_PROCESS
    
    cmd = ["sudo", "create_ap"]
    
    # Use same interface for both internet and hotspot
    cmd.extend([interface, interface])
    
    cmd.append(ssid)
    
    if password:
        cmd.append(password)
    else:
        cmd.append("")
    
    # Options
    cmd.extend(["--no-virt"])
    
    if channel > 0:
        cmd.extend(["--channel", str(channel)])
    else:
        if band == "5":
            cmd.extend(["--freq-band", "5"])
        else:
            cmd.extend(["--freq-band", "2.4"])
    
    # NAT sharing
    cmd.extend(["--nat"])
    
    try:
        HOTSPOT_PROCESS = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        import time
        time.sleep(3)
        
        if HOTSPOT_PROCESS.poll() is None:
            return True, f"Hotspot '{ssid}' started on {interface}"
        else:
            _, stderr = HOTSPOT_PROCESS.communicate()
            return False, f"Failed: {stderr.decode()[:200]}"
    
    except Exception as e:
        return False, f"Error: {str(e)}"

def save_hotspot_profile(ssid, password, interface=None, band="2.4"):
    """Save hotspot configuration"""
    config_dir = os.path.expanduser("~/.config/wifi-hotspot")
    os.makedirs(config_dir, exist_ok=True)
    
    config_file = os.path.join(config_dir, f"{ssid}.conf")
    
    iface = interface or get_default_interface()
    
    config = f"""# Hotspot Configuration
SSID={ssid}
PASSWORD={password}
INTERFACE={iface}
BAND={band}
"""
    
    with open(config_file, "w") as f:
        f.write(config)
    
    return True

def get_saved_hotspots():
    """Get list of saved hotspot profiles"""
    config_dir = os.path.expanduser("~/.config/wifi-hotspot")
    if not os.path.exists(config_dir):
        return []
    
    hotspots = []
    for f in os.listdir(config_dir):
        if f.endswith(".conf"):
            name = f[:-5]
            hotspots.append(name)
    
    return hotspots

def load_hotspot_profile(ssid):
    """Load a saved hotspot profile"""
    config_file = os.path.expanduser(f"~/.config/wifi-hotspot/{ssid}.conf")
    
    if not os.path.exists(config_file):
        return None
    
    config = {}
    with open(config_file, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                config[key] = value
    
    return config

def delete_hotspot_profile(ssid):
    """Delete a saved hotspot profile"""
    config_file = os.path.expanduser(f"~/.config/wifi-hotspot/{ssid}.conf")
    
    if os.path.exists(config_file):
        os.remove(config_file)
        return True
    return False

def get_current_hotspot():
    """Get current hotspot connection name and SSID"""
    output, _ = run_cmd(["nmcli", "-t", "connection", "show", "--active"])
    
    for line in output.split("\n"):
        if "802-11-wireless-security" in line:
            continue
        if ":hotspot:" in line or ":wifi-p2p:" in line:
            parts = line.split(":")
            if len(parts) >= 2:
                conn_name = parts[0]
                ssid = conn_name.replace("hotspot-", "").replace("wifi-", "")
                return conn_name, ssid
    
    running, _, _ = get_hotspot_status()
    if running:
        return "lnxrouter", "Hotspot"
    
    return None, None

def get_wifi_device_status():
    """Get WiFi device status"""
    output, _ = run_cmd(["nmcli", "-t", "device", "status"])
    
    for line in output.split("\n"):
        if "wifi" in line.lower():
            parts = line.split(":")
            if len(parts) >= 3:
                device = parts[0]
                state = parts[2]
                return {
                    "device": device,
                    "state": state,
                    "connected": state == "connected"
                }
    
    return {"device": None, "state": "unknown", "connected": False}

def get_connected_clients():
    """Get list of connected clients"""
    clients = []
    
    # Check dnsmasq leases
    lease_files = [
        "/tmp/dnsmasq.leases",
        "/var/lib/misc/dnsmasq.leases",
        "/var/lib/dnsmasq/leases",
        "/var/lib/dnsmasq/dnsmasq.leases"
    ]
    
    for lease_file in lease_files:
        if os.path.exists(lease_file):
            try:
                with open(lease_file, "r") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 4:
                            clients.append({
                                "ip": parts[3] if len(parts) > 3 else "N/A",
                                "mac": parts[1] if len(parts) > 1 else "N/A",
                                "hostname": parts[2] if len(parts) > 2 else "Unknown"
                            })
            except:
                pass
    
    return clients

def generate_qr_code(ssid, password):
    """Generate QR code for hotspot"""
    qr_file = "/tmp/hotspot_qr.png"
    
    if password:
        qr_string = f"WIFI:T:WPA;S:{ssid};P:{password};;"
    else:
        qr_string = f"WIFI:T:nopass;S:{ssid};;"
    
    subprocess.run(
        ["qrencode", "-o", qr_file, qr_string],
        capture_output=True
    )
    
    return qr_file if os.path.exists(qr_file) else None

def get_hotspot_info():
    """Get current hotspot information"""
    running, pid, tool = get_hotspot_status()
    
    if not running:
        return {"status": "stopped"}
    
    return {
        "status": "running",
        "pid": pid,
        "tool": tool,
        "interface": get_default_interface()
    }

def get_available_channels(band="2.4"):
    """Get available WiFi channels"""
    output, _ = run_cmd(["nmcli", "-t", "device", "wifi", "list"])
    channels = set()
    
    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 4:
            chan = parts[3]
            try:
                c = int(chan)
                if band == "5":
                    if c >= 36:
                        channels.add(c)
                else:
                    if 1 <= c <= 14:
                        channels.add(c)
            except:
                pass
    
    return sorted(list(channels))
