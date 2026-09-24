"""Generic portable hotspot utilities.

No hardware is hardcoded. Everything is discovered at runtime via
nmcli / iw / ip so other users on other machines work unchanged.

Two paths:
  1. Ethernet (or second radio) -> WiFi AP : native NetworkManager AP profile.
  2. WiFi -> WiFi on the SAME radio : virtual __ap interface + NM profile
     locked to the STA channel (what Windows does automatically), with
     fallback to lnxrouter / create_ap if present.
"""

import os
import re
import subprocess
import signal
import time

HOTSPOT_PROCESS = None
AP_CON_PREFIX = "Hotspot-"
MANAGED_VIRT_PREFIX = "ap"
HOTSPOT_SETTINGS_DIR = os.path.expanduser("~/.config/wifi-manager")
HOTSPOT_SETTINGS_FILE = os.path.join(HOTSPOT_SETTINGS_DIR, "hotspot.conf")


def run_cmd(args, timeout=10):
    """Run a command, return (stdout, ok). Never raises."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        print(f"Error running command {args}: {e}")
        return "", False


# ---------------------------------------------------------------- frequency

def freq_to_channel(freq_mhz):
    """Convert frequency MHz (float/str) to 802.11 channel. None if unknown."""
    try:
        f = float(str(freq_mhz).strip().split()[0])
    except Exception:
        return None
    # 2.4 GHz
    if 2411 <= f <= 2485:
        if abs(f - 2484.0) < 1:
            return 14
        return int(round((f - 2407) / 5))
    # 5 GHz
    for ch in (36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116,
               120, 124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165):
        if abs(f - (5000 + ch * 5)) < 2:
            return ch
    # 6 GHz (approx)
    if 5925 <= f <= 7125:
        return int(round((f - 5950) / 5))
    return None


def channel_to_band(channel):
    """Return 'bg' (2.4GHz) or 'a' (5/6GHz) for NM. None = auto."""
    try:
        c = int(channel)
    except Exception:
        return None
    if 1 <= c <= 14:
        return "bg"
    if c >= 36:
        return "a"
    return None


def channels_for_band(band):
    """Generic channel lists (no hardware probing). 0 = Auto."""
    if band == "5":
        return [0, 36, 40, 44, 48, 149, 153, 157, 161, 165]
    return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]


# ---------------------------------------------------------------- devices

def get_device_states():
    """Parse `nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status`.

    Returns list of dicts: {device, type, state, connection}.
    """
    out, _ = run_cmd(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION",
                      "device", "status"])
    devices = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(":", 3)
        while len(parts) < 4:
            parts.append("")
        devices.append({
            "device": parts[0].strip(),
            "type": parts[1].strip(),
            "state": parts[2].strip(),
            "connection": parts[3].strip(),
        })
    return devices


def list_wifi_interfaces():
    """All wifi netdevs from NM, fallback to `iw dev`."""
    devs = [d["device"] for d in get_device_states()
            if d["type"] == "wifi" and d["device"]]
    if devs:
        return devs
    out, _ = run_cmd(["iw", "dev"])
    found = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Interface "):
            found.append(line.split(None, 1)[1].strip())
    # filter out p2p-dev-* which also shows in `iw dev`
    return [i for i in found if not i.startswith("p2p-dev-")]


def list_ethernet_interfaces():
    """All ethernet netdevs known to NM."""
    return [d["device"] for d in get_device_states()
            if d["type"] == "ethernet" and d["device"]]


def list_upstream_candidates():
    """Interfaces that can provide internet (connected ethernet/wifi).

    Returns list of dicts {device, type, connection}. Includes
    disconnected ones too (marked) so the UI can show Auto + all.
    """
    devices = get_device_states()
    cands = [d for d in devices if d["type"] in ("ethernet", "wifi")]
    # Prefer connected first, keep stable order
    cands.sort(key=lambda d: (d["state"] != "connected", d["type"], d["device"]))
    return cands


def get_default_route_iface():
    """Interface of the default route, e.g. wlan0 / eno1. None if unknown."""
    out, ok = run_cmd(["ip", "route", "show", "default"])
    if not ok or not out:
        return None
    for line in out.splitlines():
        parts = line.split()
        if "dev" in parts:
            try:
                return parts[parts.index("dev") + 1]
            except IndexError:
                pass
    return None


def get_default_interface():
    """Legacy helper: first wifi iface, else default route, else wlan0."""
    wifis = list_wifi_interfaces()
    if wifis:
        return wifis[0]
    route = get_default_route_iface()
    return route or "wlan0"


def get_wifi_interface():
    """Legacy alias."""
    return list_wifi_interfaces()


# ---------------------------------------------------------------- STA info

def get_sta_link_info(iface):
    """Return {ssid, freq, channel} for a managed STA iface, via `iw dev link`.

    Empty dict values (None) if not connected.
    """
    out, _ = run_cmd(["iw", "dev", iface, "link"])
    info = {"ssid": None, "freq": None, "channel": None}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("SSID:"):
            info["ssid"] = line.split(":", 1)[1].strip()
        if line.startswith("freq:"):
            try:
                info["freq"] = float(line.split(":", 1)[1].strip().split()[0])
                info["channel"] = freq_to_channel(info["freq"])
            except Exception:
                pass
    return info


def get_current_sta_channel(iface):
    """Channel number of STA connection, or None."""
    return get_sta_link_info(iface).get("channel")


# ---------------------------------------------------------------- concurrency

def parse_concurrent_support():
    """Parse `iw list` valid interface combinations.

    Returns (sta_plus_ap, must_share_channel, raw_text).
    Generic: looks for any combination line containing both
    'managed' and 'AP'.
    """
    out, ok = run_cmd(["iw", "list"])
    if not ok or not out:
        return False, True, ""
    # Find blocks like: * #{ managed } <= 1, #{ AP } <= 1 ... #channels <= 1
    supported = False
    share_only = True
    for m in re.finditer(r"#\{([^}]*)\}[^*\n]*#channels\s*<=\s*(\d+)",
                         out):
        combos, nchan = m.group(1), m.group(0)
        # The regex above only captures last #{...}; instead inspect full line.
        line_start = out.rfind("*", 0, m.start())
        line = out[line_start:m.end()] if line_start != -1 else m.group(0)
        low = line.lower()
        if "managed" in low and (" ap" in low or "{ ap" in low or ", ap" in low
                                 or "ap," in low or "ap }" in low):
            try:
                n = int(m.group(2))
            except Exception:
                n = 1
            supported = True
            if n > 1:
                share_only = False
    # Fallback simpler scan if regex missed multi-line combos
    if not supported:
        for chunk in out.split("*"):
            low = chunk.lower()
            if "managed" in low and re.search(r"\bap\b", low) and \
                    "valid interface combinations" not in low:
                # must be a combination line (contains #{ and #channels)
                if "#{" in chunk and "#channels" in chunk:
                    supported = True
                    mc = re.search(r"#channels\s*<=\s*(\d+)", chunk)
                    if mc and int(mc.group(1)) > 1:
                        share_only = False
    return supported, share_only, out


def supports_concurrent_ap_sta():
    """(supported: bool, must_share_channel: bool)."""
    s, share, _ = parse_concurrent_support()
    return s, share


# ---------------------------------------------------------------- virtual AP iface

def _has_bin(name):
    out, ok = run_cmd(["which", name])
    return ok and bool(out)


def _run_with_priv_fallback(args, timeout=10):
    """Run args; on permission error retry via pkexec/sudo (GUI-friendly)."""
    out, ok = run_cmd(args, timeout=timeout)
    if ok:
        return out, True
    low = (out or "").lower()
    if os.geteuid() == 0 or ("permit" not in low and "denied" not in low
                             and "not supported" in low or "no such device" in low):
        # 'not supported' / missing device are real errors, don't escalate
        if "not supported" in low or "no such device" in low:
            return out, False
    if "permit" not in low and "denied" not in low and "busy" not in low:
        # other errors (e.g. file exists) -> return as-is
        if "exists" in low or "busy" in low:
            return out, False
    if _has_bin("pkexec"):
        out2, ok2 = run_cmd(["pkexec"] + list(args), timeout=timeout)
        if ok2 or out2:
            return out2, ok2
    if _has_bin("sudo"):
        out2, ok2 = run_cmd(["sudo", "-n"] + list(args), timeout=timeout)
        if ok2:
            return out2, ok2
        # interactive sudo (may prompt in terminal)
        out2, ok2 = run_cmd(["sudo"] + list(args), timeout=timeout)
        return out2, ok2
    return out, False


def list_ap_interfaces():
    """Interfaces currently in AP mode (via `iw dev`)."""
    out, _ = run_cmd(["iw", "dev"])
    aps = []
    cur = None
    cur_type = None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Interface "):
            cur = s.split(None, 1)[1].strip()
            cur_type = None
        elif s.startswith("type ") and cur:
            cur_type = s.split(None, 1)[1].strip()
            if cur_type == "AP" and cur and not cur.startswith("p2p-dev-"):
                aps.append(cur)
            cur = None
    return aps


def ensure_virtual_ap(sta_iface, prefix=MANAGED_VIRT_PREFIX):
    """Create `<prefix>_sta` style __ap interface on same phy as sta_iface.

    Returns new iface name, or existing AP iface on same phy, or None.
    """
    if not sta_iface:
        return None
    # Reuse an existing AP iface if already present
    existing = list_ap_interfaces()
    if existing:
        return existing[0]
    base = f"{prefix}_{sta_iface}" if sta_iface else f"{prefix}0"
    # iw limits to 15 chars
    base = base[:15]
    name = base
    for i in range(5):
        out, ok = _run_with_priv_fallback(
            ["iw", "dev", sta_iface, "interface", "add",
             name, "type", "__ap"])
        if ok:
            return name
        # name collision -> try suffix
        name = (base[:13] + str(i))[:15]
        # "Device or resource busy" / "not supported" -> give up
        if "not supported" in out.lower() or "operation not supported" in out.lower():
            return None
    return None


def remove_virtual_ap(iface):
    """Delete a virtual interface created by ensure_virtual_ap."""
    if not iface:
        return False
    _, ok = _run_with_priv_fallback(["iw", "dev", iface, "del"])
    return ok


# ---------------------------------------------------------------- NM AP profiles

def get_active_ap():
    """Active NM AP connection, if any.

    Returns {name, device, ssid} or None.
    """
    out, _ = run_cmd(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE",
                      "connection", "show", "--active"])
    for line in out.splitlines():
        parts = line.strip().split(":")
        if len(parts) >= 3 and parts[1] in ("802-11-wireless", "wifi"):
            name = parts[0]
            dev = parts[2]
            # confirm mode == ap
            mout, _ = run_cmd(["nmcli", "-t", "-f", "802-11-wireless.mode",
                               "connection", "show", name])
            if "ap" in mout.lower():
                sout, _ = run_cmd(["nmcli", "-t", "-f", "802-11-wireless.ssid",
                                   "connection", "show", name])
                ssid = sout.split(":", 1)[1].strip() if ":" in sout else name
                return {"name": name, "device": dev, "ssid": ssid}
    # older NM prints ":hotspot:" in tab-complete form
    out2, _ = run_cmd(["nmcli", "-t", "connection", "show", "--active"])
    for line in out2.splitlines():
        if ":hotspot:" in line:
            name = line.split(":")[0]
            return {"name": name, "device": "", "ssid": name}
    return None


def _con_name_for_ssid(ssid):
    # sanitize: NM allows most chars, keep readable
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", ssid.strip()) or "hotspot"
    return f"{AP_CON_PREFIX}{safe}"


def create_or_update_nm_hotspot(ap_iface, ssid, password, band="auto",
                                channel=0, con_name=None):
    """Create/replace an NM wifi AP profile with shared IPv4.

    band: 'auto' | '2.4' | '5'. channel: 0 = auto.
    Returns (ok, message).
    """
    if not ap_iface or not ssid:
        return False, "AP interface and SSID are required"
    if password and len(password) < 8:
        return False, "Password must be at least 8 characters (or empty for open)"
    con_name = con_name or _con_name_for_ssid(ssid)
    run_cmd(["nmcli", "connection", "delete", con_name])

    cmd = ["nmcli", "connection", "add", "type", "wifi", "ifname", ap_iface,
           "con-name", con_name, "autoconnect", "no",
           "802-11-wireless.mode", "ap", "802-11-wireless.ssid", ssid]
    _, ok = run_cmd(cmd)
    if not ok:
        return False, "nmcli failed to create AP profile"

    if band == "2.4":
        run_cmd(["nmcli", "connection", "modify", con_name,
                 "802-11-wireless.band", "bg"])
    elif band == "5":
        run_cmd(["nmcli", "connection", "modify", con_name,
                 "802-11-wireless.band", "a"])
    else:
        run_cmd(["nmcli", "connection", "modify", con_name,
                 "802-11-wireless.band", ""])

    if channel and int(channel) > 0:
        run_cmd(["nmcli", "connection", "modify", con_name,
                 "802-11-wireless.channel", str(int(channel))])
    else:
        run_cmd(["nmcli", "connection", "modify", con_name,
                 "802-11-wireless.channel", "0"])

    if password:
        run_cmd(["nmcli", "connection", "modify", con_name,
                 "802-11-wireless-security.key-mgmt", "wpa-psk",
                 "802-11-wireless-security.psk", password])
    else:
        run_cmd(["nmcli", "connection", "modify", con_name,
                 "802-11-wireless-security.key-mgmt", "none"])

    run_cmd(["nmcli", "connection", "modify", con_name,
             "ipv4.method", "shared", "ipv6.method", "ignore"])
    return True, con_name


def activate_hotspot(con_name, ap_iface=None):
    """Bring an NM hotspot profile up. Returns (ok, msg)."""
    cmd = ["nmcli", "connection", "up", con_name]
    if ap_iface:
        cmd += ["ifname", ap_iface]
    out, ok = run_cmd(cmd, timeout=20)
    if ok:
        return True, out or f"'{con_name}' activated"
    return False, out or f"Failed to activate '{con_name}'"


def deactivate_hotspot(con_name):
    """Bring an NM hotspot profile down."""
    _, ok = run_cmd(["nmcli", "connection", "down", con_name], timeout=15)
    return ok


# ---------------------------------------------------------------- external tools

def get_tool():
    """Check which helper (lnxrouter / create_ap) exists. (legacy name)."""
    r = subprocess.run(["which", "lnxrouter"], capture_output=True, text=True)
    if r.returncode == 0:
        return "lnxrouter", r.stdout.strip()
    r = subprocess.run(["which", "create_ap"], capture_output=True, text=True)
    if r.returncode == 0:
        return "create_ap", r.stdout.strip()
    return None, None


def get_hotspot_status():
    """Legacy (running, pid, tool) + NM AP awareness.

    Returns (running: bool, pid_or_conname, tool: str|None).
    """
    global HOTSPOT_PROCESS
    tool, _ = get_tool()
    if HOTSPOT_PROCESS and HOTSPOT_PROCESS.poll() is None:
        return True, HOTSPOT_PROCESS.pid, tool
    for proc_name in ["lnxrouter", "create_ap", "hostapd"]:
        result = subprocess.run(["pgrep", "-f", proc_name],
                                capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            try:
                pid = int(result.stdout.strip().split()[0])
            except Exception:
                pid = result.stdout.strip().split()[0]
            return True, pid, proc_name if proc_name == "hostapd" else tool
    ap = get_active_ap()
    if ap:
        return True, ap["name"], "networkmanager"
    # Generic hostapd / manual AP (e.g. virtual __ap iface with an SSID)
    for iface in list_ap_interfaces():
        out, _ = run_cmd(["iw", "dev", iface, "info"])
        if "ssid" in out.lower():
            return True, iface, "hostapd"
    return False, None, tool


def get_hotspot_info():
    """Dict describing current hotspot (generic)."""
    running, ident, tool = get_hotspot_status()
    if not running:
        return {"status": "stopped"}
    ap = get_active_ap()
    info = {"status": "running", "tool": tool, "id": ident,
            "interface": get_default_interface()}
    if ap:
        info.update({"connection": ap["name"], "ssid": ap["ssid"],
                     "interface": ap.get("device") or info["interface"]})
    else:
        aps = list_ap_interfaces()
        if aps:
            info["interface"] = aps[0]
            out, _ = run_cmd(["iw", "dev", aps[0], "info"])
            for line in out.splitlines():
                if line.strip().lower().startswith("ssid"):
                    info["ssid"] = line.split(None, 1)[1].strip() \
                        if len(line.split(None, 1)) > 1 else ""
                    break
    return info


def stop_hotspot():
    """Stop any hotspot we started (NM AP + helpers + virt iface cleanup)."""
    global HOTSPOT_PROCESS
    if HOTSPOT_PROCESS and HOTSPOT_PROCESS.poll() is None:
        try:
            os.killpg(os.getpgid(HOTSPOT_PROCESS.pid), signal.SIGTERM)
            HOTSPOT_PROCESS.wait(timeout=5)
        except Exception:
            pass
        HOTSPOT_PROCESS = None
    for proc_name in ["lnxrouter", "create_ap"]:
        subprocess.run(["pkill", "-f", proc_name], capture_output=True)
        if _has_bin("pkexec"):
            subprocess.run(["pkexec", "pkill", "-f", proc_name],
                           capture_output=True)
        else:
            subprocess.run(["sudo", "pkill", "-f", proc_name],
                           capture_output=True)
    # create_ap's own stop (needs root for its dnsmasq/hostapd children)
    for iface in list_ap_interfaces() + list_wifi_interfaces():
        if _has_bin("pkexec"):
            subprocess.run(["pkexec", "create_ap", "--stop", iface],
                           capture_output=True)
            break
    ap = get_active_ap()
    if ap and ap["name"].startswith(AP_CON_PREFIX):
        deactivate_hotspot(ap["name"])
    return True


def _start_via_helper(ssid, password, sta_iface, band, channel):
    """Fallback: lnxrouter / create_ap sharing the same iface."""
    global HOTSPOT_PROCESS
    tool, _ = get_tool()
    if not tool:
        return False, "No helper found. Install linux-router or linux-wifi-hotspot, or use Ethernet uplink."
    stop_hotspot()
    if tool == "lnxrouter":
        return _create_lnxrouter(ssid, password, sta_iface, band, channel)
    return _create_ap(ssid, password, sta_iface, band, channel)


def _priv_prefix():
    """Prefix needed to run a root-only helper from a GUI (user) process."""
    if os.geteuid() == 0:
        return []
    if _has_bin("pkexec"):
        return ["pkexec"]
    return ["sudo"]


def _create_lnxrouter(ssid, password, interface, band, channel):
    global HOTSPOT_PROCESS
    cmd = ["lnxrouter", "--ap", interface, ssid]
    if password:
        cmd += ["-p", password]
    cmd += ["--freq-band", "5" if band == "5" else "2.4"]
    if channel and int(channel) > 0:
        cmd += ["-c", str(int(channel))]
    # NB: no --no-virt here: same-radio sharing needs the virtual iface.
    cmd = _priv_prefix() + cmd
    try:
        HOTSPOT_PROCESS = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            preexec_fn=os.setsid)
        time.sleep(3)
        if HOTSPOT_PROCESS.poll() is None:
            return True, f"Hotspot '{ssid}' started on {interface} (lnxrouter)"
        out, err = HOTSPOT_PROCESS.communicate(timeout=5)
        detail = ((out or b"").decode(errors="ignore") + " " +
                  (err or b"").decode(errors="ignore")).strip()[:300]
        return False, f"Failed: {detail}"
    except Exception as e:
        return False, f"Error: {e}"


def _create_ap(ssid, password, interface, band, channel):
    global HOTSPOT_PROCESS
    # create_ap <wifi-if> <uplink-if> <ssid> [passphrase]; NAT is default
    # (-m nat). Same iface twice = repeater; needs its virtual iface,
    # so do NOT pass --no-virt here.
    cmd = ["create_ap", interface, interface, ssid]
    if password:
        cmd.append(password)
    cmd += ["-m", "nat"]
    if channel and int(channel) > 0:
        cmd += ["-c", str(int(channel))]
    else:
        cmd += ["--freq-band", "5" if band == "5" else "2.4"]
    cmd = _priv_prefix() + cmd
    try:
        HOTSPOT_PROCESS = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            preexec_fn=os.setsid)
        time.sleep(3)
        if HOTSPOT_PROCESS.poll() is None:
            return True, f"Hotspot '{ssid}' started on {interface} (create_ap)"
        out, err = HOTSPOT_PROCESS.communicate(timeout=5)
        detail = ((out or b"").decode(errors="ignore") + " " +
                  (err or b"").decode(errors="ignore")).strip()[:300]
        return False, f"Failed: {detail}"
    except Exception as e:
        return False, f"Error: {e}"


# ---------------------------------------------------------------- main entry

def create_hotspot(ssid, password="", interface=None, band="2.4", channel=0,
                   upstream=None):
    """Start a hotspot. Generic across hardware.

    ssid/password: AP credentials (password empty = open).
    interface: AP wifi iface, or None = auto-pick first wifi iface.
    band: 'auto' | '2.4' | '5'.
    channel: 0 = auto, else number.
    upstream: uplink iface name, or None = auto (default route).

    Returns (ok, message).
    """
    if not ssid or not ssid.strip():
        return False, "SSID is required"
    if password and len(password) < 8:
        return False, "Password must be >= 8 characters (or empty for open)"

    if band not in ("auto", "2.4", "5"):
        band = "2.4"
    try:
        channel = int(channel or 0)
    except Exception:
        channel = 0

    stop_hotspot()

    wifis = list_wifi_interfaces()
    if not wifis:
        return False, "No WiFi interface found"
    ap_iface = interface or wifis[0]
    if ap_iface not in wifis and ap_iface not in list_ap_interfaces():
        # allow virtual ap names that will be created below
        if interface:
            pass
        else:
            ap_iface = wifis[0]

    up = upstream or get_default_route_iface()
    up_type = None
    for d in get_device_states():
        if d["device"] == up:
            up_type = d["type"]
            break

    same_radio = (up is not None and up == ap_iface)

    # Case A: distinct uplink (ethernet or a second radio) -> plain NM AP
    if not same_radio:
        ok, con_or_msg = create_or_update_nm_hotspot(
            ap_iface, ssid.strip(), password, band, channel)
        if not ok:
            return False, con_or_msg
        return activate_hotspot(con_or_msg, ap_iface)

    # Case B: same-radio WiFi -> WiFi (Windows-style)
    supported, share_only, _ = parse_concurrent_support()
    if not supported:
        # Still try helper tools which implement their own virtual AP
        return _start_via_helper(ssid.strip(), password, ap_iface, band,
                                 channel)

    sta_chan = get_current_sta_channel(ap_iface)
    want_chan = sta_chan or channel
    if share_only and sta_chan and channel and int(channel) != sta_chan:
        return False, (
            f"Card must share one channel: STA is on {sta_chan}, "
            f"requested AP {channel}. Use Auto/channel {sta_chan}.")

    virt = ensure_virtual_ap(ap_iface)
    if not virt:
        return _start_via_helper(ssid.strip(), password, ap_iface, band,
                                 channel)
    eff_band = band
    if band == "auto" and want_chan:
        eff_band = "2.4" if 1 <= want_chan <= 14 else "5"
    ok, con_or_msg = create_or_update_nm_hotspot(
        virt, ssid.strip(), password,
        eff_band if eff_band in ("2.4", "5") else "auto",
        want_chan or 0)
    if not ok:
        return False, con_or_msg
    ok, msg = activate_hotspot(con_or_msg, virt)
    if ok:
        return True, msg + f" (shared with {up} on ch {want_chan or 'auto'})"
    # NM could not drive the virt iface (common) -> helper fallback
    remove_virtual_ap(virt)
    return _start_via_helper(ssid.strip(), password, ap_iface, band,
                             want_chan or channel)


def get_current_hotspot():
    """Legacy: (conn_name, ssid) or (None, None)."""
    ap = get_active_ap()
    if ap:
        return ap["name"], ap["ssid"]
    running, ident, _ = get_hotspot_status()
    if running:
        return str(ident), "Hotspot"
    return None, None


def get_wifi_device_status():
    """Legacy wifi status dict."""
    for d in get_device_states():
        if d["type"] == "wifi":
            return {"device": d["device"], "state": d["state"],
                    "connected": d["state"] == "connected"}
    return {"device": None, "state": "unknown", "connected": False}


# ---------------------------------------------------------------- clients

def _parse_station_dump(ap_iface):
    """Parse `iw dev <ap> station dump` -> {mac: {...}}."""
    out, ok = run_cmd(["iw", "dev", ap_iface, "station", "dump"])
    stations = {}
    if not ok or not out:
        return stations
    cur = None
    for line in out.splitlines():
        s = line.strip()
        m = re.match(r"Station\s+([0-9a-fA-F:]{17})", s)
        if m:
            cur = m.group(1).lower()
            stations[cur] = {"mac": cur, "rx_bytes": 0, "tx_bytes": 0,
                             "signal": None, "rx_bitrate": "",
                             "tx_bitrate": "", "connected_time": ""}
            continue
        if cur is None:
            continue
        ml = re.match(r"rx bytes:\s*(\d+)", s)
        if ml:
            stations[cur]["rx_bytes"] = int(ml.group(1))
            continue
        ml = re.match(r"tx bytes:\s*(\d+)", s)
        if ml:
            stations[cur]["tx_bytes"] = int(ml.group(1))
            continue
        ml = re.match(r"signal:\s*(-?\d+).*dBm", s)
        if ml:
            stations[cur]["signal"] = int(ml.group(1))
            continue
        ml = re.match(r"rx bitrate:\s*(.+)", s)
        if ml:
            stations[cur]["rx_bitrate"] = ml.group(1).strip()
            continue
        ml = re.match(r"tx bitrate:\s*(.+)", s)
        if ml:
            stations[cur]["tx_bitrate"] = ml.group(1).strip()
            continue
        ml = re.match(r"connected time:\s*(.+)", s)
        if ml:
            stations[cur]["connected_time"] = ml.group(1).strip()
    return stations


def _neigh_map(dev=None):
    """MAC -> IP via `ip neigh`. Optionally filtered to dev."""
    cmd = ["ip", "-o", "neigh", "show"]
    if dev:
        cmd += ["dev", dev]
    out, _ = run_cmd(cmd)
    mapping = {}
    for line in out.splitlines():
        # e.g. 192.168.12.10 dev ap0 lladdr aa:bb:... REACHABLE
        m = re.search(r"^(\S+)\s+dev\s+(\S+)\s+lladdr\s+([0-9a-fA-F:]{17})", line)
        if m:
            mapping[m.group(3).lower()] = {"ip": m.group(1),
                                           "dev": m.group(2)}
    return mapping


def _dnsmasq_leases():
    """MAC -> {ip, hostname} from known lease files (NM + standalone)."""
    leases = {}
    cands = [
        "/var/lib/NetworkManager/dnsmasq.leases",
        "/var/lib/NetworkManager/dnsmasq-shared.leases",
        "/var/lib/misc/dnsmasq.leases",
        "/var/lib/dnsmasq/dnsmasq.leases",
        "/var/lib/dnsmasq/leases",
        "/tmp/dnsmasq.leases",
    ]
    import glob as _glob
    cands += _glob.glob("/var/lib/NetworkManager/dnsmasq-*.leases")
    cands += _glob.glob("/tmp/dnsmasq*.leases")
    seen = set()
    for path in cands:
        if path in seen or not os.path.exists(path):
            continue
        seen.add(path)
        try:
            with open(path) as f:
                for line in f:
                    # duid/expiry/mac/ip/hostname/... (NM + dnsmasq variants)
                    p = line.split()
                    if len(p) >= 4:
                        mac = None
                        ip = None
                        host = "Unknown"
                        for tok in p:
                            if re.fullmatch(r"[0-9a-fA-F:]{17}", tok):
                                mac = tok.lower()
                            elif re.fullmatch(r"\d+\.\d+\.\d+\.\d+", tok):
                                ip = ip or tok
                        # dnsmasq format: expiry mac ip hostname
                        if len(p) >= 4 and re.fullmatch(r"[0-9a-fA-F:]{17}", p[1]):
                            mac, ip = p[1].lower(), p[2]
                            host = p[3] if len(p) > 3 and p[3] != "*" else "Unknown"
                        if mac and ip:
                            leases[mac] = {"ip": ip, "hostname": host}
        except Exception:
            continue
    return leases


def get_connected_clients(ap_iface=None):
    """List clients of the hotspot AP.

    Each: {mac, ip, hostname, rx_bytes, tx_bytes, signal,
           rx_bitrate, tx_bitrate, iface}.
    Works with NM shared mode, hostapd, lnxrouter, create_ap.
    """
    ifaces = list_ap_interfaces()
    if ap_iface:
        targets = [ap_iface]
    elif ifaces:
        targets = ifaces
    else:
        ap = get_active_ap()
        if ap and ap.get("device"):
            targets = [ap["device"]]
        else:
            # No AP anywhere -> not a hotspot client list. Do NOT fall
            # back to the STA iface (that would show the upstream AP
            # as a fake "client").
            return []

    leases = _dnsmasq_leases()
    clients = []
    for iface in targets:
        stations = _parse_station_dump(iface)
        neigh = _neigh_map(iface)
        neigh_all = _neigh_map(None)
        if stations:
            for mac, st in stations.items():
                entry = dict(st)
                entry["iface"] = iface
                if mac in neigh:
                    entry["ip"] = neigh[mac]["ip"]
                elif mac in neigh_all:
                    entry["ip"] = neigh_all[mac]["ip"]
                    entry["iface"] = neigh_all[mac]["dev"]
                elif mac in leases:
                    entry["ip"] = leases[mac]["ip"]
                else:
                    entry["ip"] = "N/A"
                entry["hostname"] = leases.get(mac, {}).get("hostname",
                                                            "Unknown")
                clients.append(entry)
        else:
            # No station info (e.g. no permission) -> show neigh/leases
            for mac, info in neigh.items():
                clients.append({
                    "mac": mac, "ip": info["ip"],
                    "hostname": leases.get(mac, {}).get("hostname", "Unknown"),
                    "rx_bytes": 0, "tx_bytes": 0, "signal": None,
                    "rx_bitrate": "", "tx_bitrate": "",
                    "connected_time": "", "iface": iface,
                })
    # de-dup by mac
    seen = {}
    for c in clients:
        seen[c["mac"]] = c
    return list(seen.values())


def get_available_channels(band="2.4"):
    """Channels seen in scan (legacy helper, generic)."""
    out, _ = run_cmd(["nmcli", "-t", "-f", "CHAN", "device", "wifi", "list"])
    channels = set()
    for line in out.splitlines():
        for tok in line.split(":"):
            try:
                c = int(tok.strip())
            except Exception:
                continue
            if band == "5":
                if c >= 36:
                    channels.add(c)
            elif 1 <= c <= 14:
                channels.add(c)
    return sorted(channels)


def format_bytes(n):
    """Human-readable byte counter."""
    try:
        n = int(n)
    except Exception:
        return "N/A"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n:.1f} TB"


# ---------------------------------------------------------------- profiles

def save_hotspot_profile(ssid, password, interface=None, band="2.4"):
    """Persist last-used hotspot settings (generic, portable)."""
    try:
        os.makedirs(HOTSPOT_SETTINGS_DIR, exist_ok=True)
        iface = interface or ""
        with open(HOTSPOT_SETTINGS_FILE, "w") as f:
            f.write(f"SSID={ssid}\nPASSWORD={password}\n"
                    f"INTERFACE={iface}\nBAND={band}\n")
        # legacy per-SSID dir kept for compat
        legacy_dir = os.path.expanduser("~/.config/wifi-hotspot")
        os.makedirs(legacy_dir, exist_ok=True)
        with open(os.path.join(legacy_dir, f"{ssid}.conf"), "w") as f:
            f.write(f"SSID={ssid}\nPASSWORD={password}\n"
                    f"INTERFACE={iface}\nBAND={band}\n")
        return True
    except Exception:
        return False


def load_hotspot_profile(ssid=None):
    """Load persisted hotspot settings. ssid=None -> last used."""
    path = HOTSPOT_SETTINGS_FILE
    if ssid:
        legacy = os.path.expanduser(f"~/.config/wifi-hotspot/{ssid}.conf")
        if os.path.exists(legacy):
            path = legacy
    if not os.path.exists(path):
        return None
    cfg = {}
    try:
        with open(path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    cfg[k.strip()] = v.strip()
    except Exception:
        return None
    return cfg or None


def get_saved_hotspots():
    """Legacy list of saved hotspot names."""
    d = os.path.expanduser("~/.config/wifi-hotspot")
    if not os.path.exists(d):
        return []
    return [f[:-5] for f in os.listdir(d) if f.endswith(".conf")]


def delete_hotspot_profile(ssid):
    """Legacy delete."""
    p = os.path.expanduser(f"~/.config/wifi-hotspot/{ssid}.conf")
    if os.path.exists(p):
        os.remove(p)
        return True
    return False


def generate_qr_code(ssid, password):
    """QR png for the hotspot (legacy helper)."""
    qr_file = "/tmp/hotspot_qr.png"
    qr = f"WIFI:T:WPA;S:{ssid};P:{password};;" if password else \
        f"WIFI:T:nopass;S:{ssid};;"
    subprocess.run(["qrencode", "-o", qr_file, qr], capture_output=True)
    return qr_file if os.path.exists(qr_file) else None
