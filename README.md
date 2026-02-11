# WiFi GTK Manager

A native GTK3 WiFi manager with full NetworkManager integration and QR code support.

## Features

- Scan and list available WiFi networks with signal strength
- Connect to protected and open networks
- View current connection details with speed/latency info
- **Generate and display QR codes** for easy smartphone connection
- Disconnect from networks
- **Sort networks** by Signal Strength, Name, or Security
- **Auto-connect toggle** in Settings
- **Forget saved networks**
- **Hotspot creation** with dedicated configuration page
- Native GTK3 interface

## Installation

### Dependencies
```bash
sudo apt install network-manager nmcli qrencode python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

### Setup
```bash
cd /home/nirantar/Downloads/nm-applet/wifi-gtk
chmod +x wifi-manager.py
```

## Usage

### GUI Application (Recommended)
```bash
python3 wifi-manager.py
```

### YAD Version
```bash
chmod +x wifi-manager.sh
./wifi-manager.sh
```

### Zenity Version
```bash
chmod +x wifi-manager-zenity.sh
./wifi-manager-zenity.sh
```

## Features Overview

### Main Window
```
┌─────────────────────────────────────────────────────┐
│ [📶 Hotspot]  📶 GrassHopper           [⚙ Settings] │
├─────────────────────────────────────────────────────┤
│ <small>Found 15 networks</small>                     │
│ ┌───────────────────────────────────────────────┐  │
│ │ Network        Signal  Security     Connected   │  │
│ │ ● GrassHopper  80%     WPA2       ✓        │  │
│ │ ○ FlowerPot    85%     WPA2                  │  │
│ │ ○ DEBANGSHI   60%     WPA2                  │  │
│ └───────────────────────────────────────────────┘  │
│                                                      │
│ Sort by: [Signal Strength ▼]                         │
├─────────────────────────────────────────────────────┤
│ [🔄 Refresh] [🔗 Connect] [❌ Disconnect] [📱 QR]     │
│ [ℹ Details]  [🗑 Forget]                            │
└─────────────────────────────────────────────────────┘
```

### Hotspot Creation

Click **[📶 Hotspot]** button to open dedicated hotspot page:

```
┌─────────────────────────────────────────────────────┐
│ [← Back]  <b><big>Hotspot Configuration</big></b>      │
├─────────────────────────────────────────────────────┤
│ 🔴 <b>Status:</b> Not running                          │
│                                                      │
│ ┌─ Create Hotspot ─────────────────────────────────┐ │
│ │ Network Name (SSID):                              │ │
│ │ [MyHotspot__________________________________]    │ │
│ │                                                  │ │
│ │ Password:                                        │ │
│ │ [**********_______________] [☐ Show password]   │ │
│ │                              [☐ Random password]│ │
│ │                                                  │ │
│ │ Band: [2.4 GHz ▼]                               │ │
│ │ Channel: [Auto ▼]                               │ │
│ │ Interface: [wlan0 ▼]                            │ │
│ │                                                  │ │
│ │ [▶ Start Hotspot] [■ Stop Hotspot] [💾 Save]    │ │
│ └──────────────────────────────────────────────────┘ │
│                                                      │
│ ┌─ Saved Profiles ─────────────────────────────────┐ │
│ │ Profile Name      SSID                           │ │
│ │ hotspot-MyHotspot MyHotspot                      │ │
│ │                                                  │ │
│ │ [▶ Activate] [🗑 Delete]                        │ │
│ │                                                  │ │
│ │ Quick Start: [◉ Turn On] [○ Turn Off]           │ │
└─────────────────────────────────────────────────────┘
```

### Hotspot Options

| Option | Description |
|--------|-------------|
| **Network Name** | SSID for your hotspot |
| **Password** | WPA2 password (min 8 chars) |
| **Show Password** | Toggle password visibility |
| **Random Password** | Generate secure random password |
| **Band** | 2.4 GHz, 5 GHz, or both |
| **Channel** | Specific channel or Auto |
| **Interface** | WiFi interface to use |
| **Start** | Launch the hotspot immediately |
| **Stop** | Shutdown running hotspot |
| **Save Profile** | Save configuration for later use |

### Quick Actions

- **◉ Turn On** - Start last used hotspot
- **○ Turn Off** - Stop running hotspot
- **Activate** - Use saved profile
- **Delete** - Remove saved profile

### Settings

Click **[⚙ Settings]** to:
- Toggle auto-connect for current network
- View saved network profiles

### Connection Details

Click **[ℹ Details]** to see:
- Signal strength (%, dBm)
- Connection speed
- IP address, Gateway, DNS
- Auto-connect status

### Forget Networks

- Select any saved network
- Click "Forget" to remove profile

## QR Code Feature

The app generates WiFi QR codes using the standard format:
```
WIFI:T:WPA2;S:NetworkName;P:Password;;
```

Simply scan with your smartphone camera to connect!

## Project Structure

```
wifi-gtk/
├── wifi-manager.py              # Launcher script
├── wifi_manager/                 # Main package
│   ├── __init__.py            # Package init
│   ├── wifi_manager.py         # Main window
│   ├── nmcli_utils.py          # nmcli command wrappers
│   ├── qr_utils.py             # QR code utilities
│   ├── dialogs.py             # GTK dialogs
│   ├── hotspot_utils.py        # Hotspot utilities
│   └── hotspot_dialog.py       # Hotspot configuration page
├── wifi-manager.sh              # YAD version
├── wifi-manager-zenity.sh       # Zenity version
└── wifi-manager.desktop         # Desktop entry
```

## Requirements

| Component | Required For |
|-----------|-------------|
| Python 3 + GObject | wifi-manager.py |
| YAD | wifi-manager.sh |
| Zenity | wifi-manager-zenity.sh |
| nmcli | All versions |
| qrencode | QR code generation |
| ImageMagick | QR display in YAD version |

## License

MIT License
