"""QR Code page"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

import os

QR_SIZE = 250

class QRPage(Gtk.Box):
    """QR Code page"""
    
    def __init__(self, main_window, back_callback):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_window = main_window
        self.back_callback = back_callback
        self.current_ssid = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the QR code UI"""
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(header_box, False, False, 0)
        
        btn_back = Gtk.Button.new_with_label("← Back")
        btn_back.connect("clicked", lambda w: self.back_callback())
        header_box.pack_start(btn_back, False, False, 0)
        
        lbl_title = Gtk.Label()
        lbl_title.set_text("QR Code")
        header_box.pack_start(lbl_title, True, True, 0)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(20)
        content_box.set_margin_bottom(20)
        self.pack_start(content_box, True, True, 0)
        
        lbl_select = Gtk.Label(label="Select a network to generate QR code:")
        lbl_select.set_xalign(0)
        content_box.pack_start(lbl_select, False, False, 0)
        
        combo_box = Gtk.ComboBoxText()
        combo_box.connect("changed", self._on_network_selected)
        combo_box.append("none", "-- Select Network --")
        content_box.pack_start(combo_box, False, False, 5)
        
        self.qr_image = Gtk.Image()
        self.qr_image.set_size_request(QR_SIZE, QR_SIZE)
        content_box.pack_start(self.qr_image, False, False, 10)
        
        self.lbl_ssid = Gtk.Label()
        self.lbl_ssid.set_text("Network: --")
        content_box.pack_start(self.lbl_ssid, False, False, 5)
        
        self.lbl_info = Gtk.Label()
        self.lbl_info.set_text("Select a network to generate QR code")
        self.lbl_info.set_markup("<small>Scan with your phone camera to connect</small>")
        content_box.pack_start(self.lbl_info, False, False, 5)
        
        self.combo_box = combo_box
        self._load_networks()
    
    def _load_networks(self):
        """Load available networks into combobox"""
        self.combo_box.remove_all()
        self.combo_box.append("none", "-- Select Network --")
        self.combo_box.set_active_id("none")
        
        from .nmcli_utils import get_current_ssid, get_networks, get_password, get_security
        
        current = get_current_ssid()
        networks = get_networks()
        
        for net in networks:
            ssid = net['ssid']
            security = net['security']
            password = get_password(ssid)
            label = f"{ssid} ({security})"
            if ssid == current:
                label = f"{ssid} (Connected)"
            self.combo_box.append(ssid, label)
    
    def _on_network_selected(self, combo):
        ssid = combo.get_active_id()
        if not ssid or ssid == "none":
            self._clear_qr()
            return
        
        self._generate_qr(ssid)
    
    def _generate_qr(self, ssid):
        """Generate QR code for the selected network"""
        from .nmcli_utils import get_password, get_security
        from .qr_utils import generate_qr_code, get_qr_file
        
        password = get_password(ssid)
        security = get_security(ssid)
        
        if not password:
            self._clear_qr()
            self.lbl_ssid.set_text(f"Network: {ssid}")
            self.lbl_info.set_text("No saved password - connect first")
            return
        
        generate_qr_code(ssid, password, security)
        
        qr_file = get_qr_file()
        if os.path.exists(qr_file):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(qr_file, QR_SIZE, QR_SIZE, True)
            self.qr_image.set_from_pixbuf(pixbuf)
            self.lbl_ssid.set_text(f"Network: {ssid}")
            self.lbl_info.set_text("Scan with your phone camera to connect")
        else:
            self._clear_qr()
    
    def _clear_qr(self):
        """Clear QR code display"""
        self.qr_image.clear()
        self.lbl_ssid.set_text("Network: --")
        self.lbl_info.set_text("Select a network to generate QR code")
    
    def refresh(self):
        """Refresh network list"""
        self._load_networks()


def show_qr_page(main_window, back_callback):
    """Show the QR page"""
    page = QRPage(main_window, back_callback)
    return page
