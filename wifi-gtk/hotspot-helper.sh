#!/bin/bash
# Hotspot helper script for pkexec

ACTION="$1"
SSID="$2"
PASSWORD="$3"
IFACE="${4:-wlan0}"

case "$ACTION" in
    start)
        # Kill any conflicting processes
        pkill -9 hostapd 2>/dev/null
        pkill -9 dnsmasq 2>/dev/null
        sleep 1
        
        # Stop NM's wifi management for this interface
        nmcli device disconnect "$IFACE" 2>/dev/null
        sleep 1
        
        # Start create_ap
        create_ap "$IFACE" "$IFACE" "$SSID" "$PASSWORD" --no-virt --nat &
        sleep 3
        
        if create_ap "$IFACE" "$IFACE" "$SSID" "$PASSWORD" --no-virt --nat 2>&1; then
            echo "SUCCESS: Hotspot started"
        else
            echo "FAILED"
        fi
        ;;
    stop)
        pkill -9 create_ap 2>/dev/null
        sleep 1
        
        # Restart NM wifi
        nmcli device wifi on
        echo "SUCCESS: Hotspot stopped"
        ;;
    status)
        if pgrep -f "create_ap.*$IFACE" > /dev/null; then
            echo "RUNNING"
        else
            echo "STOPPED"
        fi
        ;;
esac
