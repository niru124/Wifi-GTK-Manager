#!/bin/bash

# WiFi Manager using Zenity (GTK fallback)
# Requires: zenity, nmcli, qrencode

QR_FILE="/tmp/wifi_qr.png"

# Placeholder for escaped colons: nmcli -t escapes ':' as '\:' inside
# BSSIDs (and possibly SSIDs), so naive ':' splitting misaligns fields.
PH=$'\x1f'

get_current_connection() {
    # Profile NAME (not SSID) of the active WiFi connection.
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

get_networks() {
    local line
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        parse_wifi_line "$line"
        printf '%s|%s|%s\n' "$WIFI_SSID" "$WIFI_SIGNAL" "$WIFI_SECURITY"
    done < <(scan_networks)
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

    # NOTE: zenity has no --image dialog; open the PNG in the image
    # viewer and show its path as a fallback.
    if command -v xdg-open &> /dev/null; then
        xdg-open "$QR_FILE" &> /dev/null &
    fi

    zenity --info \
        --title="QR Code - $ssid" \
        --text="Network: $ssid\nType: $security\n\nQR saved to $QR_FILE - open it with an image viewer and scan to connect" \
        --width=350 \
        --ok-label="Close"
}

show_network_list() {
    local do_rescan="${1:-0}"
    [ "$do_rescan" = "1" ] && rescan_networks

    local current_ssid networks
    current_ssid=$(get_current_ssid)
    networks=$(get_networks)
    if [ -n "$current_ssid" ]; then
        # Append connection marker without breaking the 3-column layout.
        networks=$(printf '%s\n' "$networks" | while IFS='|' read -r ssid signal security; do
            if [ "$ssid" = "$current_ssid" ]; then
                printf '%s|%s|%s (connected)\n' "$ssid" "$signal" "$security"
            else
                printf '%s|%s|%s\n' "$ssid" "$signal" "$security"
            fi
        done)
    fi

    if [ -z "$networks" ]; then
        zenity --info --title="WiFi Manager" --text="No networks found" --width=300
        return
    fi

    local selection rc ssid security password result
    selection=$(echo "$networks" | zenity --list \
        --title="WiFi Networks" \
        --width=550 \
        --height=400 \
        --text="Select a network:" \
        --column="Network" \
        --column="Signal" \
        --column="Security" \
        --print-column=1 \
        --ok-label="Connect" \
        --cancel-label="Close" \
        --extra-button="Disconnect" \
        --extra-button="Show QR" \
        --extra-button="Refresh")
    rc=$?

    # NOTE: zenity prints an extra-button's label as the selection (exit
    # code varies by version), so match labels before exit codes.
    case "$selection" in
        "Disconnect")
            disconnect_current
            show_network_list
            return
            ;;
        "Show QR")
            current_ssid=$(get_current_ssid)
            if [ -n "$current_ssid" ]; then
                password=$(get_password_for_ssid "$current_ssid")
                security=$(get_security_for_ssid "$current_ssid")
                show_qr_code "$current_ssid" "$password" "$security"
            else
                zenity --info --title="Info" --text="Not connected to any network" --width=300
            fi
            show_network_list
            return
            ;;
        "Refresh")
            show_network_list 1
            return
            ;;
        "")
            return
            ;;
    esac

    # Otherwise a network row was chosen with Connect (rc 0).
    if [ $rc -eq 0 ] && [ -n "$selection" ]; then
        ssid="$selection"
        security=$(get_security_for_ssid "$ssid")

        if [ "$security" != "Open" ] && [ -n "$security" ]; then
            password=$(zenity --entry \
                --title="Password" \
                --text="Enter password for $ssid" \
                --hide-text \
                --width=300 \
                --ok-label="Connect" \
                --cancel-label="Cancel")
            [ $? -ne 0 ] && return
        else
            password=""
        fi

        if [ -z "$password" ]; then
            result=$(nmcli device wifi connect "$ssid" 2>&1)
        else
            result=$(nmcli device wifi connect "$ssid" password "$password" 2>&1)
        fi
        if [ $? -eq 0 ]; then
            zenity --info --title="Success" --text="Connected to $ssid" --width=300
        else
            zenity --error --title="Error" --text="Failed to connect to $ssid:\n$result" --width=400
        fi
        show_network_list
    fi
}

show_main_menu() {
    local current status ans rc password security
    current=$(get_current_ssid)
    status="Not Connected"
    [ -n "$current" ] && status="Connected: $current"

    # NOTE: an extra-button click prints its label (exit code varies by
    # version), so match the label text, not just the exit code.
    ans=$(zenity --question \
        --title="WiFi Manager" \
        --width=400 \
        --height=200 \
        --text="<b>WiFi Network Manager</b>\n\n$status" \
        --ok-label="Manage Networks" \
        --cancel-label="Quit" \
        --extra-button="Show QR" \
        --extra-button="Disconnect")
    rc=$?

    case "$ans" in
        "Show QR")
            current=$(get_current_ssid)
            if [ -n "$current" ]; then
                password=$(get_password_for_ssid "$current")
                security=$(get_security_for_ssid "$current")
                show_qr_code "$current" "$password" "$security"
            else
                zenity --info --title="Info" --text="Not connected to any network" --width=300
            fi
            show_main_menu
            ;;
        "Disconnect")
            disconnect_current
            show_main_menu
            ;;
        *)
            if [ $rc -eq 0 ]; then
                show_network_list
                show_main_menu
            fi
            ;;
    esac
}

for cmd in zenity nmcli qrencode; do
    if ! command -v "$cmd" &> /dev/null; then
        zenity --error --title="Missing Dependency" --text="$cmd not found" --width=400
        exit 1
    fi
done

show_main_menu
