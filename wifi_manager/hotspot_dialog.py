"""Hotspot page: upstream (wifi/ethernet) -> AP with live clients.

Generic: no hardcoded interfaces, SSIDs or channels. Everything is
discovered via hotspot_utils at runtime.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import threading

from . import hotspot_utils as hu
from .dialogs import show_message_dialog, show_qr_dialog


class HotspotPage(Gtk.Box):
    """Hotspot configuration + client monitoring page."""

    def __init__(self, main_window, back_callback):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_window = main_window
        self.back_callback = back_callback
        self._busy = False
        self._timer_id = None
        self._ap_iface = None

        self._setup_ui()
        self._load_saved()
        self.refresh_all()
        self._timer_id = GLib.timeout_add_seconds(2, self._periodic)

    # ------------------------------------------------------------- UI

    def _setup_ui(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.set_margin_start(10)
        header.set_margin_end(10)
        header.set_margin_top(10)
        self.pack_start(header, False, False, 0)

        btn_back = Gtk.Button.new_with_label("\u2190 Back")
        btn_back.connect("clicked", lambda w: self.back_callback())
        header.pack_start(btn_back, False, False, 0)

        title = Gtk.Label()
        title.set_markup("<b>WiFi Hotspot</b>")
        header.pack_start(title, True, True, 0)

        self.dot = Gtk.Label(label="\u25cb")
        header.pack_start(self.dot, False, False, 0)
        self.lbl_status = Gtk.Label(label="Checking...")
        self.lbl_status.set_xalign(0)
        header.pack_start(self.lbl_status, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(8)
        grid.set_margin_start(15)
        grid.set_margin_end(15)
        self.pack_start(grid, False, False, 0)

        # Upstream (internet source)
        grid.attach(Gtk.Label(label="Share from:", xalign=0), 0, 0, 1, 1)
        self.cmb_upstream = Gtk.ComboBoxText()
        self.cmb_upstream.set_hexpand(True)
        self.cmb_upstream.set_tooltip_text(
            "Uplink that provides internet. Auto = default route. "
            "Ethernet = classic hotspot. Same WiFi = repeater mode.")
        grid.attach(self.cmb_upstream, 1, 0, 1, 1)

        # AP interface
        grid.attach(Gtk.Label(label="Hotspot on:", xalign=0), 0, 1, 1, 1)
        self.cmb_ap = Gtk.ComboBoxText()
        self.cmb_ap.set_hexpand(True)
        self.cmb_ap.set_tooltip_text("WiFi radio that broadcasts the AP.")
        grid.attach(self.cmb_ap, 1, 1, 1, 1)

        # SSID
        grid.attach(Gtk.Label(label="Name (SSID):", xalign=0), 0, 2, 1, 1)
        self.entry_ssid = Gtk.Entry()
        self.entry_ssid.set_placeholder_text("MyHotspot")
        self.entry_ssid.set_hexpand(True)
        grid.attach(self.entry_ssid, 1, 2, 1, 1)

        # Password
        grid.attach(Gtk.Label(label="Password:", xalign=0), 0, 3, 1, 1)
        pwbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pwbox.set_hexpand(True)
        self.entry_pass = Gtk.Entry()
        self.entry_pass.set_visibility(False)
        self.entry_pass.set_placeholder_text("min 8 chars, empty = open")
        self.entry_pass.set_hexpand(True)
        pwbox.pack_start(self.entry_pass, True, True, 0)
        self.chk_show = Gtk.CheckButton(label="Show")
        self.chk_show.connect(
            "toggled", lambda c: self.entry_pass.set_visibility(c.get_active()))
        pwbox.pack_start(self.chk_show, False, False, 0)
        grid.attach(pwbox, 1, 3, 1, 1)

        # Band
        grid.attach(Gtk.Label(label="Band:", xalign=0), 0, 4, 1, 1)
        self.cmb_band = Gtk.ComboBoxText()
        self.cmb_band.append("auto", "Auto")
        self.cmb_band.append("2.4", "2.4 GHz")
        self.cmb_band.append("5", "5 GHz")
        self.cmb_band.set_active_id("auto")
        self.cmb_band.connect("changed", self._on_band_changed)
        grid.attach(self.cmb_band, 1, 4, 1, 1)

        # Channel
        grid.attach(Gtk.Label(label="Channel:", xalign=0), 0, 5, 1, 1)
        self.cmb_chan = Gtk.ComboBoxText()
        grid.attach(self.cmb_chan, 1, 5, 1, 1)
        self._fill_channels("auto")

        # Actions
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        actions.set_margin_start(15)
        actions.set_margin_end(15)
        self.pack_start(actions, False, False, 0)

        self.btn_toggle = Gtk.Button.new_with_label("\u25b6 Start Hotspot")
        self.btn_toggle.connect("clicked", self._on_toggle)
        actions.pack_start(self.btn_toggle, True, True, 0)

        btn_refresh = Gtk.Button.new_with_label("Refresh")
        btn_refresh.set_tooltip_text("Rescan interfaces and clients")
        btn_refresh.connect("clicked", lambda w: self.refresh_all())
        actions.pack_start(btn_refresh, False, False, 0)

        btn_qr = Gtk.Button.new_with_label("QR")
        btn_qr.set_tooltip_text("Show QR code for this hotspot")
        btn_qr.connect("clicked", self._on_qr)
        actions.pack_start(btn_qr, False, False, 0)

        self.lbl_info = Gtk.Label()
        self.lbl_info.set_xalign(0)
        self.lbl_info.set_line_wrap(True)
        self.lbl_info.set_margin_start(15)
        self.lbl_info.set_margin_end(15)
        self.pack_start(self.lbl_info, False, False, 0)

        # Clients
        self.lbl_clients = Gtk.Label()
        self.lbl_clients.set_markup("<b>Connected devices (0)</b>")
        self.lbl_clients.set_xalign(0)
        self.lbl_clients.set_margin_start(15)
        self.pack_start(self.lbl_clients, False, False, 0)

        self.store = Gtk.ListStore(str, str, str, str, str, str)
        tree = Gtk.TreeView(model=self.store)
        self.tree = tree
        for i, col_name in enumerate(
                ["Host", "IP", "MAC", "RX", "TX", "Signal"]):
            rend = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(col_name, rend, text=i)
            col.set_resizable(True)
            col.set_min_width(90 if i < 3 else 70)
            tree.append_column(col)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(160)
        scroll.add(tree)
        scroll.set_margin_start(15)
        scroll.set_margin_end(15)
        scroll.set_margin_bottom(10)
        self.pack_start(scroll, True, True, 0)

    # ------------------------------------------------------------- data

    def _load_saved(self):
        cfg = hu.load_hotspot_profile() or {}
        if cfg.get("SSID"):
            self.entry_ssid.set_text(cfg["SSID"])
        else:
            self.entry_ssid.set_text("MyHotspot")
        if cfg.get("PASSWORD"):
            self.entry_pass.set_text(cfg["PASSWORD"])
        band = cfg.get("BAND", "auto")
        if band not in ("auto", "2.4", "5"):
            band = "auto"
        self.cmb_band.set_active_id(band)
        self._saved_iface = cfg.get("INTERFACE", "")

    def _fill_channels(self, band):
        active = self.cmb_chan.get_active_id()
        self.cmb_chan.remove_all()
        chans = hu.channels_for_band(band if band in ("2.4", "5") else "2.4")
        for c in chans:
            label = "Auto" if c == 0 else str(c)
            self.cmb_chan.append(str(c), label)
        if active in [str(c) for c in chans]:
            self.cmb_chan.set_active_id(active)
        else:
            self.cmb_chan.set_active_id("0")

    def _on_band_changed(self, combo):
        self._fill_channels(combo.get_active_id())

    def _upstream_id(self):
        uid = self.cmb_upstream.get_active_id()
        return None if uid in (None, "auto") else uid

    def _ap_id(self):
        aid = self.cmb_ap.get_active_id()
        return None if aid in (None, "auto") else aid

    def refresh_all(self):
        """Rescan interfaces, status, clients."""
        # Upstream combo
        cur_up = self.cmb_upstream.get_active_id()
        self.cmb_upstream.remove_all()
        self.cmb_upstream.append("auto", "Auto (default route)")
        for d in hu.list_upstream_candidates():
            label = f"{d['device']} ({d['type']}, {d['state']})"
            self.cmb_upstream.append(d["device"], label)
        ids = ["auto"] + [d["device"] for d in hu.list_upstream_candidates()]
        self.cmb_upstream.set_active_id(
            cur_up if cur_up in ids else "auto")

        # AP combo
        cur_ap = self.cmb_ap.get_active_id()
        self.cmb_ap.remove_all()
        self.cmb_ap.append("auto", "Auto (first WiFi)")
        for w in hu.list_wifi_interfaces():
            self.cmb_ap.append(w, w)
        for v in hu.list_ap_interfaces():
            if v not in hu.list_wifi_interfaces():
                self.cmb_ap.append(v, f"{v} (AP)")
        ap_ids = ["auto"] + hu.list_wifi_interfaces() + [
            v for v in hu.list_ap_interfaces()
            if v not in hu.list_wifi_interfaces()]
        if getattr(self, "_saved_iface", "") in ap_ids and cur_ap in (None, "auto"):
            self.cmb_ap.set_active_id(self._saved_iface)
        else:
            self.cmb_ap.set_active_id(cur_ap if cur_ap in ap_ids else "auto")

        self._refresh_status()
        self._refresh_clients()

    def _refresh_status(self):
        info = hu.get_hotspot_info()
        ap = hu.get_active_ap()
        if info.get("status") == "running":
            self.dot.set_markup(
                '<span foreground="green">\u25cf</span>')
            if ap:
                self._ap_iface = ap.get("device")
                self.lbl_status.set_markup(
                    f"Running: <b>{GLib.markup_escape_text(ap.get('ssid',''))}</b>"
                    f" on {GLib.markup_escape_text(ap.get('device',''))}")
            else:
                self.lbl_status.set_text(f"Running ({info.get('tool','')})")
            self.btn_toggle.set_label("\u25a0 Stop Hotspot")
        else:
            self.dot.set_text("\u25cb")
            self.lbl_status.set_text("Not running")
            self.btn_toggle.set_label("\u25b6 Start Hotspot")
            self._ap_iface = self._ap_id() or None
        self.btn_toggle.set_sensitive(not self._busy)

        # capability hint (generic, from live `iw list`)
        sup, share, _ = hu.parse_concurrent_support()
        route = hu.get_default_route_iface() or "none"
        if sup:
            mode = "must share one channel" if share else "multi-channel OK"
            cap = f"Same-radio WiFi sharing supported ({mode})."
        else:
            cap = "Same-radio WiFi sharing NOT detected; use Ethernet uplink or 2nd adapter."
        tool, _ = hu.get_tool()
        helper = f"Helper: {tool}" if tool else "Helper: none (NM only)"
        self.lbl_info.set_markup(
            f"<small>Default route: {GLib.markup_escape_text(str(route))}  |  "
            f"{GLib.markup_escape_text(cap)}  {GLib.markup_escape_text(helper)}</small>")

    def _refresh_clients(self):
        try:
            clients = hu.get_connected_clients(self._ap_iface)
        except Exception:
            clients = []
        self.store.clear()
        for c in sorted(clients, key=lambda x: x.get("mac", "")):
            sig = c.get("signal")
            sig_txt = f"{sig} dBm" if isinstance(sig, int) else "N/A"
            self.store.append([
                c.get("hostname", "Unknown") or "Unknown",
                c.get("ip", "N/A") or "N/A",
                c.get("mac", "") or "",
                hu.format_bytes(c.get("rx_bytes", 0)),
                hu.format_bytes(c.get("tx_bytes", 0)),
                sig_txt,
            ])
        self.lbl_clients.set_markup(
            f"<b>Connected devices ({len(clients)})</b>")

    def _periodic(self):
        try:
            if self.get_visible():
                self._refresh_status()
                self._refresh_clients()
        except Exception:
            pass
        return True

    # ------------------------------------------------------------- actions

    def _on_toggle(self, widget):
        info = hu.get_hotspot_info()
        if info.get("status") == "running":
            self._stop_async()
        else:
            self._start_async()

    def _start_async(self):
        ssid = self.entry_ssid.get_text().strip()
        password = self.entry_pass.get_text()
        band = self.cmb_band.get_active_id() or "auto"
        try:
            channel = int(self.cmb_chan.get_active_id() or "0")
        except Exception:
            channel = 0
        if not ssid:
            show_message_dialog(self.main_window, "Error",
                                "Please enter a network name",
                                Gtk.MessageType.ERROR)
            return
        if password and len(password) < 8:
            show_message_dialog(self.main_window, "Error",
                                "Password must be at least 8 characters (or empty for open)",
                                Gtk.MessageType.ERROR)
            return
        self._busy = True
        self.btn_toggle.set_sensitive(False)
        self.btn_toggle.set_label("Starting...")
        self.lbl_status.set_text("Starting hotspot...")

        upstream = self._upstream_id()
        ap_iface = self._ap_id()

        def work():
            ok, msg = hu.create_hotspot(
                ssid, password, interface=ap_iface, band=band,
                channel=channel, upstream=upstream)
            if ok:
                hu.save_hotspot_profile(ssid, password, ap_iface or "", band)
            GLib.idle_add(self._done_start, ok, msg)
        threading.Thread(target=work, daemon=True).start()

    def _done_start(self, ok, msg):
        self._busy = False
        self.refresh_all()
        show_message_dialog(
            self.main_window, "Hotspot" if ok else "Error", msg,
            Gtk.MessageType.INFO if ok else Gtk.MessageType.ERROR)
        return False

    def _stop_async(self):
        self._busy = True
        self.btn_toggle.set_sensitive(False)
        self.btn_toggle.set_label("Stopping...")

        def work():
            hu.stop_hotspot()
            GLib.idle_add(self._done_stop)
        threading.Thread(target=work, daemon=True).start()

    def _done_stop(self):
        self._busy = False
        self.refresh_all()
        return False

    def _on_qr(self, widget):
        ssid = self.entry_ssid.get_text().strip()
        password = self.entry_pass.get_text()
        if not ssid:
            show_message_dialog(self.main_window, "QR Code",
                                "Enter an SSID first",
                                Gtk.MessageType.WARNING)
            return
        ap = hu.get_active_ap()
        sec = "WPA2" if password else "Open"
        show_qr_dialog(self.main_window, ssid, password, sec)


def show_hotspot_page(main_window, back_callback):
    """Factory used by the main window."""
    return HotspotPage(main_window, back_callback)
