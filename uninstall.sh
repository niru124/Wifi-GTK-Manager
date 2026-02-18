#!/bin/bash

# Main function
uninstall() {
	local choice='n'
	read -rp "Do you really want to uninstall Wifi Manager GTK (y/n)? " choice
	choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')

	# Use robust string comparison
	if [[ "$choice" == 'y' ]]; then
		echo "Starting uninstallation..."

		# List of items to remove
		declare -a ITEMS_TO_REMOVE=(
			"/opt/wifi-manager-gtk"
			"/usr/local/bin/wifi-manager-gtk"
			"/usr/share/applications/wifi-manager.desktop"
		)
		# Handle icons separately due to globbing and potential non-existence
		declare -a ICON_GLOBS=(
			"/usr/share/icons/hicolor/*/apps/wifi-manager.png"
		)

		# Remove main application files/directories
		for item in "${ITEMS_TO_REMOVE[@]}"; do
			echo "Attempting to remove: $item"
			if sudo rm -rf "$item"; then
				echo "Successfully removed: $item"
			else
				echo "Failed to remove: $item (It might not exist or there's a permission issue)." >&2
			fi
		done

		# Remove icons, handling potential globbing and non-existence gracefully
		for glob_path in "${ICON_GLOBS[@]}"; do
			echo "Attempting to remove icons matching: $glob_path"
			# Use 'ls' to check if any files match the glob before attempting to remove
			if ls $glob_path >/dev/null 2>&1; then
				if sudo rm -f $glob_path; then # Use -f for files
					echo "Successfully removed icons matching: $glob_path"
				else
					echo "Failed to remove icons matching: $glob_path." >&2
				fi
			else
				echo "No icons found matching: $glob_path."
			fi
		done

		echo "Uninstallation complete."
	else
		echo "Uninstallation cancelled."
	fi
}

uninstall
