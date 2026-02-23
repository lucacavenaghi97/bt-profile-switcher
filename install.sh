#!/usr/bin/env bash
set -euo pipefail

echo "Installing system dependencies..."
sudo apt install -y gir1.2-ayatanaappindicator3-0.1

echo "Installing bt-profile-switcher..."
install -Dm755 bt-profile-switcher.py "$HOME/.local/bin/bt-profile-switcher"
install -Dm644 bt-profile-switcher.desktop "$HOME/.config/autostart/bt-profile-switcher.desktop"
install -Dm644 bt-profile-switcher.desktop "$HOME/.local/share/applications/bt-profile-switcher.desktop"
install -Dm644 51-disable-autoswitch.lua "$HOME/.config/wireplumber/bluetooth.lua.d/51-disable-autoswitch.lua"

echo "Restarting WirePlumber..."
systemctl --user restart wireplumber

echo "Done! bt-profile-switcher will start on next login."
echo "Run 'bt-profile-switcher' to start it now."
