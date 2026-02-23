#!/usr/bin/env python3
"""Bluetooth profile switcher — system tray app for Linux."""

import fcntl
import os
import subprocess
import re
import sys

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, GLib, Notify
from gi.repository import AyatanaAppIndicator3 as AppIndicator


REFRESH_INTERVAL_MS = 5000

# Only show one A2DP (best available) and one HSP/HFP (best available)
PREFERRED_PROFILES = {
    "a2dp-sink": "Hi-Fi (LDAC)",
    "a2dp-sink-sbc_xq": "Hi-Fi (SBC-XQ)",
    "a2dp-sink-sbc": "Hi-Fi (SBC)",
    "headset-head-unit-msbc": "Call (mSBC)",
    "headset-head-unit": "Call (HSP/HFP)",
    "headset-head-unit-cvsd": "Call (CVSD)",
}

def pick_best_profiles(profiles):
    """Pick the best A2DP and best HSP/HFP profile from available ones.

    Returns list of (index, name, label) for at most 2 profiles.
    """
    a2dp_priority = ["a2dp-sink", "a2dp-sink-sbc_xq", "a2dp-sink-sbc"]
    hfp_priority = ["headset-head-unit-msbc", "headset-head-unit", "headset-head-unit-cvsd"]

    by_name = {name: (idx, name) for idx, name, _desc in profiles}
    result = []

    for order in (a2dp_priority, hfp_priority):
        for name in order:
            if name in by_name:
                idx, name = by_name[name]
                result.append((idx, name, PREFERRED_PROFILES[name]))
                break

    return result


def find_bt_device():
    """Find the first Bluetooth audio device in WirePlumber.

    Returns (device_id, device_name) or (None, None) if not found.
    """
    result = subprocess.run(
        ["wpctl", "status"], capture_output=True, text=True
    )
    in_devices = False
    for line in result.stdout.splitlines():
        if "Devices:" in line:
            in_devices = True
            continue
        if in_devices and "[bluez5]" in line:
            match = re.search(r"(\d+)\.\s+(.+?)\s+\[bluez5\]", line)
            if match:
                return int(match.group(1)), match.group(2).strip()
        if in_devices and line.strip().startswith("├") and "Devices" not in line:
            in_devices = False
    return None, None


def get_profiles(device_id):
    """Get available profiles for a device.

    Returns list of (index, name, description) tuples.
    """
    result = subprocess.run(
        ["pw-cli", "enum-params", str(device_id), "EnumProfile"],
        capture_output=True, text=True,
    )
    profiles = []
    for block in re.split(r"(?=Object: size)", result.stdout):
        ints = re.findall(r"Int (\d+)", block)
        strings = re.findall(r'String "([^"]+)"', block)
        strings = [
            s for s in strings
            if s not in ("Audio/Sink", "Audio/Source", "card.profile.devices")
        ]
        if ints and len(strings) >= 2 and strings[0] != "off":
            profiles.append((int(ints[0]), strings[0], strings[1]))
    return profiles


def get_active_profile(device_id):
    """Get the currently active profile name for a device."""
    result = subprocess.run(
        ["pw-cli", "enum-params", str(device_id), "Profile"],
        capture_output=True, text=True,
    )
    strings = re.findall(r'String "([^"]+)"', result.stdout)
    strings = [
        s for s in strings
        if s not in ("Audio/Sink", "Audio/Source", "card.profile.devices")
    ]
    return strings[0] if strings else None


def set_profile(device_id, profile_index):
    """Switch device to a given profile index."""
    subprocess.run(
        ["wpctl", "set-profile", str(device_id), str(profile_index)],
        check=True,
    )


def find_bt_address():
    """Find the MAC address of the connected Bluetooth audio device."""
    result = subprocess.run(
        ["bluetoothctl", "devices", "Connected"], capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        match = re.search(r"Device\s+([0-9A-F:]{17})", line)
        if match:
            return match.group(1)
    return None


def reconnect_device(address):
    """Disconnect and reconnect a Bluetooth device."""
    subprocess.run(["bluetoothctl", "disconnect", address],
                   capture_output=True, timeout=5)
    import time
    time.sleep(2)
    subprocess.run(["bluetoothctl", "connect", address],
                   capture_output=True, timeout=10)


class BtProfileSwitcher:
    def __init__(self):
        Notify.init("bt-profile-switcher")
        self.device_id = None
        self.device_name = None
        self.profiles = []
        self.active_profile = None
        self._updating_menu = False
        self._profile_items = {}

        self.indicator = AppIndicator.Indicator.new(
            "bt-profile-switcher",
            "audio-headphones",
            AppIndicator.IndicatorCategory.HARDWARE,
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)

        self._build_menu()
        GLib.timeout_add(REFRESH_INTERVAL_MS, self._poll)

    def _build_menu(self):
        """Build or rebuild the full menu from scratch."""
        for child in self.menu.get_children():
            self.menu.remove(child)
        self._profile_items.clear()

        self.device_id, self.device_name = find_bt_device()

        if self.device_id is None:
            item = Gtk.MenuItem(label="No Bluetooth headphones connected")
            item.set_sensitive(False)
            self.menu.append(item)
            self.indicator.set_icon_full(
                "audio-headphones-symbolic", "disconnected"
            )
        else:
            all_profiles = get_profiles(self.device_id)
            self.profiles = pick_best_profiles(all_profiles)
            self.active_profile = get_active_profile(self.device_id)

            header = Gtk.MenuItem(label=self.device_name)
            header.set_sensitive(False)
            self.menu.append(header)
            self.menu.append(Gtk.SeparatorMenuItem())

            self._updating_menu = True
            for idx, name, label in self.profiles:
                item = Gtk.CheckMenuItem(label=label)
                item.set_draw_as_radio(True)
                item.set_active(name == self.active_profile)
                item.connect("toggled", self._on_profile_toggled, idx, name, label)
                self.menu.append(item)
                self._profile_items[name] = item
            self._updating_menu = False

            self.indicator.set_icon_full(
                "audio-headphones", self.device_name
            )

        self.menu.append(Gtk.SeparatorMenuItem())

        if self.device_id is not None:
            reconnect_item = Gtk.MenuItem(label="Reconnect")
            reconnect_item.connect("activate", self._on_reconnect)
            self.menu.append(reconnect_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit)
        self.menu.append(quit_item)

        self.menu.show_all()

    def _poll(self):
        """Lightweight poll: only update the active radio, rebuild if device changed."""
        new_id, _ = find_bt_device()

        if new_id != self.device_id:
            self._build_menu()
            return True

        if self.device_id is None:
            return True

        active = get_active_profile(self.device_id)
        if active != self.active_profile:
            self.active_profile = active
            self._updating_menu = True
            for name, item in self._profile_items.items():
                item.set_active(name == active)
            self._updating_menu = False

        return True

    def _on_profile_toggled(self, item, profile_index, profile_name, profile_label):
        if self._updating_menu:
            return
        if not item.get_active():
            return
        if profile_name == self.active_profile:
            return
        set_profile(self.device_id, profile_index)
        self.active_profile = profile_name

        self._updating_menu = True
        for name, menu_item in self._profile_items.items():
            menu_item.set_active(name == profile_name)
        self._updating_menu = False

        Notify.Notification.new(
            "bt-profile-switcher",
            f"Switched to {profile_label}",
            "audio-headphones",
        ).show()

    def _on_reconnect(self, _):
        address = find_bt_address()
        if not address:
            return
        Notify.Notification.new(
            "bt-profile-switcher",
            "Reconnecting...",
            "audio-headphones",
        ).show()

        def do_reconnect():
            reconnect_device(address)
            GLib.timeout_add(3000, self._build_menu)

        import threading
        threading.Thread(target=do_reconnect, daemon=True).start()

    def _on_quit(self, _):
        Notify.uninit()
        Gtk.main_quit()


if __name__ == "__main__":
    lock_path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "bt-profile-switcher.lock")
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit(0)

    BtProfileSwitcher()
    Gtk.main()
