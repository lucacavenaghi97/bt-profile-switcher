# bt-profile-switcher

A lightweight Linux system tray app to switch Bluetooth headphone profiles between high-fidelity (A2DP/LDAC) and call mode (HSP/HFP) with a single click.

Works with any Bluetooth headphone on PipeWire/WirePlumber (tested with Sony WH-1000XM6).

## Requirements

- Linux with PipeWire + WirePlumber
- Python 3
- GTK 3, AyatanaAppIndicator3, libnotify

## Install

```bash
./install.sh
```

## Usage

Launch from app menu or run:

```bash
bt-profile-switcher
```

Right-click the tray icon to switch profiles.
