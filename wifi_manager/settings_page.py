"""Settings page"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import os

class SettingsPage(Gtk.Box):
    """Settings page"""
    
    def __init__(self, main_window, back_callback):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_window = main_window
        self.back_callback = back_callback
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the settings UI"""
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(header_box, False, False, 0)
        
        btn_back = Gtk.Button.new_with_label("← Back")
        btn_back.connect("clicked", lambda w: self.back_callback())
        header_box.pack_start(btn_back, False, False, 0)
        
        lbl_title = Gtk.Label()
        lbl_title.set_text("Settings")
        header_box.pack_start(lbl_title, True, True, 0)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(20)
        content_box.set_margin_bottom(20)
        self.pack_start(content_box, True, True, 0)
        
        # Auto-Connect section
        from .nmcli_utils import get_current_ssid, get_current_connection_name, get_auto_connect
        
        label = Gtk.Label()
        label.set_text("Auto-Connect")
        content_box.pack_start(label, False, False, 10)
        
        current_ssid = get_current_ssid()
        conn_name = get_current_connection_name()
        
        if conn_name:
            autoconnect = get_auto_connect(conn_name)
            
            switch_autoconnect = Gtk.Switch()
            switch_autoconnect.set_active(autoconnect)
            switch_autoconnect.connect("state-set", lambda w, s: self._toggle_autoconnect(s))
            
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            content_box.pack_start(hbox, False, False, 5)
            
            from .dialogs import create_icon_image
            icon = create_icon_image("sync-symbolic", 16)
            hbox.pack_start(icon, False, False, 0)
            
            lbl = Gtk.Label(label=f"Auto-connect to {current_ssid}")
            lbl.set_xalign(0)
            hbox.pack_start(lbl, True, True, 0)
            hbox.pack_start(switch_autoconnect, False, False, 0)
        
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(10)
        sep.set_margin_bottom(10)
        content_box.pack_start(sep, False, False, 0)
        
        # Live Speed Display section
        label_speed = Gtk.Label()
        label_speed.set_text("Live Speed Display")
        content_box.pack_start(label_speed, False, False, 10)
        
        hbox_speed = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content_box.pack_start(hbox_speed, False, False, 5)
        
        from .dialogs import create_icon_image
        icon = create_icon_image("transmit-symbolic", 16)
        hbox_speed.pack_start(icon, False, False, 0)
        
        lbl_speed = Gtk.Label(label="Show live TX/RX speed in header")
        lbl_speed.set_xalign(0)
        hbox_speed.pack_start(lbl_speed, True, True, 0)
        
        switch_speed = Gtk.Switch()
        from .dialogs import load_settings
        show_speed = load_settings().get("show_live_speed", True)
        switch_speed.set_active(show_speed)
        switch_speed.connect("state-set", lambda w, s: self._toggle_speed(s))
        hbox_speed.pack_start(switch_speed, False, False, 0)
        
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep2.set_margin_top(10)
        sep2.set_margin_bottom(10)
        content_box.pack_start(sep2, False, False, 0)
        
        # Saved Networks section
        label_saved = Gtk.Label()
        label_saved.set_text("Saved Networks")
        content_box.pack_start(label_saved, False, False, 10)
        
        from .nmcli_utils import get_saved_connections
        
        saved = get_saved_connections()
        
        if saved:
            store = Gtk.ListStore(str, str)
            for conn in saved[:10]:
                store.append([conn['name'], conn['ssid']])
            
            tree = Gtk.TreeView(model=store)
            renderer = Gtk.CellRendererText()
            col1 = Gtk.TreeViewColumn("Profile", renderer, text=0)
            col2 = Gtk.TreeViewColumn("SSID", renderer, text=1)
            tree.append_column(col1)
            tree.append_column(col2)
            tree.set_headers_visible(True)
            
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_min_content_height(150)
            scrolled.add(tree)
            content_box.pack_start(scrolled, True, True, 5)
            
            lbl_count = Gtk.Label(label=f"Showing {len(saved)} saved networks")
            lbl_count.set_markup(f"<small>Showing {len(saved)} saved networks</small>")
            content_box.pack_start(lbl_count, False, False, 5)
        else:
            lbl_none = Gtk.Label(label="No saved networks")
            lbl_none.set_xalign(0)
            content_box.pack_start(lbl_none, False, False, 5)
    
    def _toggle_autoconnect(self, state):
        """Toggle auto-connect for current network"""
        from .nmcli_utils import get_current_connection_name, set_auto_connect
        
        conn_name = get_current_connection_name()
        if conn_name:
            set_auto_connect(conn_name, state)
    
    def _toggle_speed(self, state):
        """Toggle live speed display"""
        from .dialogs import load_settings, save_settings
        
        settings = load_settings()
        settings["show_live_speed"] = state
        save_settings(settings)


def show_settings_page(main_window, back_callback):
    """Show the settings page"""
    page = SettingsPage(main_window, back_callback)
    return page
