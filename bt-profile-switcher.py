#!/usr/bin/env python3
"""Bluetooth profile switcher — system tray app for Linux."""

import subprocess
import re


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


if __name__ == "__main__":
    dev_id, dev_name = find_bt_device()
    print(f"Device: {dev_name} (id={dev_id})")
    if dev_id:
        profiles = get_profiles(dev_id)
        for idx, name, desc in profiles:
            print(f"  [{idx}] {name}: {desc}")
        active = get_active_profile(dev_id)
        print(f"Active: {active}")
