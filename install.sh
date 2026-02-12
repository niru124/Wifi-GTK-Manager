#!/bin/bash
# WiFi GTK Manager Installation Script

set -e

INSTALL_DIR="/opt/wifi-manager-gtk"
BIN_DIR="/usr/local/bin"
APP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/icons/hicolor/48x48/apps"

echo "Installing WiFi GTK Manager..."

# Check for required packages
if ! command -v nmcli &> /dev/null; then
    echo "Error: nmcli is required but not installed."
    exit 1
fi

# Create installation directory
sudo mkdir -p "$INSTALL_DIR"

# Copy application files
sudo cp -r wifi_manager "$INSTALL_DIR/"
sudo cp wifi-manager.py "$INSTALL_DIR/"
sudo cp -r icons "$INSTALL_DIR/"
sudo cp -r data/*.desktop "$APP_DIR/wifi-manager.desktop"

# Create launcher script
sudo tee "$BIN_DIR/wifi-manager-gtk" > /dev/null << 'EOF'
#!/bin/bash
DIR="/opt/wifi-manager-gtk"
cd "$DIR"
export PYTHONPATH="$DIR:$PYTHONPATH"
python3 "$DIR/wifi-manager.py" "$@"
EOF

sudo chmod +x "$BIN_DIR/wifi-manager-gtk"

# Create icon
sudo mkdir -p "$ICON_DIR"
if [ -f "$INSTALL_DIR/icons/wifi-manager.png" ]; then
    sudo cp "$INSTALL_DIR/icons/wifi-manager.png" "$ICON_DIR/wifi-manager.png"
    # Also install to other standard icon sizes
    for size in 16 22 24 32 64 128 256; do
        sudo mkdir -p "/usr/share/icons/hicolor/${size}x${size}/apps"
        sudo cp "$INSTALL_DIR/icons/wifi-manager.png" "/usr/share/icons/hicolor/${size}x${size}/apps/wifi-manager.png"
    done
else
    echo "Note: Custom icon not found."
fi

# Update desktop database
update-desktop-database "$APP_DIR" 2>/dev/null || true

echo ""
echo "WiFi GTK Manager installed successfully!"
echo ""
echo "You can now launch it by:"
echo "  - Running: wifi-manager-gtk"
echo "  - Searching for 'WiFi GTK Manager' in your applications menu"
echo ""
echo "To uninstall, run:"
echo "  sudo rm -rf $INSTALL_DIR"
echo "  sudo rm $BIN_DIR/wifi-manager-gtk"
echo "  sudo rm $APP_DIR/wifi-manager.desktop"
echo "  sudo rm -rf /usr/share/icons/hicolor/*/apps/wifi-manager.png"
