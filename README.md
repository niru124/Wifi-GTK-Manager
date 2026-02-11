# WiFi GTK Manager

A native GTK3 WiFi manager with full NetworkManager integration, QR code support, and live speed monitoring.

![Main Window](assets/homepage.png)

## Features

- **Scan & Connect** - List available WiFi networks with signal strength
- **Live Speed Monitoring** - Real-time TX/RX speed display in header
- **WiFi Toggle** - Turn WiFi on/off directly from the app
- **QR Code Generation** - Share WiFi with smartphone camera scan
- **Connection Details** - View IP, Gateway, DNS, Signal dBm
- **Auto-Connect Toggle** - Enable/disable auto-connect for networks
- **Forget Networks** - Remove saved network profiles
- **Sort Networks** - By Signal Strength, Name, or Security
- **Hotspot Creation** - Native NetworkManager hotspot support
- **Persistent Settings** - Preferences saved between sessions
- **Custom Icons** - Bundled SVG icons for consistent look

## Installation

### Ubuntu/Debian

```bash
sudo apt install network-manager nmcli qrencode python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

### Arch Linux

```bash
sudo pacman -S networkmanager nmcli qrencode python-gobject gtk3
```

### Setup

```bash
cd /home/nirantar/Downloads/nm-applet/wifi-gtk
chmod +x wifi-manager.py
```

## Usage

```bash
python3 wifi-manager.py
```

## Icons

The application uses bundled SVG icons for consistent appearance:

| Icon | File | Used For |
|------|------|----------|
| Hotspot | `hotspot-rectangles-symbolic.svg` | Hotspot button |
| QR Code | `qr-code-scanner-symbolic.svg` | QR code button |
| Connect | `plug-symbolic.svg` | Connect button |
| Disconnect | `unplug-dots-symbolic.svg` | Disconnect button |
| Refresh | `arrow-circular-bottom-right-symbolic.svg` | Refresh button |

Add more SVG icons to the `icons/` directory and update `SVG_ICON_MAP` in `dialogs.py`.

## Screenshots

### Connection Info Dialog

![Connection Info](assets/info.png)

### QR Code Feature

![QR Code](assets/QR.png)

### Settings Dialog

![Settings](assets/settings.png)

## Features Overview

### Main Window

```
┌─────────────────────────────────────────────────────┐
│ [📶 Hotspot]  WiFi: [ON●]  📶 GrassHopper  [⚙ Settings] │
├─────────────────────────────────────────────────────┤
│ ↓125 KB/s  ↑45 KB/s                                │
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

### Header Bar Features

| Element            | Description                                |
|--------------------|--------------------------------------------|
| Hotspot Button     | Opens dedicated hotspot configuration page |
| WiFi Toggle        | Switch to enable/disable WiFi radio        |
| Live Speed         | Real-time download/upload speeds           |
| Current SSID       | Shows connected network name               |
| Settings           | Opens preferences dialog                   |

### Settings Dialog

![Settings](assets/settings.png)

Settings include:
- **Auto-Connect** - Toggle automatic connection to current network
- **Live Speed Display** - Show/hide TX/RX speeds in header

Settings are saved to `~/.config/wifi-manager/settings.conf`

### Connection Details

![Connection Info](assets/info.png)

View detailed information:
- Network name (SSID)
- Signal strength (%, dBm)
- Connection speed
- IP address, Gateway, DNS servers
- Auto-connect status

### QR Code Feature

![QR Code](assets/QR.png)

Generate QR codes for easy smartphone connection. Format:
```
WIFI:T:WPA2;S:NetworkName;P:Password;;
```

Scan with your phone camera to connect instantly.

### Hotspot Page

Click **[📶 Hotspot]** button to open dedicated hotspot configuration:

```
┌─────────────────────────────────────────────────────┐
│ [← Back]  <b><big>WiFi Hotspot</big></b>              │
├─────────────────────────────────────────────────────┤
│ ○ <b>Status:</b> Not running                          │
│                                                      │
│ ┌─ Create Hotspot ─────────────────────────────────┐ │
│ │ Network Name (SSID):                              │ │
│ │ [MyHotspot__________________________________]    │ │
│ │                                                  │ │
│ │ Password:                                        │ │
│ │ [**********_______________] [☐ Show password]   │ │
│ │                                                  │ │
│ │ [▶ Start Hotspot]                                │ │
│ └──────────────────────────────────────────────────┘ │
│                                                      │
│ ┌─ Quick Actions ──────────────────────────────────┐ │
│ │ This hotspot uses NetworkManager's built-in       │ │
│ │ feature. Other devices can connect to share       │ │
│ │ your internet connection.                         │ │
│ │                                                  │ │
│ │ [■ Stop Hotspot]                                 │ │
└─────────────────────────────────────────────────────┘
```

### WiFi Toggle

The WiFi toggle switch in the header allows you to:

- **Turn OFF** - Disable WiFi radio (stops all WiFi connections)
- **Turn ON** - Enable WiFi radio and automatically scan for networks

When WiFi is turned on, the app automatically starts scanning for available networks.

## Project Structure

```
wifi-gtk/
├── wifi-manager.py              # Main GTK3 application
├── wifi_manager/                 # Python package
│   ├── __init__.py            # Package init
│   ├── wifi_manager.py         # Main window
│   ├── nmcli_utils.py          # nmcli wrappers
│   ├── qr_utils.py             # QR code utilities
│   ├── dialogs.py             # GTK dialogs
│   ├── hotspot_utils.py        # Hotspot utilities
│   └── hotspot_dialog.py       # Hotspot page
├── icons/                        # Bundled SVG icons
│   ├── hotspot-rectangles-symbolic.svg
│   ├── qr-code-scanner-symbolic.svg
│   ├── plug-symbolic.svg
│   ├── unplug-dots-symbolic.svg
│   └── arrow-circular-bottom-right-symbolic.svg
├── assets/                      # Screenshots
│   ├── homepage.png
│   ├── info.png
│   ├── QR.png
│   └── settings.png
├── wifi-manager.sh              # YAD version
├── wifi-manager-zenity.sh       # Zenity version
└── README.md
```

## Requirements

| Component      | Ubuntu/Debian   | Arch Linux     |
| -------------- | --------------- | -------------- |
| Python         | python3         | python         |
| GObject        | python3-gi      | python-gobject |
| GTK            | gir1.2-gtk-3.0  | gtk3           |
| nmcli          | nmcli           | nmcli          |
| NetworkManager | network-manager | networkmanager |
| QR Code        | qrencode        | qrencode       |

## License

MIT License
