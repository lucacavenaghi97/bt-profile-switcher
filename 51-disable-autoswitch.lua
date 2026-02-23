-- Disable automatic profile switching to HSP/HFP when a Communication
-- stream is detected. This prevents apps like browsers (Google Meet, etc.)
-- from downgrading the Bluetooth codec from A2DP/LDAC to HSP/HFP.
bluez_monitor.rules = {
  {
    matches = {
      {
        { "device.name", "matches", "bluez_card.*" },
      },
    },
    apply_properties = {
      ["bluez5.autoswitch-profile"] = false,
    },
  },
}
