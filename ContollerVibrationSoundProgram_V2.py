# -*- coding: utf-8 -*-
# Version 2 - OpenVR Support
import openvr
import threading, time, sys, keyboard, colorama, sounddevice as sd, numpy as np

colorama.init()
exit_requested = False
RUMBLE_STRENGTH = 20000
VIBRATION_TIME = 0.08
THRESHOLD = 0.0050
current_volume = 0.0
was_over_threshold = False

openvr.init(openvr.VRApplication_Other)
vr_system = openvr.VRSystem()

def get_controller_indices():
    indices = []
    for i in range(openvr.k_unMaxTrackedDeviceCount):
        device_class = vr_system.getTrackedDeviceClass(i)
        if device_class == openvr.TrackedDeviceClass_Controller:
            indices.append(i)
    return indices

def vibrate_controllers(strength, duration_sec):
    pulse_duration = 3999  # Max duration allowed per pulse
    pulse_strength = 3999  # Max strength
    indices = get_controller_indices()

    pulses = int(duration_sec / 0.01)  # 10ms pulse loop
    for _ in range(pulses):
        for i in indices:
            vr_system.triggerHapticPulse(i, 0, pulse_strength)
        time.sleep(0.01)

def keep_controllers_awake():
    while not exit_requested:
        vibrate_controllers(1, 0.01)  # Very light nudge
        time.sleep(60)

def choose_input_device():
    print("\n🎧 Available input devices:")
    devices = sd.query_devices()
    input_devices = [(i, d["name"]) for i, d in enumerate(devices) if d["max_input_channels"] > 0]
    for idx, name in input_devices:
        print(f"  [{idx}] {name}")
    while True:
        try:
            selected = int(input("Select input device by number: "))
            if any(idx == selected for idx, _ in input_devices):
                return selected
        except ValueError:
            continue

def audio_callback(indata, frames, time_info, status):
    global current_volume, was_over_threshold
    volume = np.linalg.norm(indata) / len(indata)
    current_volume = volume
    if volume > THRESHOLD and not was_over_threshold:
        was_over_threshold = True
        strength = min(int(RUMBLE_STRENGTH * (volume - THRESHOLD) * 5), 65535)
        strength = max(strength, 10000)
        vibrate_controllers(strength, VIBRATION_TIME)
    elif volume <= THRESHOLD:
        was_over_threshold = False

def hud_display():
    global current_volume, RUMBLE_STRENGTH, VIBRATION_TIME, THRESHOLD
    while not exit_requested:
        sys.stdout.write("\033[H\033[2J")
        print("🎧 SoundMaxer HUD (OpenVR)")
        print("-" * 40)
        print(f"Volume:     {current_volume:.4f}")
        print(f"Threshold:  {THRESHOLD:.5f}")
        print(f"Strength:   {RUMBLE_STRENGTH}")
        print(f"Time:       {VIBRATION_TIME:.2f}s")
        print("-" * 40)
        print("Z/X/C/Num1–3 = Vibrate")
        print("Num8/5 = Strength | Num9/6 = Time | Num7/4 = Threshold | Q = Quit")
        time.sleep(0.5)

def listen_for_keys():
    keys = ["z", "x", "c", "num 1", "num 2", "num 3"]
    pressed = {k: False for k in keys}
    while not exit_requested:
        for key in keys:
            if keyboard.is_pressed(key):
                if not pressed[key]:
                    vibrate_controllers(RUMBLE_STRENGTH, VIBRATION_TIME)
                    pressed[key] = True
            else:
                pressed[key] = False
        time.sleep(0.01)

def adjust_settings():
    global RUMBLE_STRENGTH, VIBRATION_TIME, THRESHOLD
    last_keys = {}
    def press_once(k):
        if keyboard.is_pressed(k) and not last_keys.get(k, False):
            last_keys[k] = True
            return True
        elif not keyboard.is_pressed(k):
            last_keys[k] = False
        return False

    while not exit_requested:
        if press_once("num 8"): RUMBLE_STRENGTH = min(RUMBLE_STRENGTH + 1000, 65535)
        if press_once("num 5"): RUMBLE_STRENGTH = max(RUMBLE_STRENGTH - 1000, 0)
        if press_once("num 9"): VIBRATION_TIME = min(VIBRATION_TIME + 0.01, 2.0)
        if press_once("num 6"): VIBRATION_TIME = max(VIBRATION_TIME - 0.01, 0.01)
        if press_once("num 7"): THRESHOLD = min(THRESHOLD + 0.0001, 1.0)
        if press_once("num 4"): THRESHOLD = max(THRESHOLD - 0.0001, 0.00001)
        time.sleep(0.05)

def monitor_quit_key():
    global exit_requested
    while not exit_requested:
        if keyboard.is_pressed("q"):
            exit_requested = True
        time.sleep(0.1)

def main():
    global exit_requested
    print("🎧 Starting (OpenVR Mode)")
    device_index = choose_input_device()
    sys.stdout.write("\033[2J\033[H")

    threads = [
        threading.Thread(target=listen_for_keys, daemon=True),
        threading.Thread(target=adjust_settings, daemon=True),
        threading.Thread(target=monitor_quit_key, daemon=True),
        threading.Thread(target=hud_display, daemon=True),
        threading.Thread(target=keep_controllers_awake, daemon=True)
    ]

    for t in threads:
        t.start()

    try:
        with sd.InputStream(callback=audio_callback, device=device_index, channels=1, samplerate=44100):
            while not exit_requested:
                time.sleep(0.1)
    finally:
        vibrate_controllers(0, 0)
        print("\n🛑 Program exited cleanly.")

if __name__ == "__main__":
    main()
