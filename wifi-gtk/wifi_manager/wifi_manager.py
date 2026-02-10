#!/usr/bin/env python3
"""
WiFi GTK Manager - Main Application
Requires: python3, pygi, nmcli, qrencode
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from .nmcli_utils import (
    get_current_ssid,
    get_networks,
    get_security,
    get_password,
    connect_network,
    disconnect_network,
    rescan_networks
)
from .dialogs import (
    show_qr_dialog,
    show_connection_info_dialog,
    show_settings_dialog,
    show_password_dialog,
    show_forget_confirm_dialog,
    show_message_dialog
)
from .hotspot_dialog import show_hotspot_page

SORT_SIGNAL = "signal"
SORT_NAME = "name"
SORT_SECURITY = "security"

class WiFiManager(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="WiFi GTK Manager")
        self.set_default_size(750, 550)
        self.set_border_width(0)
        
        self.refresh_count = 0
        self.current_sort = SORT_SIGNAL
        self.in_hotspot_mode = False
        
        self._setup_ui()
        self.refresh_networks()
    
    def _setup_ui(self):
        """Setup the main UI with stacked pages"""
        
        self.stack = Gtk.Stack()
        self.add(self.stack)
        
        # Main WiFi page
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.stack.add_named(self.main_box, "wifi")
        
        # Hotspot page
        self.hotspot_page = None
        self._create_hotspot_page()
        
        self._setup_main_header(self.main_box)
        self._setup_main_network_list(self.main_box)
        self._setup_main_sort_box(self.main_box)
        self._setup_main_button_box(self.main_box)
        
        self.stack.set_visible_child_name("wifi")
    
    def _create_hotspot_page(self):
        """Create the hotspot configuration page"""
        def on_back():
            self.in_hotspot_mode = False
            self.stack.set_visible_child_name("wifi")
            self.refresh_networks()
        
        self.hotspot_page = show_hotspot_page(self, on_back)
        self.stack.add_named(self.hotspot_page, "hotspot")
    
    def _setup_main_header(self, parent):
        """Setup the header section"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_start(10)
        header_box.set_margin_end(10)
        header_box.set_margin_top(10)
        parent.pack_start(header_box, False, False, 0)
        
        btn_hotspot = Gtk.Button.new_with_label("📶 Hotspot")
        btn_hotspot.connect("clicked", self._on_show_hotspot)
        header_box.pack_start(btn_hotspot, False, False, 0)
        
        self.spinner = Gtk.Spinner()
        header_box.pack_start(self.spinner, False, False, 0)
        
        self.current_label = Gtk.Label()
        header_box.pack_start(self.current_label, True, True, 0)
        
        btn_settings = Gtk.Button.new_with_label("⚙ Settings")
        btn_settings.connect("clicked", lambda w: show_settings_dialog(self))
        header_box.pack_start(btn_settings, False, False, 0)
        
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<small>Ready</small>")
        self.status_label.set_xalign(0)
        self.status_label.set_margin_start(10)
        self.status_label.set_margin_end(10)
        parent.pack_start(self.status_label, False, False, 5)
    
    def _setup_main_network_list(self, parent):
        """Setup the network list treeview"""
        self.store = Gtk.ListStore(str, str, str, bool)
        self.tree = Gtk.TreeView(model=self.store)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Network", renderer, text=0)
        self.tree.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Signal", renderer, text=1)
        self.tree.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Security", renderer, text=2)
        self.tree.append_column(column)
        
        renderer = Gtk.CellRendererToggle()
        column = Gtk.TreeViewColumn("Connected", renderer, active=3)
        self.tree.append_column(column)
        
        self.tree.connect("row-activated", self._on_double_click)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.tree)
        parent.pack_start(scrolled, True, True, 0)
    
    def _setup_main_sort_box(self, parent):
        """Setup the sort options"""
        sort_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sort_box.set_margin_start(10)
        sort_box.set_margin_end(10)
        parent.pack_start(sort_box, False, False, 5)
        
        label_sort = Gtk.Label(label="Sort by:")
        sort_box.pack_start(label_sort, False, False, 0)
        
        sort_combo = Gtk.ComboBoxText()
        sort_combo.append(SORT_SIGNAL, "Signal Strength")
        sort_combo.append(SORT_NAME, "Name (A-Z)")
        sort_combo.append(SORT_SECURITY, "Security")
        sort_combo.set_active_id(SORT_SIGNAL)
        sort_combo.connect("changed", self._on_sort_changed)
        sort_box.pack_start(sort_combo, False, False, 0)
    
    def _setup_main_button_box(self, parent):
        """Setup the action buttons"""
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_margin_start(10)
        btn_box.set_margin_end(10)
        btn_box.set_margin_bottom(10)
        parent.pack_start(btn_box, False, False, 5)
        
        self.btn_refresh = Gtk.Button.new_with_label("🔄 Refresh")
        self.btn_refresh.connect("clicked", self._on_refresh)
        btn_box.pack_start(self.btn_refresh, True, True, 0)
        
        btn_connect = Gtk.Button.new_with_label("🔗 Connect")
        btn_connect.connect("clicked", self._on_connect)
        btn_box.pack_start(btn_connect, True, True, 0)
        
        btn_disconnect = Gtk.Button.new_with_label("❌ Disconnect")
        btn_disconnect.connect("clicked", self._on_disconnect)
        btn_box.pack_start(btn_disconnect, True, True, 0)
        
        btn_qr = Gtk.Button.new_with_label("📱 QR Code")
        btn_qr.connect("clicked", self._on_show_qr)
        btn_box.pack_start(btn_qr, True, True, 0)
        
        btn_info = Gtk.Button.new_with_label("ℹ Details")
        btn_info.connect("clicked", lambda w: show_connection_info_dialog(self))
        btn_box.pack_start(btn_info, True, True, 0)
        
        btn_forget = Gtk.Button.new_with_label("🗑 Forget")
        btn_forget.connect("clicked", self._on_forget)
        btn_box.pack_start(btn_forget, True, True, 0)
    
    def _on_show_hotspot(self, widget):
        """Switch to hotspot mode"""
        self.in_hotspot_mode = True
        self.stack.set_visible_child_name("hotspot")
        if self.hotspot_page:
            self.hotspot_page._refresh_status()
    
    def _set_refreshing(self, refreshing):
        """Update UI during refresh"""
        if refreshing:
            self.spinner.start()
            self.btn_refresh.set_label("Scanning...")
            self.status_label.set_markup("<small><i>Scanning for networks...</i></small>")
        else:
            self.spinner.stop()
            self.btn_refresh.set_label("🔄 Refresh")
    
    def _update_status(self, message):
        """Update status label"""
        self.status_label.set_markup(f"<small>{message}</small>")
    
    def _sort_networks(self, networks):
        """Sort networks based on current sort option"""
        if self.current_sort == SORT_NAME:
            return sorted(networks, key=lambda x: x['ssid'].lower())
        elif self.current_sort == SORT_SECURITY:
            return sorted(networks, key=lambda x: x['security'])
        else:
            return sorted(
                networks,
                key=lambda x: int(x['signal']) if x['signal'].isdigit() else 0,
                reverse=True
            )
    
    def _on_sort_changed(self, combo):
        """Handle sort option change"""
        self.current_sort = combo.get_active_id()
        self.refresh_networks(show_animation=False)
    
    def _on_double_click(self, tree, path, column):
        """Handle double-click on network"""
        model = tree.get_model()
        iter = model.get_iter(path)
        if iter:
            ssid = model[iter][0]
            self._connect_to_network(ssid)
    
    def refresh_networks(self, show_animation=True):
        """Refresh the network list"""
        if show_animation:
            self._set_refreshing(True)
        GLib.timeout_add(100, self._do_refresh)
    
    def _do_refresh(self):
        """Perform the actual refresh"""
        try:
            rescan_networks()
            self.refresh_count += 1
            GLib.timeout_add(1500, self._finish_refresh)
        except:
            self._set_refreshing(False)
            return False
        return False
    
    def _finish_refresh(self):
        """Finish refresh and update UI"""
        self.store.clear()
        current = get_current_ssid()
        networks = get_networks()
        networks = self._sort_networks(networks)
        
        if current:
            self.current_label.set_text(f"📶 {current}")
            self._update_status(f"Found {len(networks)} networks")
        else:
            self.current_label.set_text("Not Connected")
            self._update_status(f"Found {len(networks)} networks")
        
        for net in networks:
            self.store.append([
                net['ssid'],
                net['signal'] + "%",
                net['security'],
                net['connected']
            ])
        
        self._set_refreshing(False)
        return False
    
    def _on_refresh(self, widget):
        """Handle refresh button click"""
        self.refresh_networks(show_animation=True)
    
    def _on_connect(self, widget):
        """Handle connect button click"""
        selection = self.tree.get_selection()
        model, iter = selection.get_selected()
        if iter:
            ssid = model[iter][0]
            self._connect_to_network(ssid)
        else:
            self._update_status("Select a network to connect")
    
    def _connect_to_network(self, ssid):
        """Connect to a network"""
        security = get_security(ssid)
        self._update_status(f"<i>Connecting to {ssid}...</i>")
        
        password = ""
        if security != "Open":
            saved_password = get_password(ssid)
            if not saved_password:
                password = show_password_dialog(self, ssid)
                if password is None:
                    self._update_status("Connection cancelled")
                    return
            else:
                password = saved_password
        
        self._set_refreshing(True)
        
        if connect_network(ssid, password, security):
            self._update_status("Connected!")
            show_message_dialog(
                self, "Connected",
                f"Successfully connected to {ssid}",
                Gtk.MessageType.INFO
            )
            GLib.timeout_add(
                500,
                lambda: self.refresh_networks(show_animation=False)
            )
        else:
            self._set_refreshing(False)
            self._update_status("Connection failed")
            show_message_dialog(
                self, "Connection Failed",
                "Could not connect to the network",
                Gtk.MessageType.ERROR
            )
    
    def _on_show_qr(self, widget):
        """Handle show QR button click"""
        selection = self.tree.get_selection()
        model, iter = selection.get_selected()
        
        if iter:
            ssid = model[iter][0]
        else:
            ssid = get_current_ssid()
            if not ssid:
                show_message_dialog(
                    self, "No Network Selected",
                    "No WiFi network is currently connected",
                    Gtk.MessageType.WARNING
                )
                return
        
        password = get_password(ssid)
        security = get_security(ssid)
        self._update_status(f"<small>Generating QR for {ssid}...</small>")
        
        # Process pending GTK events to update status
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        
        GLib.timeout_add(100, lambda: self._show_qr_and_update(ssid, password, security))
    
    def _show_qr_and_update(self, ssid, password, security):
        """Show QR dialog and update status after"""
        show_qr_dialog(self, ssid, password, security)
        self._update_status("QR code closed")
        return False
    
    def _on_forget(self, widget):
        """Handle forget button click"""
        selection = self.tree.get_selection()
        model, iter = selection.get_selected()
        
        if not iter:
            show_message_dialog(
                self, "No Network Selected",
                "Select a network to forget",
                Gtk.MessageType.WARNING
            )
            return
        
        ssid = model[iter][0]
        
        if show_forget_confirm_dialog(self, ssid):
            from nmcli_utils import forget_network
            if forget_network(ssid):
                self._update_status(f"Forgot {ssid}")
                GLib.timeout_add(
                    300,
                    lambda: self.refresh_networks(show_animation=False)
                )
            else:
                show_message_dialog(
                    self, "Error",
                    f"Could not forget {ssid}",
                    Gtk.MessageType.ERROR
                )
    
    def _on_disconnect(self, widget):
        """Handle disconnect button click"""
        current = get_current_ssid()
        if current:
            self._update_status(f"<i>Disconnecting from {current}...</i>")
            self._set_refreshing(True)
            disconnect_network()
            GLib.timeout_add(
                800,
                lambda: self.refresh_networks(show_animation=False)
            )


def main():
    """Main entry point"""
    win = WiFiManager()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
