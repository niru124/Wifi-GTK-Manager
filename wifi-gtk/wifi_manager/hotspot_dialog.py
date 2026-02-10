"""Hotspot configuration dialog with dedicated page"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from .hotspot_utils import (
    get_wifi_interface,
    get_current_hotspot,
    stop_hotspot,
    create_hotspot,
    save_hotspot_profile,
    get_saved_hotspots,
    delete_hotspot_profile,
    get_available_channels,
    get_wifi_device_status
)

class HotspotPage(Gtk.Box):
    """Dedicated hotspot configuration page"""
    
    def __init__(self, main_window, back_callback):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_window = main_window
        self.back_callback = back_callback
        self.current_hotspot_name = None
        
        self._setup_ui()
        self._refresh_status()
    
    def _setup_ui(self):
        """Setup the hotspot configuration UI"""
        
        # Header with back button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(header_box, False, False, 0)
        
        btn_back = Gtk.Button.new_with_label("← Back")
        btn_back.connect("clicked", self.back_callback)
        header_box.pack_start(btn_back, False, False, 0)
        
        self.lbl_title = Gtk.Label()
        self.lbl_title.set_markup("<b><big>Hotspot Configuration</big></b>")
        header_box.pack_start(self.lbl_title, True, True, 0)
        
        # Status indicator
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(self.status_box, False, False, 5)
        
        self.status_icon = Gtk.Label()
        self.status_box.pack_start(self.status_icon, False, False, 0)
        
        self.lbl_status = Gtk.Label()
        self.lbl_status.set_markup("<b>Status:</b> Checking...")
        self.status_box.pack_start(self.lbl_status, False, False, 0)
        
        # Notebook for Create / Saved tabs
        notebook = Gtk.Notebook()
        notebook.set_show_tabs(True)
        notebook.set_show_border(True)
        self.pack_start(notebook, True, True, 0)
        
        # Tab 1: Create Hotspot
        create_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        create_box.set_margin_start(20)
        create_box.set_margin_end(20)
        create_box.set_margin_top(20)
        create_box.set_margin_bottom(20)
        notebook.append_page(create_box, Gtk.Label("Create Hotspot"))
        
        # SSID
        lbl_ssid = Gtk.Label(label="Network Name (SSID):")
        lbl_ssid.set_xalign(0)
        create_box.pack_start(lbl_ssid, False, False, 0)
        
        self.entry_ssid = Gtk.Entry()
        self.entry_ssid.set_placeholder_text("MyHotspot")
        self.entry_ssid.set_text("MyHotspot")
        create_box.pack_start(self.entry_ssid, False, False, 0)
        
        # Password
        lbl_pass = Gtk.Label(label="Password:")
        lbl_pass.set_xalign(0)
        create_box.pack_start(lbl_pass, False, False, 0)
        
        self.entry_password = Gtk.Entry()
        self.entry_password.set_visibility(False)
        self.entry_password.set_placeholder_text("Enter password (min 8 characters)")
        create_box.pack_start(self.entry_password, False, False, 0)
        
        # Password show/hide toggle
        pass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        create_box.pack_start(pass_box, False, False, 0)
        
        self.chk_show_pass = Gtk.CheckButton(label="Show password")
        self.chk_show_pass.connect("toggled", self._on_show_pass_toggled)
        pass_box.pack_start(self.chk_show_pass, False, False, 0)
        
        self.chk_random_pass = Gtk.CheckButton(label="Generate random password")
        self.chk_random_pass.connect("toggled", self._on_random_pass_toggled)
        pass_box.pack_start(self.chk_random_pass, False, False, 0)
        
        # Band selection
        lbl_band = Gtk.Label(label="Band:")
        lbl_band.set_xalign(0)
        create_box.pack_start(lbl_band, False, False, 0)
        
        self.combo_band = Gtk.ComboBoxText()
        self.combo_band.append("bg", "2.4 GHz")
        self.combo_band.append("a", "5 GHz")
        self.combo_band.append("all", "2.4 GHz + 5 GHz")
        self.combo_band.set_active_id("bg")
        self.combo_band.connect("changed", self._on_band_changed)
        create_box.pack_start(self.combo_band, False, False, 0)
        
        # Channel
        lbl_channel = Gtk.Label(label="Channel:")
        lbl_channel.set_xalign(0)
        create_box.pack_start(lbl_channel, False, False, 0)
        
        self.combo_channel = Gtk.ComboBoxText()
        self._populate_channels("bg")
        create_box.pack_start(self.combo_channel, False, False, 0)
        
        # Interface selection
        lbl_iface = Gtk.Label(label="Interface:")
        lbl_iface.set_xalign(0)
        create_box.pack_start(lbl_iface, False, False, 0)
        
        self.combo_iface = Gtk.ComboBoxText()
        self._populate_interfaces()
        create_box.pack_start(self.combo_iface, False, False, 0)
        
        # Action buttons
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_margin_top(20)
        create_box.pack_start(action_box, False, False, 0)
        
        self.btn_start = Gtk.Button.new_with_label("▶ Start Hotspot")
        self.btn_start.connect("clicked", self._on_start_hotspot)
        action_box.pack_start(self.btn_start, True, True, 0)
        
        self.btn_stop = Gtk.Button.new_with_label("■ Stop Hotspot")
        self.btn_stop.connect("clicked", self._on_stop_hotspot)
        self.btn_stop.set_sensitive(False)
        action_box.pack_start(self.btn_stop, True, True, 0)
        
        self.btn_save = Gtk.Button.new_with_label("💾 Save Profile")
        self.btn_save.connect("clicked", self._on_save_profile)
        action_box.pack_start(self.btn_save, True, True, 0)
        
        # Tab 2: Saved Hotspots
        saved_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        saved_box.set_margin_start(20)
        saved_box.set_margin_end(20)
        saved_box.set_margin_top(20)
        saved_box.set_margin_bottom(20)
        notebook.append_page(saved_box, Gtk.Label("Saved Profiles"))
        
        lbl_saved = Gtk.Label()
        lbl_saved.set_markup("<b>Saved Hotspot Profiles</b>")
        saved_box.pack_start(lbl_saved, False, False, 0)
        
        # Saved hotspots list
        self.store_saved = Gtk.ListStore(str, str)
        tree_saved = Gtk.TreeView(model=self.store_saved)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Profile Name", renderer, text=0)
        tree_saved.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("SSID", renderer, text=1)
        tree_saved.append_column(column)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(tree_saved)
        scrolled.set_size_request(-1, 200)
        saved_box.pack_start(scrolled, True, True, 0)
        
        saved_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        saved_box.pack_start(saved_btn_box, False, False, 0)
        
        btn_activate = Gtk.Button.new_with_label("▶ Activate")
        btn_activate.connect("clicked", self._on_activate_saved, tree_saved)
        saved_btn_box.pack_start(btn_activate, True, True, 0)
        
        btn_delete = Gtk.Button.new_with_label("🗑 Delete")
        btn_delete.connect("clicked", self._on_delete_saved, tree_saved)
        saved_btn_box.pack_start(btn_delete, True, True, 0)
        
        # Quick actions
        quick_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        quick_box.set_margin_top(20)
        saved_box.pack_start(quick_box, False, False, 0)
        
        lbl_quick = Gtk.Label(label="Quick Start:")
        quick_box.pack_start(lbl_quick, False, False, 10)
        
        btn_quick_on = Gtk.Button.new_with_label("◉ Turn On")
        btn_quick_on.connect("clicked", self._on_quick_on)
        quick_box.pack_start(btn_quick_on, True, True, 0)
        
        btn_quick_off = Gtk.Button.new_with_label("○ Turn Off")
        btn_quick_off.connect("clicked", self._on_quick_off)
        quick_box.pack_start(btn_quick_off, True, True, 0)
        
        self._load_saved_hotspots()
    
    def _populate_interfaces(self):
        """Populate WiFi interfaces"""
        self.combo_iface.remove_all()
        interfaces = get_wifi_interface()
        for iface in interfaces:
            self.combo_iface.append(iface, iface)
        if interfaces:
            self.combo_iface.set_active_id(interfaces[0])
    
    def _populate_channels(self, band):
        """Populate available channels for band"""
        self.combo_channel.remove_all()
        self.combo_channel.append("0", "Auto")
        
        channels = get_available_channels(band)
        for chan in channels:
            self.combo_channel.append(str(chan), f"Channel {chan}")
        self.combo_channel.set_active_id("0")
    
    def _on_band_changed(self, combo):
        band = combo.get_active_id()
        self._populate_channels(band)
    
    def _on_show_pass_toggled(self, checkbox):
        self.entry_password.set_visibility(checkbox.get_active())
    
    def _on_random_pass_toggled(self, checkbox):
        if checkbox.get_active():
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for _ in range(12))
            self.entry_password.set_text(password)
            self.entry_password.set_sensitive(False)
        else:
            self.entry_password.set_text("")
            self.entry_password.set_sensitive(True)
    
    def _on_start_hotspot(self, widget):
        ssid = self.entry_ssid.get_text().strip()
        password = self.entry_password.get_text()
        band = self.combo_band.get_active_id()
        channel = self.combo_channel.get_active_id()
        interface = self.combo_iface.get_active_id()
        
        if not ssid:
            self._show_message("Error", "Please enter a network name", Gtk.MessageType.ERROR)
            return
        
        if len(password) < 8:
            self._show_message("Error", "Password must be at least 8 characters", Gtk.MessageType.ERROR)
            return
        
        self.btn_start.set_sensitive(False)
        self.btn_start.set_label("Starting...")
        
        success = create_hotspot(ssid, password, interface, band)
        
        if success:
            self.current_hotspot_name = f"hotspot-{ssid}"
            self._show_message("Success", f"Hotspot '{ssid}' started successfully!", Gtk.MessageType.INFO)
            self._refresh_status()
        else:
            self._show_message("Error", "Failed to start hotspot. Make sure WiFi is enabled.", Gtk.MessageType.ERROR)
            self.btn_start.set_sensitive(True)
            self.btn_start.set_label("▶ Start Hotspot")
    
    def _on_stop_hotspot(self, widget):
        if self.current_hotspot_name:
            stop_hotspot(self.current_hotspot_name)
            self.current_hotspot_name = None
            self._show_message("Info", "Hotspot stopped", Gtk.MessageType.INFO)
            self._refresh_status()
    
    def _on_save_profile(self, widget):
        ssid = self.entry_ssid.get_text().strip()
        password = self.entry_password.get_text()
        band = self.combo_band.get_active_id()
        interface = self.combo_iface.get_active_id()
        
        if not ssid:
            self._show_message("Error", "Please enter a network name", Gtk.MessageType.ERROR)
            return
        
        if len(password) < 8:
            self._show_message("Error", "Password must be at least 8 characters", Gtk.MessageType.ERROR)
            return
        
        success = save_hotspot_profile(ssid, password, interface, band)
        
        if success:
            self._show_message("Success", f"Profile 'hotspot-{ssid}' saved!", Gtk.MessageType.INFO)
            self._load_saved_hotspots()
        else:
            self._show_message("Error", "Failed to save profile", Gtk.MessageType.ERROR)
    
    def _load_saved_hotspots(self):
        """Load saved hotspot profiles"""
        self.store_saved.clear()
        profiles = get_saved_hotspots()
        for profile in profiles:
            ssid = profile.replace("hotspot-", "")
            self.store_saved.append([profile, ssid])
    
    def _on_activate_saved(self, widget, tree):
        selection = tree.get_selection()
        model, iter = selection.get_selected()
        if iter:
            profile = model[iter][0]
            ssid = model[iter][1]
            password = self._get_profile_password(profile)
            
            if password:
                self.btn_start.set_sensitive(False)
                self.btn_start.set_label("Starting...")
                
                success = create_hotspot(ssid, password)
                
                if success:
                    self.current_hotspot_name = profile
                    self._show_message("Success", f"Hotspot '{ssid}' activated!", Gtk.MessageType.INFO)
                    self._refresh_status()
                else:
                    self._show_message("Error", "Failed to activate hotspot", Gtk.MessageType.ERROR)
                    self.btn_start.set_sensitive(True)
                    self.btn_start.set_label("▶ Start Hotspot")
    
    def _get_profile_password(self, profile):
        """Get password from saved profile"""
        from .nmcli_utils import run_cmd
        output, _ = run_cmd(["nmcli", "-s", "-t", "connection", "show", profile])
        for line in output.split("\n"):
            if "802-11-wireless-security.psk:" in line:
                parts = line.split(":", 1)
                if len(parts) >= 2 and parts[1] not in ["", "<hidden>"]:
                    return parts[1]
        return None
    
    def _on_delete_saved(self, widget, tree):
        selection = tree.get_selection()
        model, iter = selection.get_selected()
        if iter:
            profile = model[iter][0]
            ssid = model[iter][1]
            
            dialog = Gtk.Dialog(
                title="Delete Profile",
                transient_for=self.main_window,
                modal=True
            )
            dialog.add_button("Delete", Gtk.ResponseType.YES)
            dialog.add_button("Cancel", Gtk.ResponseType.NO)
            
            box = dialog.get_content_area()
            box.pack_start(
                Gtk.Label(label=f"Delete profile '{profile}'?"),
                True, True, 20
            )
            box.show_all()
            
            if dialog.run() == Gtk.ResponseType.YES:
                delete_hotspot_profile(profile)
                self._load_saved_hotspots()
            
            dialog.destroy()
    
    def _on_quick_on(self, widget):
        """Quick start hotspot from saved or default"""
        profiles = get_saved_hotspots()
        if profiles:
            profile = profiles[0]
            ssid = profile.replace("hotspot-", "")
            password = self._get_profile_password(profile)
            if password:
                self.current_hotspot_name = profile
                success = create_hotspot(ssid, password)
                if success:
                    self._show_message("Success", f"Hotspot '{ssid}' started", Gtk.MessageType.INFO)
                    self._refresh_status()
                else:
                    self._show_message("Error", "Failed to start hotspot", Gtk.MessageType.ERROR)
        else:
            self._show_message("Info", "No saved profiles. Create one first.", Gtk.MessageType.INFO)
    
    def _on_quick_off(self, widget):
        """Quick stop hotspot"""
        if self.current_hotspot_name:
            stop_hotspot(self.current_hotspot_name)
            self.current_hotspot_name = None
            self._show_message("Info", "Hotspot stopped", Gtk.MessageType.INFO)
            self._refresh_status()
    
    def _refresh_status(self):
        """Refresh hotspot status"""
        conn_name, ssid = get_current_hotspot()
        
        if conn_name:
            self.current_hotspot_name = conn_name
            self.status_icon.set_markup("🔴")
            self.lbl_status.set_markup(f"<b>Status:</b> Running - '{ssid}'")
            self.btn_start.set_sensitive(False)
            self.btn_start.set_label("▶ Running")
            self.btn_stop.set_sensitive(True)
        else:
            self.current_hotspot_name = None
            self.status_icon.set_markup("⚪")
            self.lbl_status.set_markup("<b>Status:</b> Not running")
            self.btn_start.set_sensitive(True)
            self.btn_start.set_label("▶ Start Hotspot")
            self.btn_stop.set_sensitive(False)
    
    def _show_message(self, title, message, msg_type):
        """Show a message dialog"""
        dialog = Gtk.MessageDialog(
            self.main_window, 0, msg_type,
            Gtk.ButtonsType.OK, title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def show_hotspot_page(main_window, back_callback):
    """Show the hotspot configuration page"""
    page = HotspotPage(main_window, back_callback)
    return page
