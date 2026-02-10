#!/bin/bash

# WiFi GTK Manager using YAD
# Requires: yad, nmcli, qrencode, ImageMagick

WIFI_ICON="/usr/share/icons/Adwaita/48x48/devices/network-wireless.svg"
QR_FILE="/tmp/wifi_qr.png"

get_current_connection() {
    nmcli -t connection show --active | grep "802-11-wireless" | head -1 | cut -d: -f1
}

get_current_ssid() {
    conn=$(get_current_connection)
    if [ -n "$conn" ]; then
        nmcli -t connection show "$conn" | grep "802-11-wireless.ssid" | cut -d: -f2
    fi
}

parse_wifi_line() {
    local line="$1"
    # Replace \: with placeholder, split, restore
    echo "$line" | sed 's/\\:/\x00/g' | tr ':' '\n' | sed 's/\x00/:/g' | tr '\n' ':' | sed 's/:$//'
}

scan_networks() {
    nmcli -t device wifi list
}

get_signal_strength() {
    local signal="$1"
    if [ "$signal" -ge 80 ]; then
        echo "Excellent"
    elif [ "$signal" -ge 60 ]; then
        echo "Good"
    elif [ "$signal" -ge 40 ]; then
        echo "Fair"
    else
        echo "Poor"
    fi
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
    
    convert "$QR_FILE" -resize 300x300 "$QR_FILE" 2>/dev/null
    
    yad --image="$QR_FILE" \
        --image-on-top \
        --button=gtk-close:0 \
        --title="QR Code - $ssid" \
        --text="<b>Network:</b> $ssid\n<b>Type:</b> $security\n\nScan with your phone to connect"
}

connect_to_network() {
    local ssid="$1"
    local password="$2"
    local security="$3"
    
    if [ "$security" = "Open" ] || [ -z "$security" ]; then
        result=$(nmcli device wifi connect "$ssid" 2>&1)
    else
        result=$(nmcli device wifi connect "$ssid" password "$password" 2>&1)
    fi
    
    if [ $? -eq 0 ]; then
        yad --title="Success" --text="Connected to $ssid" --button=gtk-ok:0 --width=300
        return 0
    else
        yad --title="Error" --text="Failed to connect:\n$result" --button=gtk-close:1 --width=400 --error
        return 1
    fi
}

get_network_list() {
    local current_ssid="$1"
    local output=$(scan_networks)
    
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        
        # Parse: :BSSID\:with\:colons:SSID:MODE:CHAN:RATE:SIGNAL:BARS:SECURITY
        # Using awk to handle the fields properly
        echo "$line" | awk -F: '{
            # Reconstruct BSSID (field 2 but with escaped colons)
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
    done <<< "$output"
}

show_network_list() {
    local current_ssid=$(get_current_ssid)
    local network_data=$(get_network_list "$current_ssid")
    
    if [ -z "$network_data" ]; then
        yad --title="WiFi Manager" --text="No networks found" --button=gtk-refresh:1 --button=gtk-close:0
        return $?
    fi
    
    local selection=$(echo "$network_data" | yad --list \
        --title="WiFi Networks" \
        --width=550 \
        --height=450 \
        --image="$WIFI_ICON" \
        --image-on-top \
        --column="Network" \
        --column="Signal %" \
        --column="Security" \
        --print-column=1 \
        --hide-column=1 \
        --button="gtk-refresh!Refresh":1 \
        --button="gtk-connect!Connect":2 \
        --button="gtk-disconnect!Disconnect":3 \
        --button="gtk-info!Details":4 \
        --button="gtk-close!Close":0 \
        --tooltip-column=3)
    
    local exit_code=$?
    
    case $exit_code in
        0) return 0 ;;
        1) show_network_list; return ;;
        2) # Connect
            if [ -n "$selection" ]; then
                ssid=$(echo "$selection" | cut -d'|' -f1)
                security=$(echo "$selection" | cut -d'|' -f3)
                
                if [ "$security" != "Open" ]; then
                    password=$(yad --entry \
                        --title="Connect" \
                        --text="Enter password for $ssid" \
                        --entry-text "" \
                        --hide-text \
                        --button=gtk-connect:0 \
                        --button=gtk-cancel:1)
                    
                    [ -z "$password" ] && return
                else
                    password=""
                fi
                
                connect_to_network "$ssid" "$password" "$security" && show_network_list
            fi
            ;;
        3) # Disconnect
            current=$(get_current_ssid)
            [ -n "$current" ] && nmcli connection down "$current" 2>/dev/null
            sleep 1
            show_network_list
            ;;
        4) # Details
            if [ -n "$selection" ]; then
                ssid=$(echo "$selection" | cut -d'|' -f1)
                password=$(nmcli -t connection show "$ssid" 2>/dev/null | grep "802-11-wireless-security.psk" | cut -d: -f2)
                security=$(echo "$selection" | cut -d'|' -f3)
                
                show_qr_code "$ssid" "$password" "$security" &
                qr_pid=$!
                
                yad --form \
                    --title="Connection Details - $ssid" \
                    --width=400 \
                    --field="SSID":RO "$ssid" \
                    --field="Security":RO "$security" \
                    --field="Password":RO "$password" \
                    --button=gtk-close:0 \
                    --button="Show QR":1
                
                kill $qr_pid 2>/dev/null
            fi
            ;;
    esac
}

show_main_menu() {
    local current_ssid=$(get_current_ssid)
    local current_conn=$(get_current_connection)
    
    local status_text="Not Connected"
    [ -n "$current_ssid" ] && status_text="Connected to: $current_ssid"
    
    yad --paned \
        --title="WiFi GTK Manager" \
        --width=500 \
        --height=300 \
        --image="$WIFI_ICON" \
        --image-on-top \
        --orient=vertical \
        --button="gtk-network!Manage Networks":0 \
        --button="gtk-connect!Connect":1 \
        --button="gtk-disconnect!Disconnect":2 \
        --button="gtk-info!Current Details":3 \
        --button="gtk-quit!Quit":4 \
        --text="<b>WiFi Network Manager</b>\n\n$status_text"
        
    local choice=$?
    
    case $choice in
        0) show_network_list ;;
        1) show_network_list ;;
        2)
            current=$(get_current_ssid)
            [ -n "$current" ] && nmcli connection down "$current" 2>/dev/null
            ;;
        3)
            current=$(get_current_ssid)
            if [ -n "$current" ]; then
                password=$(nmcli -t connection show "$current" | grep "802-11-wireless-security.psk" | cut -d: -f2)
                security=$(get_current_ssid | xargs -I {} nmcli -t device wifi list | grep ":{}:" | head -1 | cut -d: -f9)
                show_qr_code "$current" "$password" "$security"
            else
                yad --title="Info" --text="Not connected to any network" --button=gtk-ok:0 --width=300
            fi
            ;;
    esac
    
    [ $choice -ne 4 ] && show_main_menu
}

check_dependencies() {
    for cmd in yad nmcli qrencode; do
        if ! command -v $cmd &> /dev/null; then
            echo "Missing: $cmd"
            exit 1
        fi
    done
}

check_dependencies
show_main_menu
