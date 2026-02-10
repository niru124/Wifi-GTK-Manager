#!/bin/bash

# WiFi Manager using Zenity (GTK fallback)
# Requires: zenity, nmcli, qrencode

QR_FILE="/tmp/wifi_qr.png"

get_current_ssid() {
    nmcli -t connection show --active | grep "802-11-wireless" | head -1 | cut -d: -f1 | xargs -I {} nmcli -t connection show {} | grep "802-11-wireless.ssid" | cut -d: -f2
}

scan_networks() {
    nmcli -t device wifi list
}

parse_wifi_line() {
    local line="$1"
    # Output: SSID|SIGNAL|SECURITY
    echo "$line" | awk -F: '{
        bssid = $2
        ssid = $3
        mode = $4
        chan = $5
        rate = $6
        signal = $7
        bars = $8
        security = $9
        
        if (ssid == "") ssid = "Hidden Network"
        print ssid "|" signal "|" security
    }'
}

get_networks() {
    local output=$(scan_networks)
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        parse_wifi_line "$line"
    done <<< "$output"
}

show_qr_code() {
    local ssid="$1"
    local password="$2"
    local security="$3"
    
    local wifi_type="WPA"
    [ "$security" = "WEP" ] && wifi_type="WEP"
    [ "$(echo "$security" | grep -i WPA3)" != "" ] && wifi_type="WPA3"
    
    local qr_string="WIFI:T:${wifi_type};S:${ssid};P:${password};;"
    qrencode -o "$QR_FILE" "$qr_string"
    
    zenity --image="$QR_FILE" \
        --title="QR Code - $ssid" \
        --text="Network: $ssid\nType: $security\n\nScan to connect" \
        --width=350 \
        --height=400 \
        --ok-label="Close"
}

show_network_list() {
    local current_ssid=$(get_current_ssid)
    local networks=""
    
    while IFS=: read -r bssid ssid mode chan rate signal security in_use; do
        [ -z "$ssid" ] && ssid="Hidden Network"
        [ "$ssid" = "$current_ssid" ] && status="Connected" || status=""
        networks="$networks\n$ssid|$signal|$security|$status"
    done < <(scan_networks)
    
    if [ -z "$networks" ]; then
        zenity --info --title="WiFi Manager" --text="No networks found" --width=300
        return
    fi
    
    local selection=$(echo -e "$networks" | zenity --list \
        --title="WiFi Networks" \
        --width=550 \
        --height=400 \
        --text="Select a network:" \
        --column="Network" \
        --column="Signal" \
        --column="Security" \
        --column="Status" \
        --print-column=1 \
        --hide-column=1 \
        --ok-label="Connect" \
        --cancel-label="Close" \
        --extra-button="Disconnect" \
        --extra-button="Show QR" \
        --extra-button="Refresh")
    
    local exit=$?
    
    case $exit in
        0)  # Connect
            if [ -n "$selection" ]; then
                ssid="$selection"
                security=$(scan_networks | grep ":${ssid}:" | head -1 | awk -F: '{print $9}')
                
                if [ "$security" != "Open" ]; then
                    password=$(zenity --entry \
                        --title="Password" \
                        --text="Enter password for $ssid" \
                        --hide-text \
                        --width=300 \
                        --ok-label="Connect" \
                        --cancel-label="Cancel")
                    [ -z "$password" ] && return
                else
                    password=""
                fi
                
                if nmcli device wifi connect "$ssid" password "$password" 2>&1 | zenity --progress --title="Connecting" --text="Connecting to $ssid..." --pulsate --auto-close --width=300; then
                    zenity --info --title="Success" --text="Connected to $ssid" --width=300
                else
                    zenity --error --title="Error" --text="Failed to connect" --width=300
                fi
            fi
            ;;
        1)  # Close
            return
            ;;
        *)
            if [ "$selection" = "Disconnect" ]; then
                current=$(get_current_ssid)
                [ -n "$current" ] && nmcli connection down "$current" 2>/dev/null
            elif [ "$selection" = "Show QR" ]; then
                current=$(get_current_ssid)
                if [ -n "$current" ]; then
                    password=$(nmcli -t connection show "$current" | grep "802-11-wireless-security.psk" | cut -d: -f2)
                    security=$(scan_networks | grep ":${current}:" | head -1 | awk -F: '{print $9}')
                    show_qr_code "$current" "$password" "$security"
                fi
            elif [ "$selection" = "Refresh" ]; then
                show_network_list
            fi
            ;;
    esac
}

show_main_menu() {
    local current=$(get_current_ssid)
    local status="Not Connected"
    [ -n "$current" ] && status="Connected: $current"
    
    zenity --question \
        --title="WiFi Manager" \
        --width=400 \
        --height=200 \
        --image="network-wireless" \
        --text="<b>WiFi Network Manager</b>\n\n$status" \
        --ok-label="Manage Networks" \
        --cancel-label="Quit" \
        --extra-button="Show QR" \
        --extra-button="Disconnect"
        
    local ans=$?
    
    case $ans in
        0) show_network_list; show_main_menu ;;
        1) exit 0 ;;
        *)
            if [ "$ans" = "Show QR" ]; then
                current=$(get_current_ssid)
                if [ -n "$current" ]; then
                    password=$(nmcli -t connection show "$current" | grep "802-11-wireless-security.psk" | cut -d: -f2)
                    security=$(scan_networks | grep ":${current}:" | head -1 | awk -F: '{print $9}')
                    show_qr_code "$current" "$password" "$security"
                fi
                show_main_menu
            elif [ "$ans" = "Disconnect" ]; then
                current=$(get_current_ssid)
                [ -n "$current" ] && nmcli connection down "$current" 2>/dev/null
                show_main_menu
            fi
            ;;
    esac
}

for cmd in zenity nmcli qrencode; do
    if ! command -v $cmd &> /dev/null; then
        zenity --error --title="Missing Dependency" --text="$cmd not found" --width=400
        exit 1
    fi
done

show_main_menu
