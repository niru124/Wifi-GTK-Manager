"""QR code utilities"""

import subprocess
import os

QR_FILE = "/tmp/wifi_qr.png"

def generate_qr_code(ssid, password, security):
    """Generate WiFi QR code"""
    wifi_type = "WPA"
    if security == "WEP":
        wifi_type = "WEP"
    elif "WPA3" in security.upper():
        wifi_type = "WPA3"
    
    qr_string = f"WIFI:T:{wifi_type};S:{ssid};P:{password};;"
    subprocess.run(["qrencode", "-o", QR_FILE, qr_string])
    return QR_FILE

def get_qr_file():
    """Get the QR file path"""
    return QR_FILE

def qr_file_exists():
    """Check if QR file exists"""
    return os.path.exists(QR_FILE)
