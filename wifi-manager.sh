#!/bin/bash

# WiFi Manager using YAD
# Requires: yad, nmcli, qrencode (ImageMagick 'convert' optional, for QR resize)

WIFI_ICON="/usr/share/icons/Adwaita/48x48/devices/network-wireless.svg"
QR_FILE="/tmp/wifi_qr.png"

# Placeholder for escaped colons: nmcli -t escapes ':' as '\:' inside
# BSSIDs (and possibly SSIDs), so naive ':' splitting misaligns fields.
PH=$'\x1f'

get_current_connection() {
    # Profile NAME (not SSID) of the active WiFi connection.
    # $NF match keeps this working even if the name contains colons.
    nmcli -t -f NAME,TYPE connection show --active 2>/dev/null \
        | awk -F: '$NF == "802-11-wireless" { sub(/:[^:]*$/, ""); print; exit }'
}

get_current_ssid() {
    local conn
    conn=$(get_current_connection)
    if [ -n "$conn" ]; then
        nmcli -t connection show "$conn" 2>/dev/null \
            | grep "802-11-wireless.ssid:" | cut -d: -f2-
    fi
}

# Split one `nmcli -t device wifi list` line on unescaped colons.
# Sets: WIFI_SSID, WIFI_CHAN, WIFI_SIGNAL, WIFI_SECURITY.
parse_wifi_line() {
    local line="$1"
    local tmp="${line//\\:/$PH}"
    local -a _f
    IFS=':' read -r -a _f <<< "$tmp"
    # IN-USE:BSSID:SSID:MODE:CHAN:RATE:SIGNAL:BARS:SECURITY
    WIFI_SSID="${_f[2]:-}"
    WIFI_CHAN="${_f[4]:-}"
    WIFI_SIGNAL="${_f[6]:-}"
    WIFI_SECURITY="${_f[8]:-}"
    WIFI_SSID="${WIFI_SSID//$PH/:}"
    WIFI_SECURITY="${WIFI_SECURITY//$PH/:}"
    [ -z "$WIFI_SSID" ] && WIFI_SSID="Hidden Network"
    # Plain-text security type only (no bars/widgets): empty means open.
    [ -z "$WIFI_SECURITY" ] && WIFI_SECURITY="Open"
}

scan_networks() {
    nmcli -t device wifi list 2>/dev/null
}

rescan_networks() {
    nmcli device wifi rescan >/dev/null 2>&1
    sleep 2
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

# Exact security lookup for an SSID (no fragile grep on the raw line).
get_security_for_ssid() {
    local want="$1" line
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        parse_wifi_line "$line"
        if [ "$WIFI_SSID" = "$want" ]; then
            printf '%s\n' "$WIFI_SECURITY"
            return 0
        fi
    done < <(scan_networks)
    printf 'WPA2\n'
}

# Resolve an SSID to its saved connection profile name.
get_profile_for_ssid() {
    local want="$1" line name ssid
    while IFS= read -r line; do
        [ "${line##*:}" = "802-11-wireless" ] || continue
        name="${line%:*}"
        ssid=$(nmcli -t -f 802-11-wireless.ssid connection show "$name" 2>/dev/null | cut -d: -f2-)
        if [ "$ssid" = "$want" ]; then
            printf '%s\n' "$name"
            return 0
        fi
    done < <(nmcli -t -f NAME,TYPE connection show 2>/dev/null)
    return 1
}

get_password_for_ssid() {
    local profile
    profile=$(get_profile_for_ssid "$1") || return 1
    # -s is required: without --show-secrets nmcli prints <hidden>/nothing.
    nmcli -s -t connection show "$profile" 2>/dev/null \
        | grep "802-11-wireless-security.psk:" | cut -d: -f2-
}

disconnect_current() {
    local conn
    conn=$(get_current_connection)
    [ -n "$conn" ] && nmcli connection down "$conn" 2>/dev/null
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

    if command -v convert &> /dev/null; then
        convert "$QR_FILE" -resize 300x300 "$QR_FILE" 2>/dev/null
    elif command -v magick &> /dev/null; then
        magick "$QR_FILE" -resize 300x300 "$QR_FILE" 2>/dev/null
    fi

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
    local result

    if [ "$security" = "Open" ] || [ -z "$security" ] || [ -z "$password" ]; then
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
    local line
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        parse_wifi_line "$line"
        printf '%s|%s|%s\n' "$WIFI_SSID" "$WIFI_SIGNAL" "$WIFI_SECURITY"
    done < <(scan_networks)
}

show_network_list() {
    local do_rescan="${1:-0}"
    [ "$do_rescan" = "1" ] && rescan_networks

    local network_data
    network_data=$(get_network_list)

    if [ -z "$network_data" ]; then
        yad --title="WiFi Manager" --text="No networks found" --button=gtk-refresh:1 --button=gtk-close:0
        [ $? -eq 1 ] && show_network_list 1
        return
    fi

    local selection
    selection=$(echo "$network_data" | yad --list \
        --title="WiFi Networks" \
        --width=550 \
        --height=450 \
        --image="$WIFI_ICON" \
        --image-on-top \
        --column="Network" \
        --column="Signal %" \
        --column="Security" \
        --print-column=1 \
        --button="gtk-refresh!Refresh":1 \
        --button="gtk-connect!Connect":2 \
        --button="gtk-disconnect!Disconnect":3 \
        --button="gtk-info!Details":4 \
        --button="gtk-close!Close":0 \
        --tooltip-column=3)

    local exit_code=$?

    case $exit_code in
        0) return 0 ;;
        1) show_network_list 1; return ;;
        2) # Connect
            if [ -n "$selection" ]; then
                local ssid security password rc
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
                    rc=$?
                    [ $rc -ne 0 ] && return
                else
                    password=""
                fi

                connect_to_network "$ssid" "$password" "$security" && show_network_list
            fi
            ;;
        3) # Disconnect (by profile name, not SSID)
            disconnect_current
            sleep 1
            show_network_list
            ;;
        4) # Details
            if [ -n "$selection" ]; then
                local ssid security password qr_pid
                ssid=$(echo "$selection" | cut -d'|' -f1)
                security=$(echo "$selection" | cut -d'|' -f3)
                password=$(get_password_for_ssid "$ssid")

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
    local current_ssid current_conn status_text choice
    current_ssid=$(get_current_ssid)
    current_conn=$(get_current_connection)

    status_text="Not Connected"
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

    choice=$?

    case $choice in
        0) show_network_list ;;
        1) show_network_list ;;
        2)
            disconnect_current
            ;;
        3)
            current_ssid=$(get_current_ssid)
            if [ -n "$current_ssid" ]; then
                local password security
                password=$(get_password_for_ssid "$current_ssid")
                security=$(get_security_for_ssid "$current_ssid")
                show_qr_code "$current_ssid" "$password" "$security"
            else
                yad --title="Info" --text="Not connected to any network" --button=gtk-ok:0 --width=300
            fi
            ;;
    esac

    [ $choice -ne 4 ] && show_main_menu
}

check_dependencies() {
    local cmd missing=0
    for cmd in yad nmcli qrencode; do
        if ! command -v "$cmd" &> /dev/null; then
            echo "Missing: $cmd"
            missing=1
        fi
    done
    if ! command -v convert &> /dev/null && ! command -v magick &> /dev/null; then
        echo "Note: ImageMagick (convert/magick) not found, QR images won't be resized."
    fi
    [ "$missing" -ne 0 ] && exit 1
}

check_dependencies
show_main_menu
