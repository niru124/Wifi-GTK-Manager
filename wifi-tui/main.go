package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

type WiFiNetwork struct {
	SSID     string
	Signal   string
	Security string
	InUse    bool
	Rate     string
}

func runCommandTimeout(name string, args ...string) string {
	cmd := exec.Command(name, args...)
	output, err := cmd.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(output))
}

func getCurrentConnection() string {
	output := runCommandTimeout("nmcli", "-t", "connection", "show", "--active")
	scanner := bufio.NewScanner(strings.NewReader(output))
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, "802-11-wireless") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) >= 2 {
				name := parts[0]
				details := runCommandTimeout("nmcli", "-t", "connection", "show", name)
				for _, d := range strings.Split(details, "\n") {
					if strings.HasPrefix(d, "802-11-wireless.ssid:") {
						return strings.SplitN(d, ":", 2)[1]
					}
				}
			}
		}
	}
	return ""
}

func parseWiFiList() []WiFiNetwork {
	output := runCommandTimeout("nmcli", "-t", "device", "wifi", "list")
	currentSSID := getCurrentConnection()

	var networks []WiFiNetwork
	scanner := bufio.NewScanner(strings.NewReader(output))
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		parts := strings.Split(line, ":")
		if len(parts) < 7 {
			continue
		}

		inUse := strings.HasPrefix(parts[0], "*")
		ssid := parts[1]
		signal := parts[5]
		security := parts[6]

		if ssid == "" {
			ssid = "Hidden Network"
		}

		network := WiFiNetwork{
			SSID:     ssid,
			Signal:   signal,
			Security: security,
			InUse:    inUse || ssid == currentSSID,
		}
		networks = append(networks, network)
	}
	return networks
}

func getSSIDSecurity(ssid string) string {
	networks := parseWiFiList()
	for _, net := range networks {
		if net.SSID == ssid {
			return net.Security
		}
	}
	return "WPA2"
}

func getNetworkPassword(ssid string) string {
	output := runCommandTimeout("nmcli", "-t", "connection", "show", ssid)
	for _, line := range strings.Split(output, "\n") {
		if strings.HasPrefix(line, "802-11-wireless-security.psk:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) >= 2 {
				return parts[1]
			}
		}
	}
	return ""
}

func connectToNetwork(ssid, password string) bool {
	cmd := exec.Command("nmcli", "device", "wifi", "connect", ssid)
	if password != "" {
		cmd = exec.Command("nmcli", "device", "wifi", "connect", ssid, "password", password)
	}
	_, err := cmd.Output()
	return err == nil
}

func disconnectNetwork(ssid string) bool {
	cmd := exec.Command("nmcli", "connection", "down", ssid)
	_, err := cmd.Output()
	return err == nil
}

func showQRCode(ssid, password, security string) {
	wifiType := "WPA"
	if security == "WEP" {
		wifiType = "WEP"
	} else if strings.Contains(security, "WPA3") {
		wifiType = "WPA3"
	}

	qrString := fmt.Sprintf("WIFI:T:%s;S:%s;P:%s;;", wifiType, ssid, password)

	tmpFile := "/tmp/wifi_qr.png"
	runCommandTimeout("qrencode", "-o", tmpFile, qrString)

	fmt.Printf("\n\033[2J\033[H")
	fmt.Printf("\n📶 QR Code for WiFi: %s\n", ssid)
	fmt.Printf("Type: %s\n\n", security)

	cmd := exec.Command("kitten", "icat", "--align", "center", tmpFile)
	cmd.Stdout = os.Stdout
	cmd.Run()

	fmt.Println("\n\nPress Enter to continue...")
	bufio.NewReader(os.Stdin).ReadString('\n')
}

func showNetworkDetails(ssid string) {
	fmt.Printf("\n\033[2J\033[H")
	fmt.Printf("\n📶 Network Details: %s\n\n", ssid)

	security := getSSIDSecurity(ssid)
	password := getNetworkPassword(ssid)

	fmt.Printf("SSID: %s\n", ssid)
	fmt.Printf("Security: %s\n", security)
	fmt.Printf("Password: %s\n", password)
	fmt.Printf("QR Code: Available\n")

	fmt.Println("\n\nPress Enter to go back...")
	bufio.NewReader(os.Stdin).ReadString('\n')
}

func main() {
	for {
		networks := parseWiFiList()
		currentSSID := getCurrentConnection()

		var choices []string
		for _, net := range networks {
			status := "○"
			if net.InUse {
				status = "●"
			}
			signalBar := "▂▄▆█"
			sigVal := 0
			fmt.Sscanf(net.Signal, "%d", &sigVal)
			if sigVal < 50 {
				signalBar = "▂▄__"
			} else if sigVal < 70 {
				signalBar = "▂▄▆_"
			}
			choices = append(choices, fmt.Sprintf("%s %s %s %s", status, net.SSID, signalBar, net.Security))
		}

		choices = append(choices, "🔄 Refresh Networks")
		choices = append(choices, "📱 Show QR Code (Current)")
		choices = append(choices, "❌ Exit")

		gumArgs := append([]string{"choose", "--header", "WiFi Manager - Connected: " + currentSSID, "--item.padding", "0 2", "--selected.prefix", " ", "--selected.suffix", " "}, choices...)

		choice := runCommandTimeout("gum", gumArgs...)

		if choice == "🔄 Refresh Networks" {
			continue
		}

		if choice == "📱 Show QR Code (Current)" {
			if currentSSID != "" {
				security := getSSIDSecurity(currentSSID)
				password := getNetworkPassword(currentSSID)
				showQRCode(currentSSID, password, security)
			} else {
				fmt.Println("\nNo WiFi connected!")
				fmt.Println("Press Enter to continue...")
				bufio.NewReader(os.Stdin).ReadString('\n')
			}
			continue
		}

		if choice == "❌ Exit" {
			break
		}

		for _, net := range networks {
			choiceStr := fmt.Sprintf("● %s", net.SSID)
			if choice == choiceStr && net.InUse {
				action := runCommandTimeout("gum", "choose", "--header", "Actions for "+net.SSID, "Show Details", "Show QR Code", "Disconnect", "Go Back")

				if action == "Show Details" {
					showNetworkDetails(net.SSID)
				} else if action == "Show QR Code" {
					security := getSSIDSecurity(net.SSID)
					password := getNetworkPassword(net.SSID)
					showQRCode(net.SSID, password, security)
				} else if action == "Disconnect" {
					disconnectNetwork(net.SSID)
				}
				break
			} else if choice == fmt.Sprintf("○ %s", net.SSID) {
				var password string
				if net.Security != "Open" {
					password = runCommandTimeout("gum", "input", "--placeholder", "Enter password", "--password")
				}

				if connectToNetwork(net.SSID, password) {
					runCommandTimeout("gum", "spin", "--spinner", "points", "--title", "Connecting...", "--", "sleep", "2")
					fmt.Println("Connected successfully!")
				} else {
					fmt.Println("Failed to connect!")
				}
				break
			}
		}
	}
}
