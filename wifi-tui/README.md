# WiFi TUI Manager

A terminal-based WiFi manager built with Gum that provides all essential NetworkManager functionality with QR code support.

## Features

- Scan and list available WiFi networks
- Connect to protected and open networks
- View current connection details
- Generate and display QR codes for WiFi networks
- Disconnect from networks
- Signal strength visualization
- Security type indication

## Requirements

- Go 1.20+
- [Gum](https://github.com/charmbracelet/gum) - Terminal UI library
- NetworkManager (`nmcli`)
- qrencode - For generating QR codes
- kitten (from [kitty](https://sw.kovidgoyal.net/kitty/)) - For displaying QR codes in terminal

## Installation

```bash
# Install dependencies
go get github.com/charmbracelet/gum

# Build
go build -o wifi-tui main.go

# Run
./wifi-tui
```

## QR Code Format

The QR codes are generated using the standard WiFi QR code format:
```
WIFI:T:WPA;S:NetworkName;P:Password;;
```

This allows you to scan the QR code with any smartphone camera to connect to the WiFi network.

## Controls

- Arrow keys to navigate
- Enter to select
- View QR codes for current or any saved network
- Refresh to rescan networks

## Screenshot

```
┌─────────────────────────────────────────────────┐
│ WiFi Manager - Connected: GrassHopper          │
│                                                 │
│  ● GrassHopper ▂▄▆_ WPA2                       │
│  ○ FlowerPot   ▂▄▆█ WPA2                       │
│  ○ DEBANGSHI   ▂▄▆_ WPA2                       │
│  ○ Krishana    ▂▄▆_ WPA2                       │
│  ○ sumit       ▂▄__ WPA2                       │
│  ○ Jio_2       ▂▄__ WPA2                       │
│  ○ ARYAV-4G    ▂▄__ WPA2                       │
│  ○ Yash        ▂▄__ WPA2                       │
│  ○ ADI-LINK    ▂▄__ WPA2                       │
│  ○ Realme C1   ▂▄__ WPA2                       │
│                                                 │
│  🔄 Refresh Networks                            │
│  📱 Show QR Code (Current)                      │
│  ❌ Exit                                        │
└─────────────────────────────────────────────────┘
```
