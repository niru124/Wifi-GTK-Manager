#!/usr/bin/env python3
"""
WiFi GTK Manager - Main Application
Requires: python3, pygi, nmcli, qrencode
"""

import gi
import os

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from .nmcli_utils import (
    get_current_ssid,
    get_networks,
    get_security,
    get_password,
    connect_network,
    disconnect_network,
    rescan_networks,
    get_live_speed,
    format_speed,
    is_wifi_enabled,
    set_wifi_enabled,
    get_last_connected,
)
from .dialogs import (
    show_qr_dialog,
    show_connection_info_dialog,
    show_settings_dialog,
    show_password_dialog,
    show_forget_confirm_dialog,
    show_message_dialog,
    create_icon_image,
    load_svg_icon,
    get_icon_for_signal,
    get_show_live_speed,
)

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
        self.show_live_speed = get_show_live_speed()

        self._setup_ui()
        self._start_speed_monitor()
        self.wifi_switch.set_active(is_wifi_enabled())
        self.refresh_networks()

    def _setup_ui(self):
        """Setup the main UI with stacked pages"""

        self.stack = Gtk.Stack()
        self.add(self.stack)

        # Main WiFi page
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.stack.add_named(self.main_box, "wifi")

        self._setup_main_header(self.main_box)
        self._setup_main_network_list(self.main_box)
        self._setup_main_sort_box(self.main_box)
        self._setup_main_button_box(self.main_box)

        # Hotspot page (generic: wifi/ethernet uplink, band, live clients)
        from .hotspot_dialog import show_hotspot_page
        self.hotspot_page = show_hotspot_page(self, self._show_wifi_page)
        self.stack.add_named(self.hotspot_page, "hotspot")

        self.stack.set_visible_child_name("wifi")

    def _show_hotspot_page(self):
        """Switch to the hotspot page and refresh it."""
        try:
            self.hotspot_page.refresh_all()
        except Exception:
            pass
        self.stack.set_visible_child_name("hotspot")

    def _show_wifi_page(self):
        """Back to the main WiFi list."""
        self.stack.set_visible_child_name("wifi")
        self.refresh_networks(show_animation=False)

    def _setup_main_header(self, parent):
        """Setup the header section"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_start(10)
        header_box.set_margin_end(10)
        header_box.set_margin_top(10)
        parent.pack_start(header_box, False, False, 0)

        # WiFi toggle switch
        wifi_label = Gtk.Label(label="WiFi:")
        header_box.pack_start(wifi_label, False, False, 5)

        self.wifi_switch = Gtk.Switch()
        self.wifi_switch.set_tooltip_text("Toggle WiFi")
        self.wifi_switch.connect("state-set", self._on_wifi_toggle)
        header_box.pack_start(self.wifi_switch, False, False, 0)

        self.spinner = Gtk.Spinner()
        header_box.pack_start(self.spinner, False, False, 0)

        # Current connection with icon
        self.current_icon = create_icon_image("network-wireless-symbolic", 16)
        header_box.pack_start(self.current_icon, False, False, 0)

        self.current_label = Gtk.Label()
        header_box.pack_start(self.current_label, True, True, 0)

        # Live speed display
        self.speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        header_box.pack_start(self.speed_box, False, False, 0)

        rx_icon = create_icon_image("go-down-symbolic", 12)
        self.speed_box.pack_start(rx_icon, False, False, 0)

        self.rx_label = Gtk.Label()
        self.rx_label.set_markup("<small>↓0 B/s</small>")
        self.speed_box.pack_start(self.rx_label, False, False, 0)

        tx_icon = create_icon_image("go-up-symbolic", 12)
        self.speed_box.pack_start(tx_icon, False, False, 0)

        self.tx_label = Gtk.Label()
        self.tx_label.set_markup("<small>↑0 B/s</small>")
        self.speed_box.pack_start(self.tx_label, False, False, 0)

        # Settings button with icon
        btn_settings = Gtk.Button()
        btn_settings.set_tooltip_text("Settings")
        settings_icon = create_icon_image("preferences-system-symbolic")
        btn_settings.add(settings_icon)
        btn_settings.connect("clicked", self._on_settings)
        header_box.pack_start(btn_settings, False, False, 0)

        self.status_label = Gtk.Label()
        self.status_label.set_markup("<small>Ready</small>")
        self.status_label.set_xalign(0)
        self.status_label.set_margin_start(10)
        self.status_label.set_margin_end(10)
        parent.pack_start(self.status_label, False, False, 5)

    def _start_speed_monitor(self):
        """Start live speed monitoring"""
        GLib.timeout_add(1000, self._update_speed_display)

    def _update_speed_display(self):
        """Update speed display in header"""
        if not self.show_live_speed:
            self.speed_box.hide()
        else:
            self.speed_box.show()
            rx_speed, tx_speed = get_live_speed()

            rx_text = format_speed(rx_speed)
            tx_text = format_speed(tx_speed)

            self.rx_label.set_markup(f"<small>↓{rx_text}</small>")
            self.tx_label.set_markup(f"<small>↑{tx_text}</small>")

        # Update current connection icon
        current = get_current_ssid()
        if current:
            self.current_icon.set_from_icon_name(
                "network-wireless-symbolic", Gtk.IconSize.BUTTON
            )
        else:
            self.current_icon.set_from_icon_name(
                "network-wireless-disconnected-symbolic", Gtk.IconSize.BUTTON
            )

        return True

    def _setup_main_network_list(self, parent):
        """Setup the network list treeview with search"""
        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        search_box.set_margin_start(10)
        search_box.set_margin_end(10)
        search_box.set_margin_top(5)
        parent.pack_start(search_box, False, False, 0)

        search_icon = Gtk.Image.new_from_icon_name(
            "system-search-symbolic", Gtk.IconSize.BUTTON
        )
        search_box.pack_start(search_icon, False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search networks...")
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)

        # Network list
        self.store = Gtk.ListStore(str, str, str, bool)
        self.store_filtered = self.store.filter_new()
        self.tree = Gtk.TreeView(model=self.store_filtered)

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

        # Set up filter function
        self.store_filtered.set_visible_func(self._filter_networks)

    def _on_search_changed(self, entry):
        """Handle search text changes"""
        self.store_filtered.refilter()

    def _filter_networks(self, model, iter, data):
        """Filter networks based on search text"""
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True
        ssid = model[iter][0].lower()
        return search_text in ssid

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

        # Refresh button with text
        self.btn_refresh = Gtk.Button.new_with_label("Refresh")
        self.btn_refresh.set_tooltip_text("Refresh networks")
        self.btn_refresh.connect("clicked", self._on_refresh)
        btn_box.pack_start(self.btn_refresh, True, True, 0)

        # Connect button
        btn_connect = Gtk.Button()
        btn_connect.set_tooltip_text("Connect")
        connect_icon = load_svg_icon("connect", 16)
        btn_connect.add(connect_icon)
        btn_connect.connect("clicked", self._on_connect)
        btn_box.pack_start(btn_connect, True, True, 0)

        # Disconnect button
        btn_disconnect = Gtk.Button()
        btn_disconnect.set_tooltip_text("Disconnect")
        disconnect_icon = load_svg_icon("disconnect", 16)
        btn_disconnect.add(disconnect_icon)
        btn_disconnect.connect("clicked", self._on_disconnect)
        btn_box.pack_start(btn_disconnect, True, True, 0)

        # QR Code button
        btn_qr = Gtk.Button()
        btn_qr.set_tooltip_text("QR Code")
        qr_icon = load_svg_icon("qr-code", 16)
        btn_qr.add(qr_icon)
        btn_qr.connect("clicked", self._on_show_qr)
        btn_box.pack_start(btn_qr, True, True, 0)

        # Details button
        btn_info = Gtk.Button()
        btn_info.set_tooltip_text("Details")
        info_icon = create_icon_image("dialog-information-symbolic")
        btn_info.add(info_icon)
        btn_info.connect("clicked", lambda w: show_connection_info_dialog(self))
        btn_box.pack_start(btn_info, True, True, 0)

        # Hotspot button
        btn_hotspot = Gtk.Button()
        btn_hotspot.set_tooltip_text("Hotspot (share WiFi/Ethernet)")
        hotspot_icon = load_svg_icon("hotspot", 16)
        btn_hotspot.add(hotspot_icon)
        btn_hotspot.connect("clicked", lambda w: self._show_hotspot_page())
        btn_box.pack_start(btn_hotspot, True, True, 0)

        # Forget button
        btn_forget = Gtk.Button()
        btn_forget.set_tooltip_text("Forget Network")
        forget_icon = create_icon_image("edit-delete-symbolic")
        btn_forget.add(forget_icon)
        btn_forget.connect("clicked", self._on_forget)
        btn_box.pack_start(btn_forget, True, True, 0)

    def _on_wifi_toggle(self, widget, state):
        """Handle WiFi toggle switch"""
        self.wifi_switch.set_sensitive(False)

        if set_wifi_enabled(state):
            if state:
                self._update_status("WiFi enabled - Scanning...")
                GLib.timeout_add(
                    300, lambda: self.refresh_networks(show_animation=True)
                )
            else:
                self._update_status("WiFi disabled")
                self.current_label.set_text(" WiFi Off")
                self.store.clear()
        else:
            self._update_status("Failed to toggle WiFi")

        self.wifi_switch.set_sensitive(True)

    def _on_settings(self, widget):
        """Handle settings button click"""
        self.stack.set_visible_child_name("settings")

    def _set_refreshing(self, refreshing):
        """Update UI during refresh"""
        if refreshing:
            self.spinner.start()
            # Create spinner button
            self.btn_refresh.remove(self.btn_refresh.get_child())
            spinner = Gtk.Spinner()
            spinner.start()
            self.btn_refresh.add(spinner)
            self.status_label.set_markup(
                "<small><i>Scanning for networks...</i></small>"
            )
        else:
            self.spinner.stop()
            # Restore refresh button
            self.btn_refresh.set_label("Refresh")

    def _update_status(self, message):
        """Update status label"""
        self.status_label.set_markup(f"<small>{message}</small>")

    def _sort_networks(self, networks):
        """Sort networks based on current sort option"""
        if self.current_sort == SORT_NAME:
            return sorted(networks, key=lambda x: x["ssid"].lower())
        elif self.current_sort == SORT_SECURITY:
            return sorted(networks, key=lambda x: x["security"])
        else:
            return sorted(
                networks,
                key=lambda x: int(x["signal"]) if x["signal"].isdigit() else 0,
                reverse=True,
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
            self.current_label.set_text(f" {current}")
            self._update_status(f"Found {len(networks)} networks")
        else:
            self.current_label.set_text(" Not Connected")
            self._update_status(f"Found {len(networks)} networks")

        for net in networks:
            self.store.append(
                [net["ssid"], net["signal"] + "%", net["security"], net["connected"]]
            )

        self.wifi_switch.set_active(is_wifi_enabled())
        self._set_refreshing(False)
        return False

    def _on_refresh(self, widget):
        """Handle refresh button click"""
        self.refresh_networks(show_animation=True)

    def _on_connect(self, widget):
        """Handle connect button click - try selected or last connected network"""
        ssid = None

        # First, try to get currently selected network from the list
        selection = self.tree.get_selection()
        model, iter = selection.get_selected()
        if iter:
            ssid = model[iter][0]
        else:
            # If nothing selected, try to connect to current network if connected
            current = get_current_ssid()
            if current:
                self._update_status(f"Already connected to {current}")
                return

            # Get currently visible networks
            networks = get_networks()
            visible_ssids = {net["ssid"] for net in networks if net["ssid"]}

            # Get saved connections
            from .nmcli_utils import get_saved_connections, get_password

            saved = get_saved_connections()

            # Try to find a visible saved network with password
            ssid = None
            for conn in saved:
                conn_ssid = conn["ssid"]
                # Only consider networks that are currently visible
                if conn_ssid in visible_ssids:
                    # Check if we have a password for this network
                    if get_password(conn["name"]):
                        ssid = conn_ssid
                        break

            if ssid:
                self._update_status(f"Connecting to {ssid}...")
            else:
                self._update_status("No available networks with saved passwords")
                return

        if ssid:
            # Check if already connected to this network
            current = get_current_ssid()
            if current == ssid:
                self._update_status(f"Already connected to {ssid}")
                return
            self._connect_to_network(ssid)

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
            self._update_status(f"Connected to {ssid}!")
            # Refresh immediately to show new connection status
            self.refresh_networks(show_animation=False)
            # Update UI to reflect connection change
            current = get_current_ssid()
            if current:
                self.current_label.set_text(f" {current}")
            show_message_dialog(
                self,
                "Connected",
                f"Successfully connected to {ssid}",
                Gtk.MessageType.INFO,
            )
            # Refresh again after dialog closes to ensure UI is updated
            GLib.timeout_add(100, lambda: self.refresh_networks(show_animation=False))
        else:
            self._set_refreshing(False)
            self._update_status("Connection failed")
            show_message_dialog(
                self,
                "Connection Failed",
                "Could not connect to the network",
                Gtk.MessageType.ERROR,
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
                    self,
                    "No Network Selected",
                    "No WiFi network is currently connected",
                    Gtk.MessageType.WARNING,
                )
                return

        password = get_password(ssid)
        security = get_security(ssid)
        self._update_status(f"<small>Generating QR for {ssid}...</small>")

        # Process pending GTK events to update status
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

        GLib.timeout_add(
            100, lambda: self._show_qr_and_update(ssid, password, security)
        )

    def _show_qr_and_update(self, ssid, password, security):
        """Show QR dialog and update status after"""
        show_qr_dialog(self, ssid, password, security)
        self._update_status("QR code closed")
        return False

    def _on_settings(self, widget):
        """Handle settings button click"""
        result = show_settings_dialog(self)
        if result:
            show_speed = result.get("show_speed", True)
            self.show_live_speed = show_speed
            self._update_speed_display()

    def _on_forget(self, widget):
        """Handle forget button click - show dialog to select from all saved networks"""
        from .nmcli_utils import get_saved_connections, forget_network

        saved = get_saved_connections()

        if not saved:
            show_message_dialog(
                self,
                "No Saved Networks",
                "No saved networks to forget",
                Gtk.MessageType.INFO,
            )
            return

        # Create dialog to select network to forget
        dialog = Gtk.Dialog(title="Forget Network", transient_for=self, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Forget", Gtk.ResponseType.OK)
        dialog.set_default_size(350, 450)

        box = dialog.get_content_area()
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)

        lbl = Gtk.Label(label="Select a network to forget:")
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 5)

        # Search entry
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search networks...")
        box.pack_start(search_entry, False, False, 5)

        # Create list of saved networks
        self.forget_store = Gtk.ListStore(str, str)  # SSID, Profile Name
        self.forget_store_filtered = self.forget_store.filter_new()
        current = get_current_ssid()

        for conn in saved:
            ssid = conn["ssid"]
            name = conn["name"]
            self.forget_store.append([ssid, name])

        def on_search_changed(entry):
            search_text = entry.get_text().lower()
            self.forget_store_filtered.refilter()

        def filter_func(model, iter, data):
            search_text = search_entry.get_text().lower()
            if not search_text:
                return True
            ssid = model[iter][0].lower()
            return search_text in ssid

        self.forget_store_filtered.set_visible_func(filter_func)
        search_entry.connect("search-changed", on_search_changed)

        tree = Gtk.TreeView(model=self.forget_store_filtered)
        tree.set_headers_visible(False)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Network", renderer, text=0)
        tree.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.add(tree)
        box.pack_start(scrolled, True, True, 10)

        # Show current connection info
        if current:
            lbl_current = Gtk.Label(label=f"Currently connected to: {current}")
            lbl_current.set_xalign(0)
            box.pack_start(lbl_current, False, False, 5)

        box.show_all()

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            selection = tree.get_selection()
            model, iter = selection.get_selected()
            if iter:
                ssid = model[iter][0]
                profile_name = model[iter][1]

                if show_forget_confirm_dialog(self, ssid):
                    if forget_network(profile_name):
                        self._update_status(f"Forgot {ssid}")
                        GLib.timeout_add(
                            300, lambda: self.refresh_networks(show_animation=False)
                        )
                    else:
                        show_message_dialog(
                            self,
                            "Error",
                            f"Could not forget {ssid}",
                            Gtk.MessageType.ERROR,
                        )

        dialog.destroy()

    def _on_disconnect(self, widget):
        """Handle disconnect button click"""
        current = get_current_ssid()
        if current:
            self._update_status(f"<i>Disconnecting from {current}...</i>")
            self._set_refreshing(True)
            disconnect_network()
            GLib.timeout_add(800, lambda: self.refresh_networks(show_animation=False))


def main():
    """Main entry point"""
    win = WiFiManager()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
