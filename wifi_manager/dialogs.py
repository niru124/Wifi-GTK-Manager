"""GTK dialogs for WiFi Manager"""

import gi
import os

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf

from .nmcli_utils import (
    get_current_ssid,
    get_current_connection_name,
    get_password,
    get_security,
    get_auto_connect,
    set_auto_connect,
    forget_network,
    get_connection_details,
    get_connection_speed,
    get_ip_info,
    get_live_speed,
    format_speed,
)
from .qr_utils import generate_qr_code, get_qr_file

QR_SIZE = 250

CONFIG_DIR = os.path.expanduser("~/.config/wifi-manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.conf")


def load_settings():
    """Load settings from config file"""
    settings = {"show_live_speed": True}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        if value.lower() == "true":
                            settings[key] = True
                        elif value.lower() == "false":
                            settings[key] = False
                        else:
                            settings[key] = value
        except:
            pass
    return settings


def save_settings(settings):
    """Save settings to config file"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w") as f:
            for key, value in settings.items():
                f.write(f"{key}={value}\n")
        return True
    except:
        return False


def get_show_live_speed():
    """Get whether to show live speed"""
    return load_settings().get("show_live_speed", True)


# Icon directory path (relative to package)
ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")

# Mapping of logical icon names to SVG files
SVG_ICON_MAP = {
    "verified": "verified-checkmark-symbolic.svg",
    "qr-code": "qr-code-scanner-symbolic.svg",
    "connect": "plug-symbolic.svg",
    "disconnect": "unplug-dots-symbolic.svg",
    "refresh": "circle-outline-thick-symbolic.svg",
    "auto": "auto-connect.svg",
    "speed": "wifi-speed.svg",
    "ip": "network-ip-white.svg",
    "gateway": "gateway-white.svg",
    "dns": "dns-white.svg",
    "speed-toggle": "speed-toggle-white.svg",
}


def load_svg_icon(icon_name, size=16):
    """Load an SVG icon from the bundled icons directory"""
    svg_file = SVG_ICON_MAP.get(icon_name)
    if not svg_file:
        return create_icon_image("dialog-information-symbolic", size)

    svg_path = os.path.join(ICONS_DIR, svg_file)
    if not os.path.exists(svg_path):
        return create_icon_image("dialog-information-symbolic", size)

    image = Gtk.Image()
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(svg_path, size, size, True)
        image.set_from_pixbuf(pixbuf)
    except:
        return create_icon_image("dialog-information-symbolic", size)
    return image


# Icon names for network status
ICON_NETWORK = "network-wireless-symbolic"
ICON_NETWORK_OFFLINE = "network-wireless-disconnected-symbolic"
ICON_LOCK = "lock-symbolic"
ICON_UNLOCK = "unlock-symbolic"
ICON_SIGNAL = "network-wireless-signal-"
ICON_DOWNLOAD = "go-down-symbolic"
ICON_UPLOAD = "go-up-symbolic"
ICON_SETTINGS = "preferences-system-symbolic"
ICON_INFO = "dialog-information-symbolic"
ICON_CLOSE = "window-close-symbolic"


def get_icon_for_signal(signal_str):
    """Get icon name based on signal strength"""
    try:
        signal = int(signal_str.rstrip("%"))
        if signal >= 80:
            return "network-wireless-signal-excellent-symbolic"
        elif signal >= 60:
            return "network-wireless-signal-good-symbolic"
        elif signal >= 40:
            return "network-wireless-signal-ok-symbolic"
        elif signal >= 20:
            return "network-wireless-signal-weak-symbolic"
        else:
            return "network-wireless-signal-none-symbolic"
    except:
        return "network-wireless-signal-none-symbolic"


def create_icon_image(icon_name, size=16):
    """Create an image widget with the specified icon"""
    image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
    return image


def show_qr_dialog(parent, ssid, password, security):
    """Show QR code dialog"""
    generate_qr_code(ssid, password, security)

    dialog = Gtk.Dialog(title=f"QR Code - {ssid}", transient_for=parent, modal=True)
    dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    dialog.set_default_size(350, 450)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_start(20)
    box.set_margin_end(20)
    box.set_margin_top(20)
    box.set_margin_bottom(20)
    dialog.get_content_area().add(box)

    if os.path.exists(get_qr_file()):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            get_qr_file(), QR_SIZE, QR_SIZE, True
        )
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        box.pack_start(image, False, False, 10)

    sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    box.pack_start(sep, False, False, 5)

    label_ssid = Gtk.Label()
    label_ssid.set_markup(f"<b>Network:</b> {ssid}")
    box.pack_start(label_ssid, False, False, 5)

    if password:
        label_pass = Gtk.Label()
        label_pass.set_markup(f"<b>Password:</b> {password}")
        box.pack_start(label_pass, False, False, 5)

    label_type = Gtk.Label()
    label_type.set_markup(f"<b>Type:</b> {security}")
    box.pack_start(label_type, False, False, 5)

    box.show_all()
    dialog.run()
    dialog.destroy()


def show_connection_info_dialog(parent):
    """Show detailed connection information"""
    current_ssid = get_current_ssid()
    conn_name = get_current_connection_name()
    if not current_ssid:
        dialog = Gtk.MessageDialog(
            parent, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "Not Connected"
        )
        dialog.format_secondary_text("No WiFi network is currently connected")
        dialog.run()
        dialog.destroy()
        return

    details = get_connection_details()
    rate, signal = get_connection_speed()
    ip_info = get_ip_info()
    password = get_password(conn_name)
    security = get_security(current_ssid)
    autoconnect = details.get("autoconnect", False)
    rx_speed, tx_speed = get_live_speed()

    dialog = Gtk.Dialog(
        title=f"Connection Details - {current_ssid}", transient_for=parent, modal=True
    )
    dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    dialog.add_button("Toggle Auto-Connect", Gtk.ResponseType.APPLY)
    dialog.add_button("Show QR", Gtk.ResponseType.HELP)
    dialog.set_default_size(420, 420)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_start(20)
    box.set_margin_end(20)
    box.set_margin_top(20)
    box.set_margin_bottom(20)
    dialog.get_content_area().add(box)

    # Network name header
    label_title = Gtk.Label()
    label_title.set_markup(f"<b><big>{current_ssid}</big></b>")
    label_title.set_margin_bottom(10)
    box.pack_start(label_title, False, False, 0)

    # Network info section
    frame_network = Gtk.Frame(label="<b>Network</b>")
    frame_network.set_margin_bottom(10)
    box.pack_start(frame_network, False, False, 0)

    box_network = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box_network.set_margin_start(15)
    box_network.set_margin_end(15)
    box_network.set_margin_top(10)
    box_network.set_margin_bottom(10)
    frame_network.add(box_network)

    # Signal with icon
    hbox_signal = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    signal_icon = create_icon_image(get_icon_for_signal(signal))
    hbox_signal.pack_start(signal_icon, False, False, 0)
    lbl = Gtk.Label(label=f"Signal: {signal}% ({details.get('signal_dbm', 'N/A')} dBm)")
    hbox_signal.pack_start(lbl, False, False, 0)
    box_network.pack_start(hbox_signal, False, False, 0)

    # Speed
    hbox_speed = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    speed_icon = load_svg_icon("speed", 16)
    hbox_speed.pack_start(speed_icon, False, False, 0)
    lbl = Gtk.Label(label=f"Speed: {rate}")
    hbox_speed.pack_start(lbl, False, False, 0)
    box_network.pack_start(hbox_speed, False, False, 0)

    # Live speed (RX/TX)
    hbox_live = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

    hbox_rx = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    rx_icon = create_icon_image("go-down-symbolic")
    hbox_rx.pack_start(rx_icon, False, False, 0)
    rx_label = Gtk.Label(label=f"RX: {format_speed(rx_speed)}")
    hbox_rx.pack_start(rx_label, False, False, 0)
    hbox_live.pack_start(hbox_rx, True, True, 0)

    hbox_tx = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    tx_icon = create_icon_image("go-up-symbolic")
    hbox_tx.pack_start(tx_icon, False, False, 0)
    tx_label = Gtk.Label(label=f"TX: {format_speed(tx_speed)}")
    hbox_tx.pack_start(tx_label, False, False, 0)
    hbox_live.pack_start(hbox_tx, True, True, 0)

    box_network.pack_start(hbox_live, False, False, 0)

    # Auto-connect with icon
    hbox_auto = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    auto_icon = load_svg_icon("auto", 16)
    hbox_auto.pack_start(auto_icon, False, False, 0)
    auto_status = "Enabled" if autoconnect else "Disabled"
    lbl = Gtk.Label(label=f"Auto-connect: {auto_status}")
    hbox_auto.pack_start(lbl, False, False, 0)
    box_network.pack_start(hbox_auto, False, False, 0)

    # IP Address section
    frame_ip = Gtk.Frame(label="<b>IP Address</b>")
    frame_ip.set_margin_bottom(10)
    box.pack_start(frame_ip, False, False, 0)

    box_ip = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box_ip.set_margin_start(15)
    box_ip.set_margin_end(15)
    box_ip.set_margin_top(10)
    box_ip.set_margin_bottom(10)
    frame_ip.add(box_ip)

    # Local IP
    hbox_ip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    ip_icon = load_svg_icon("ip", 16)
    hbox_ip.pack_start(ip_icon, False, False, 0)
    lbl = Gtk.Label(label=f"Local IP: {ip_info.get('local_ip', 'N/A')}")
    hbox_ip.pack_start(lbl, False, False, 0)
    box_ip.pack_start(hbox_ip, False, False, 0)

    # Gateway
    hbox_gw = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    gw_icon = load_svg_icon("gateway", 16)
    hbox_gw.pack_start(gw_icon, False, False, 0)
    lbl = Gtk.Label(label=f"Gateway: {ip_info.get('gateway', 'N/A')}")
    hbox_gw.pack_start(lbl, False, False, 0)
    box_ip.pack_start(hbox_gw, False, False, 0)

    # DNS
    hbox_dns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    dns_icon = load_svg_icon("dns", 16)
    hbox_dns.pack_start(dns_icon, False, False, 0)
    lbl = Gtk.Label(label=f"DNS: {ip_info.get('dns1', 'N/A')}")
    hbox_dns.pack_start(lbl, False, False, 0)
    box_ip.pack_start(hbox_dns, False, False, 0)

    # Interface
    hbox_iface = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    iface_icon = create_icon_image("network-wireless-symbolic")
    hbox_iface.pack_start(iface_icon, False, False, 0)
    lbl = Gtk.Label(label=f"Interface: {ip_info.get('interface', 'N/A')}")
    hbox_iface.pack_start(lbl, False, False, 0)
    box_ip.pack_start(hbox_iface, False, False, 0)

    # Password section (if available)
    if password:
        frame_pass = Gtk.Frame(label="<b>Password</b>")
        box.pack_start(frame_pass, False, False, 0)

        box_pass = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box_pass.set_margin_start(15)
        box_pass.set_margin_end(15)
        box_pass.set_margin_top(10)
        box_pass.set_margin_bottom(10)
        frame_pass.add(box_pass)

        lbl = Gtk.Label(label=password)
        lbl.set_selectable(True)
        lbl.set_xalign(0)
        box_pass.pack_start(lbl, False, False, 0)

    box.show_all()

    response = dialog.run()

    if response == Gtk.ResponseType.APPLY:
        new_state = not autoconnect
        set_auto_connect(conn_name, new_state)
    elif response == Gtk.ResponseType.HELP:
        show_qr_dialog(parent, current_ssid, password, security)

    dialog.destroy()


def show_settings_dialog(parent):
    """Show settings dialog"""
    current_ssid = get_current_ssid()
    conn_name = get_current_connection_name()

    dialog = Gtk.Dialog(title="Settings", transient_for=parent, modal=True)
    dialog.add_button("Save", Gtk.ResponseType.APPLY)
    dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    dialog.set_default_size(400, 300)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_start(20)
    box.set_margin_end(20)
    box.set_margin_top(20)
    box.set_margin_bottom(20)
    dialog.get_content_area().add(box)

    # Auto-Connect section
    label = Gtk.Label()
    label.set_markup("<b>Auto-Connect</b>")
    box.pack_start(label, False, False, 10)

    autoconnect = False
    autoconnect_changed = False
    if conn_name:
        autoconnect = get_auto_connect(conn_name)

        switch = Gtk.Switch()
        switch.set_active(autoconnect)
        switch.set_name("autoconnect")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = create_icon_image("sync-symbolic")
        hbox.pack_start(icon, False, False, 0)

        label_switch = Gtk.Label(label=f"Auto-connect to {current_ssid}")
        label_switch.set_xalign(0)
        hbox.pack_start(label_switch, True, True, 0)
        hbox.pack_start(switch, False, False, 0)
        box.pack_start(hbox, False, False, 10)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(sep, False, False, 10)

    # Live Speed Display section
    label_speed = Gtk.Label()
    label_speed.set_markup("<b>Live Speed Display</b>")
    box.pack_start(label_speed, False, False, 10)

    hbox_speed = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    icon = create_icon_image("transmit-symbolic")
    hbox_speed.pack_start(icon, False, False, 0)

    label_speed_set = Gtk.Label(label="Show live TX/RX speed in header")
    label_speed_set.set_xalign(0)
    hbox_speed.pack_start(label_speed_set, True, True, 0)

    switch_speed = Gtk.Switch()
    show_speed = load_settings().get("show_live_speed", True)
    switch_speed.set_active(show_speed)
    switch_speed.set_name("show_speed")
    hbox_speed.pack_start(switch_speed, False, False, 0)
    box.pack_start(hbox_speed, False, False, 10)

    box.show_all()

    result = {"show_speed": show_speed}

    response = dialog.run()

    if response == Gtk.ResponseType.APPLY:
        settings = load_settings()

        # Save auto-connect
        if conn_name:
            new_autoconnect = switch.get_active()
            if new_autoconnect != autoconnect:
                set_auto_connect(conn_name, new_autoconnect)

        # Save live speed setting
        new_show_speed = switch_speed.get_active()
        settings["show_live_speed"] = new_show_speed
        save_settings(settings)

        result["show_speed"] = new_show_speed

    dialog.destroy()
    return result


def show_password_dialog(parent, ssid):
    """Show password input dialog"""
    dialog = Gtk.Dialog(title="Password", transient_for=parent, modal=True)
    dialog.add_button("Connect", Gtk.ResponseType.OK)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)

    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_placeholder_text("Enter password")

    box = dialog.get_content_area()
    box.pack_start(Gtk.Label(label=f"Connect to {ssid}:"), True, True, 10)
    box.pack_start(entry, True, True, 0)
    box.show_all()

    response = dialog.run()
    password = entry.get_text() if response == Gtk.ResponseType.OK else ""
    dialog.destroy()

    return password if response == Gtk.ResponseType.OK else None


def show_forget_confirm_dialog(parent, ssid):
    """Show confirmation dialog before forgetting a network"""
    dialog = Gtk.Dialog(title="Forget Network", transient_for=parent, modal=True)
    dialog.add_button("Forget", Gtk.ResponseType.YES)
    dialog.add_button("Cancel", Gtk.ResponseType.NO)
    dialog.set_default_size(350, 150)

    box = dialog.get_content_area()
    box.pack_start(
        Gtk.Label(label=f"Are you sure you want to forget '{ssid}'?"), True, True, 20
    )
    box.pack_start(
        Gtk.Label(label="This will remove the saved network profile."), True, True, 5
    )

    box.show_all()

    response = dialog.run()
    dialog.destroy()

    return response == Gtk.ResponseType.YES


def show_message_dialog(parent, title, message, msg_type=Gtk.MessageType.INFO):
    """Show a simple message dialog"""
    dialog = Gtk.MessageDialog(parent, 0, msg_type, Gtk.ButtonsType.OK, title)
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def show_progress_dialog(parent, title, message):
    """Show a progress dialog (returns dialog for updating)"""
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)

    label = Gtk.Label(label=message)

    progress = Gtk.ProgressBar()
    progress.pulse()

    box = dialog.get_content_area()
    box.pack_start(label, True, True, 10)
    box.pack_start(progress, True, True, 0)

    box.show_all()

    def update_pulse():
        progress.pulse()
        return True

    return dialog, update_pulse
