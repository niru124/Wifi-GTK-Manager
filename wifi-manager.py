#!/usr/bin/env python3
"""WiFi GTK Manager - Launcher"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wifi_manager.wifi_manager import main

if __name__ == "__main__":
    main()
