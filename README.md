# bt-profile-switcher

A lightweight Linux system tray app to switch Bluetooth headphone profiles between high-fidelity (A2DP/LDAC) and call mode (HSP/HFP) with a single click.

Works with any Bluetooth headphone on PipeWire/WirePlumber (tested with Sony WH-1000XM6).

## Features

- **Two-profile menu**: Hi-Fi (LDAC) for music and Call (mSBC) for microphone, selectable from the system tray
- **Auto-detection**: Finds your Bluetooth headphones automatically, no configuration needed
- **Autoswitch prevention**: Includes a WirePlumber config that stops apps (e.g. Google Meet) from silently downgrading your audio to HSP/HFP
- **Reconnect button**: If profiles get stuck, one click disconnects and reconnects the headphones
- **Single instance**: Launching the app again won't create duplicates
- **Autostart**: Starts automatically on login

## Requirements

- Linux with PipeWire + WirePlumber
- Python 3
- GTK 3, AyatanaAppIndicator3, libnotify

## Install

```bash
git clone https://github.com/lucacavenaghi97/bt-profile-switcher.git
cd bt-profile-switcher
./install.sh
```

This will:
1. Install the system dependency (`gir1.2-ayatanaappindicator3-0.1`)
2. Copy the app to `~/.local/bin/`
3. Set up autostart and app menu entry
4. Install a WirePlumber config to disable automatic profile switching
5. Restart WirePlumber

## Usage

Launch from the app menu or run:

```bash
bt-profile-switcher
```

Right-click the tray icon to:
- Switch between **Hi-Fi (LDAC)** and **Call (mSBC)**
- **Reconnect** the headphones if something goes wrong
- **Quit** the app

## Why?

Bluetooth headphones on Linux default to the HSP/HFP profile (mono, 16kHz, 64kbps) instead of A2DP/LDAC (stereo, 96kHz, 990kbps). Even worse, apps like browsers can silently switch your profile to HSP/HFP when they detect a microphone stream, killing your audio quality. This app gives you manual control over the profile and prevents automatic switching.
