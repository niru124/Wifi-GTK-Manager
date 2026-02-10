"""Simple Hotspot page using NetworkManager's built-in hotspot"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import subprocess
import os

class HotspotPage(Gtk.Box):
    """Simple hotspot configuration page"""
    
    def __init__(self, main_window, back_callback):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_window = main_window
        self.back_callback = back_callback
        self.hotspot_running = False
        
        self._setup_ui()
        self._refresh_status()
    
    def _setup_ui(self):
        """Setup the hotspot UI"""
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(header_box, False, False, 0)
        
        btn_back = Gtk.Button.new_with_label("← Back")
        btn_back.connect("clicked", lambda w: self.back_callback())
        header_box.pack_start(btn_back, False, False, 0)
        
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<b><big>WiFi Hotspot</big></b>")
        header_box.pack_start(lbl_title, True, True, 0)
        
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(self.status_box, False, False, 5)
        
        self.status_icon = Gtk.Label()
        self.status_box.pack_start(self.status_icon, False, False, 0)
        
        self.lbl_status = Gtk.Label()
        self.lbl_status.set_markup("<b>Status:</b> Checking...")
        self.status_box.pack_start(self.lbl_status, False, False, 0)
        
        notebook = Gtk.Notebook()
        notebook.set_show_tabs(True)
        notebook.set_show_border(True)
        self.pack_start(notebook, True, True, 0)
        
        create_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        create_box.set_margin_start(20)
        create_box.set_margin_end(20)
        create_box.set_margin_top(20)
        create_box.set_margin_bottom(20)
        notebook.append_page(create_box, Gtk.Label("Create Hotspot"))
        
        lbl_ssid = Gtk.Label(label="Network Name (SSID):")
        lbl_ssid.set_xalign(0)
        create_box.pack_start(lbl_ssid, False, False, 0)
        
        self.entry_ssid = Gtk.Entry()
        self.entry_ssid.set_placeholder_text("MyHotspot")
        self.entry_ssid.set_text("MyHotspot")
        create_box.pack_start(self.entry_ssid, False, False, 0)
        
        lbl_pass = Gtk.Label(label="Password:")
        lbl_pass.set_xalign(0)
        create_box.pack_start(lbl_pass, False, False, 0)
        
        self.entry_password = Gtk.Entry()
        self.entry_password.set_visibility(False)
        self.entry_password.set_placeholder_text("Enter password (min 8 characters)")
        self.entry_password.set_text("12345678")
        create_box.pack_start(self.entry_password, False, False, 0)
        
        pass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        create_box.pack_start(pass_box, False, False, 0)
        
        chk_show = Gtk.CheckButton(label="Show password")
        chk_show.connect("toggled", lambda c: self.entry_password.set_visibility(c.get_active()))
        pass_box.pack_start(chk_show, False, False, 0)
        
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_margin_top(20)
        create_box.pack_start(action_box, False, False, 0)
        
        self.btn_toggle = Gtk.Button.new_with_label("▶ Start Hotspot")
        self.btn_toggle.connect("clicked", self._on_toggle_hotspot)
        action_box.pack_start(self.btn_toggle, True, True, 0)
        
        saved_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        saved_box.set_margin_start(20)
        saved_box.set_margin_end(20)
        saved_box.set_margin_top(20)
        saved_box.set_margin_bottom(20)
        notebook.append_page(saved_box, Gtk.Label("Quick Actions"))
        
        lbl_quick = Gtk.Label()
        lbl_quick.set_markup("<b>Quick Actions</b>")
        saved_box.pack_start(lbl_quick, False, False, 0)
        
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        saved_box.pack_start(info_box, False, False, 10)
        
        lbl_info = Gtk.Label(label="This hotspot uses NetworkManager's built-in feature.")
        lbl_info.set_xalign(0)
        info_box.pack_start(lbl_info, False, False, 0)
        
        lbl_info2 = Gtk.Label(label="Other devices can connect to share your internet connection.")
        lbl_info2.set_xalign(0)
        info_box.pack_start(lbl_info2, False, False, 0)
        
        btn_stop = Gtk.Button.new_with_label("■ Stop Hotspot")
        btn_stop.connect("clicked", self._on_stop_hotspot)
        saved_box.pack_start(btn_stop, False, False, 10)
    
    def _get_hotspot_status(self):
        """Check if hotspot is running"""
        result = subprocess.run(
            ["nmcli", "-t", "connection", "show", "--active"],
            capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if ":hotspot:" in line:
                return True, line.split(":")[0]
        return False, None
    
    def _get_wifi_interface(self):
        """Get WiFi interface"""
        result = subprocess.run(
            ["nmcli", "-t", "device"],
            capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if "wifi" in line.lower():
                return line.split(":")[0]
        return "wlan0"
    
    def _refresh_status(self):
        """Refresh hotspot status"""
        running, conn_name = self._get_hotspot_status()
        self.hotspot_running = running
        
        if running:
            self.status_icon.set_markup("●")
            self.lbl_status.set_markup(f"<b>Status:</b> Running - '{conn_name}'")
            self.btn_toggle.set_label("■ Stop")
            self.btn_toggle.set_sensitive(True)
        else:
            self.status_icon.set_markup("○")
            self.lbl_status.set_markup("<b>Status:</b> Not running")
            self.btn_toggle.set_label("▶ Start Hotspot")
            self.btn_toggle.set_sensitive(True)
    
    def _on_toggle_hotspot(self, widget):
        if self.hotspot_running:
            self._on_stop_hotspot(widget)
        else:
            self._on_start_hotspot(widget)
    
    def _on_start_hotspot(self, widget):
        ssid = self.entry_ssid.get_text().strip()
        password = self.entry_password.get_text()
        
        if not ssid:
            self._show_message("Error", "Please enter a network name", Gtk.MessageType.ERROR)
            return
        
        if len(password) < 8:
            self._show_message("Error", "Password must be at least 8 characters", Gtk.MessageType.ERROR)
            return
        
        widget.set_sensitive(False)
        widget.set_label("Starting...")
        
        interface = self._get_wifi_interface()
        
        result = subprocess.run(
            ["pkexec", "nmcli", "device", "wifi", "hotspot", 
             "ifname", interface, "ssid", ssid, "password", password],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            self._show_message("Success", f"Hotspot '{ssid}' started!", Gtk.MessageType.INFO)
            self._refresh_status()
        else:
            error = result.stderr or result.stdout
            self._show_message("Error", f"Failed: {error}", Gtk.MessageType.ERROR)
            widget.set_sensitive(True)
            widget.set_label("▶ Start Hotspot")
    
    def _on_stop_hotspot(self, widget):
        widget.set_sensitive(False)
        widget.set_label("Stopping...")
        
        result = subprocess.run(
            ["pkexec", "nmcli", "connection", "down", "hotspot"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            self._show_message("Info", "Hotspot stopped", Gtk.MessageType.INFO)
        else:
            self._show_message("Info", "Hotspot may already be stopped", Gtk.MessageType.INFO)
        
        self._refresh_status()
        widget.set_sensitive(True)
    
    def _show_message(self, title, message, msg_type):
        dialog = Gtk.MessageDialog(
            self.main_window, 0, msg_type,
            Gtk.ButtonsType.OK, title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def show_hotspot_page(main_window, back_callback):
    """Show the hotspot page"""
    page = HotspotPage(main_window, back_callback)
    return page
