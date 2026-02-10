"""GTK dialogs for WiFi Manager"""

import gi
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

from .nmcli_utils import (
    get_current_ssid,
    get_password,
    get_security,
    get_auto_connect,
    set_auto_connect,
    forget_network,
    get_connection_details,
    get_connection_speed,
    get_ip_info
)
from .qr_utils import generate_qr_code, get_qr_file

QR_SIZE = 250

def show_qr_dialog(parent, ssid, password, security):
    """Show QR code dialog"""
    generate_qr_code(ssid, password, security)
    
    dialog = Gtk.Dialog(
        title=f"QR Code - {ssid}",
        transient_for=parent,
        modal=True
    )
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
    current = get_current_ssid()
    if not current:
        dialog = Gtk.MessageDialog(
            parent, 0, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK, "Not Connected"
        )
        dialog.format_secondary_text(
            "No WiFi network is currently connected"
        )
        dialog.run()
        dialog.destroy()
        return
    
    details = get_connection_details()
    rate, signal = get_connection_speed()
    ip_info = get_ip_info()
    password = get_password(current)
    security = get_security(current)
    autoconnect = details.get("autoconnect", False)
    
    dialog = Gtk.Dialog(
        title=f"Connection Details - {current}",
        transient_for=parent,
        modal=True
    )
    dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    dialog.add_button("Toggle Auto-Connect", Gtk.ResponseType.APPLY)
    dialog.add_button("Show QR", Gtk.ResponseType.HELP)
    dialog.set_default_size(420, 400)
    
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_start(20)
    box.set_margin_end(20)
    box.set_margin_top(20)
    box.set_margin_bottom(20)
    dialog.get_content_area().add(box)
    
    # Network name header
    label_title = Gtk.Label()
    label_title.set_markup(f"<b><big>{current}</big></b>")
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
    
    lbl = Gtk.Label()
    lbl.set_markup(f"🔒 <b>Security:</b> {security}")
    lbl.set_xalign(0)
    box_network.pack_start(lbl, False, False, 0)
    
    lbl = Gtk.Label()
    lbl.set_markup(f"📶 <b>Signal:</b> {signal}% ({details.get('signal_dbm', 'N/A')} dBm)")
    lbl.set_xalign(0)
    box_network.pack_start(lbl, False, False, 0)
    
    lbl = Gtk.Label()
    lbl.set_markup(f"⚡ <b>Speed:</b> {rate}")
    lbl.set_xalign(0)
    box_network.pack_start(lbl, False, False, 0)
    
    lbl = Gtk.Label()
    auto_status = "Enabled" if autoconnect else "Disabled"
    lbl.set_markup(f"🔄 <b>Auto-connect:</b> {auto_status}")
    lbl.set_xalign(0)
    box_network.pack_start(lbl, False, False, 0)
    
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
    
    lbl = Gtk.Label()
    lbl.set_markup(f"🏠 <b>Local IP:</b> {ip_info.get('local_ip', 'N/A')}")
    lbl.set_xalign(0)
    box_ip.pack_start(lbl, False, False, 0)
    
    lbl = Gtk.Label()
    lbl.set_markup(f"🚪 <b>Gateway:</b> {ip_info.get('gateway', 'N/A')}")
    lbl.set_xalign(0)
    box_ip.pack_start(lbl, False, False, 0)
    
    lbl = Gtk.Label()
    lbl.set_markup(f"🌐 <b>DNS 1:</b> {ip_info.get('dns1', 'N/A')}")
    lbl.set_xalign(0)
    box_ip.pack_start(lbl, False, False, 0)
    
    lbl = Gtk.Label()
    lbl.set_markup(f"🌐 <b>DNS 2:</b> {ip_info.get('dns2', 'N/A')}")
    lbl.set_xalign(0)
    box_ip.pack_start(lbl, False, False, 0)
    
    lbl = Gtk.Label()
    lbl.set_markup(f"🔌 <b>Interface:</b> {ip_info.get('interface', 'N/A')}")
    lbl.set_xalign(0)
    box_ip.pack_start(lbl, False, False, 0)
    
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
        set_auto_connect(current, new_state)
    elif response == Gtk.ResponseType.HELP:
        show_qr_dialog(parent, current, password, security)
    
    dialog.destroy()

def show_settings_dialog(parent):
    """Show settings dialog"""
    current = get_current_ssid()
    
    dialog = Gtk.Dialog(
        title="Settings",
        transient_for=parent,
        modal=True
    )
    dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    dialog.set_default_size(350, 250)
    
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_start(20)
    box.set_margin_end(20)
    box.set_margin_top(20)
    box.set_margin_bottom(20)
    dialog.get_content_area().add(box)
    
    label = Gtk.Label()
    label.set_markup("<b>Auto-Connect Settings</b>")
    box.pack_start(label, False, False, 10)
    
    if current:
        autoconnect = get_auto_connect(current)
        
        switch = Gtk.Switch()
        switch.set_active(autoconnect)
        switch.connect("state-set", lambda w, s: set_auto_connect(current, s))
        
        label_switch = Gtk.Label(label=f"Auto-connect to {current}")
        label_switch.set_xalign(0)
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.pack_start(label_switch, True, True, 0)
        hbox.pack_start(switch, False, False, 0)
        box.pack_start(hbox, False, False, 10)
        
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(sep, False, False, 10)
    
    label2 = Gtk.Label()
    label2.set_markup("<b>Network Profiles</b>")
    box.pack_start(label2, False, False, 10)
    
    label3 = Gtk.Label()
    label3.set_markup(
        "<small>Select a network and click 'Forget' to remove saved profile</small>"
    )
    label3.set_xalign(0)
    box.pack_start(label3, False, False, 5)
    
    box.show_all()
    dialog.run()
    dialog.destroy()

def show_password_dialog(parent, ssid):
    """Show password input dialog"""
    dialog = Gtk.Dialog(
        title="Password",
        transient_for=parent,
        modal=True
    )
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
    dialog = Gtk.Dialog(
        title="Forget Network",
        transient_for=parent,
        modal=True
    )
    dialog.add_button("Forget", Gtk.ResponseType.YES)
    dialog.add_button("Cancel", Gtk.ResponseType.NO)
    dialog.set_default_size(350, 150)
    
    box = dialog.get_content_area()
    box.pack_start(
        Gtk.Label(label=f"Are you sure you want to forget '{ssid}'?"),
        True, True, 20
    )
    box.pack_start(
        Gtk.Label(label="This will remove the saved network profile."),
        True, True, 5
    )
    
    box.show_all()
    
    response = dialog.run()
    dialog.destroy()
    
    return response == Gtk.ResponseType.YES

def show_message_dialog(parent, title, message, msg_type=Gtk.MessageType.INFO):
    """Show a simple message dialog"""
    dialog = Gtk.MessageDialog(
        parent, 0, msg_type,
        Gtk.ButtonsType.OK, title
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()

def show_progress_dialog(parent, title, message):
    """Show a progress dialog (returns dialog for updating)"""
    dialog = Gtk.Dialog(
        title=title,
        transient_for=parent,
        modal=True
    )
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
