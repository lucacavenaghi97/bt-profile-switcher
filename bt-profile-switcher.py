#!/usr/bin/env python3
"""Bluetooth profile switcher — system tray app for Linux."""

import subprocess
import re

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, GLib, Notify
from gi.repository import AyatanaAppIndicator3 as AppIndicator


REFRESH_INTERVAL_MS = 5000


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


class BtProfileSwitcher:
    def __init__(self):
        Notify.init("bt-profile-switcher")
        self.device_id = None
        self.device_name = None
        self.profiles = []
        self.active_profile = None

        self.indicator = AppIndicator.Indicator.new(
            "bt-profile-switcher",
            "audio-headphones",
            AppIndicator.IndicatorCategory.HARDWARE,
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)

        self.refresh()
        GLib.timeout_add(REFRESH_INTERVAL_MS, self.refresh)

    def refresh(self):
        """Poll device state and rebuild menu."""
        self.device_id, self.device_name = find_bt_device()

        for child in self.menu.get_children():
            self.menu.remove(child)

        if self.device_id is None:
            item = Gtk.MenuItem(label="No Bluetooth headphones connected")
            item.set_sensitive(False)
            self.menu.append(item)
            self.indicator.set_icon_full(
                "audio-headphones-symbolic", "disconnected"
            )
        else:
            self.profiles = get_profiles(self.device_id)
            self.active_profile = get_active_profile(self.device_id)

            header = Gtk.MenuItem(label=self.device_name)
            header.set_sensitive(False)
            self.menu.append(header)
            self.menu.append(Gtk.SeparatorMenuItem())

            for idx, name, desc in self.profiles:
                item = Gtk.CheckMenuItem(label=desc)
                item.set_draw_as_radio(True)
                is_active = name == self.active_profile
                item.set_active(is_active)
                item.connect("toggled", self.on_profile_toggled, idx, name, desc)
                self.menu.append(item)

            self.indicator.set_icon_full(
                "audio-headphones", self.device_name
            )

        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.on_quit)
        self.menu.append(quit_item)

        self.menu.show_all()
        return True

    def on_profile_toggled(self, item, profile_index, profile_name, profile_desc):
        if not item.get_active():
            return
        if profile_name == self.active_profile:
            return
        set_profile(self.device_id, profile_index)
        self.active_profile = profile_name
        Notify.Notification.new(
            "bt-profile-switcher",
            f"Switched to {profile_desc}",
            "audio-headphones",
        ).show()
        self.refresh()

    def on_quit(self, _):
        Notify.uninit()
        Gtk.main_quit()


if __name__ == "__main__":
    BtProfileSwitcher()
    Gtk.main()
