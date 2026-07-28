#!/usr/bin/env python3
"""Guided bootloader unlock for the VITURE Neckband Pro - Windows version.

Flow:
  1. Wait for a wireless adb connection (used to drive the UI).
  2. Wait for the device to appear over USB.
  3. Tick "Always allow from this computer" and accept the USB debugging dialog.
  4. Confirm with the user, then reboot to the bootloader.
  5. Wait for fastboot, then issue `fastboot flashing unlock`.
  6. Tell the user which buttons to press to confirm on the device.

Every adb/fastboot command and its output is echoed.

Differences from the Linux version:
  * Locates adb.exe / fastboot.exe on PATH or in the usual SDK install folders.
  * Strips CR from command output (Windows adb emits CRLF, and adb shell adds
    another CR of its own, which breaks naive line parsing).
  * Fastboot troubleshooting covers drivers rather than udev rules.
"""

import os
import re
import shutil
import subprocess
import sys
import time

DIALOG_ACTIVITY = "UsbDebuggingActivity"
ALWAYS_ALLOW_ID = "android:id/alwaysUse"
ALLOW_BUTTON_ID = "android:id/button1"

# Common platform-tools locations, checked after PATH.
SEARCH_DIRS = [
    r"C:\platform-tools",
    r"C:\adb",
    os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools"),
    os.path.expandvars(r"%ProgramFiles%\platform-tools"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Android\android-sdk\platform-tools"),
    os.path.dirname(os.path.abspath(__file__)),
]


def find_tool(name):
    """Locate adb.exe / fastboot.exe on PATH or in a known SDK folder."""
    exe = name if name.lower().endswith(".exe") else name + ".exe"
    found = shutil.which(exe) or shutil.which(name)
    if found:
        return found
    for d in SEARCH_DIRS:
        if not d:
            continue
        candidate = os.path.join(d, exe)
        if os.path.isfile(candidate):
            return candidate
    return None


ADB = find_tool("adb")
FASTBOOT = find_tool("fastboot")


# --------------------------------------------------------------------------- io


def run(cmd, timeout=60, echo=True):
    """Run a command, echo it and its output, return CompletedProcess."""
    if echo:
        printable = " ".join(os.path.basename(c) if i == 0 else c
                             for i, c in enumerate(cmd))
        print(f"\n> {printable}")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("  !! timed out")
        return subprocess.CompletedProcess(cmd, 124, "", "timeout")
    except FileNotFoundError:
        die(f"could not run {cmd[0]} - is it installed?")
    out = (p.stdout or "").replace("\r", "").rstrip()
    err = (p.stderr or "").replace("\r", "").rstrip()
    if echo:
        for line in out.splitlines():
            print(f"  {line}")
        for line in err.splitlines():
            print(f"  {line}")
        if not out and not err:
            print("  (no output)")
    p.stdout, p.stderr = out, err
    return p


def say(msg):
    print(f"\n=== {msg} ===")


def die(msg, code=1):
    print(f"\nERROR: {msg}")
    input("\nPress Enter to close... ")
    sys.exit(code)


# ------------------------------------------------------------------- adb state


def adb_devices():
    """Return [(serial, state)] from `adb devices`, excluding the header."""
    p = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    text = (p.stdout or "").replace("\r", "")
    out = []
    for line in text.splitlines()[1:]:
        line = line.strip()
        if not line or "\t" not in line:
            continue
        serial, state = line.split("\t", 1)
        out.append((serial.strip(), state.strip()))
    return out


def wireless_devices():
    return [(s, st) for s, st in adb_devices() if ":" in s]


def usb_devices():
    return [(s, st) for s, st in adb_devices() if ":" not in s]


def wait_for(predicate, prompt, timeout=300, interval=2):
    """Poll predicate() until it returns a truthy value."""
    print(f"\n{prompt}")
    print(f"(waiting up to {timeout}s, Ctrl-C to abort)")
    deadline = time.time() + timeout
    while time.time() < deadline:
        got = predicate()
        if got:
            return got
        time.sleep(interval)
    return None


# ------------------------------------------------------- usb debugging dialog


def dialog_showing(serial):
    p = subprocess.run(
        [ADB, "-s", serial, "shell", "dumpsys", "window"],
        capture_output=True, text=True,
    )
    return DIALOG_ACTIVITY in (p.stdout or "")


def center_of(bounds):
    """'[x1,y1][x2,y2]' -> (cx, cy)"""
    nums = [int(n) for n in re.findall(r"-?\d+", bounds)]
    if len(nums) != 4:
        return None
    x1, y1, x2, y2 = nums
    return (x1 + x2) // 2, (y1 + y2) // 2


def find_bounds(xml, resource_id):
    """Bounds of the node carrying resource_id, or None."""
    for node in re.findall(r"<node[^>]*>", xml):
        if f'resource-id="{resource_id}"' in node:
            m = re.search(r'bounds="(\[-?\d+,-?\d+\]\[-?\d+,-?\d+\])"', node)
            if m:
                return m.group(1)
    return None


def accept_usb_dialog(serial):
    """Tick 'always allow' and press Allow on the USB debugging prompt."""
    run([ADB, "-s", serial, "shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    p = run([ADB, "-s", serial, "shell", "cat", "/sdcard/ui.xml"], echo=False)
    xml = p.stdout or ""
    if not xml.strip():
        die("could not read the dialog layout from the device")

    fp = re.search(r"RSA key fingerprint is:&#10;([0-9A-F:]+)", xml)
    if fp:
        print(f"\n  RSA key fingerprint: {fp.group(1)}")

    always = find_bounds(xml, ALWAYS_ALLOW_ID)
    allow = find_bounds(xml, ALLOW_BUTTON_ID)
    if not allow:
        die("could not locate the Allow button in the dialog")

    if always:
        x, y = center_of(always)
        print(f"  ticking 'Always allow from this computer' at ({x},{y})")
        run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
    else:
        print("  (no 'always allow' checkbox found - continuing)")

    x, y = center_of(allow)
    print(f"  pressing Allow at ({x},{y})")
    run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
    time.sleep(2)


# ------------------------------------------------------------------- fastboot


def fastboot_serials():
    try:
        p = subprocess.run([FASTBOOT, "devices"], capture_output=True, text=True)
    except FileNotFoundError:
        return []
    text = (p.stdout or "").replace("\r", "")
    serials = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "\t" in line:
            serials.append(line.split("\t", 1)[0].strip())
        elif " " in line:
            serials.append(line.split()[0].strip())
    return serials


# ----------------------------------------------------------------------- main


def main():
    say("VITURE Neckband Pro - bootloader unlock (Windows)")

    if not ADB:
        die("adb.exe not found. Install Android platform-tools and either add\n"
            "  it to PATH or drop this script next to adb.exe.")
    if not FASTBOOT:
        die("fastboot.exe not found. Install Android platform-tools and either\n"
            "  add it to PATH or drop this script next to fastboot.exe.")
    print(f"\n  adb:      {ADB}")
    print(f"  fastboot: {FASTBOOT}")

    print("\nStep 1: connect the neckband over WIRELESS adb.")
    print("  On the device: Developer options > Wireless debugging > pair,")
    print("  then in this console: adb connect <ip>:<port>")

    wl = wait_for(
        lambda: [s for s, st in wireless_devices() if st == "device"],
        "Waiting for a wireless adb device...",
    )
    if not wl:
        die("no wireless adb device appeared")
    wireless = wl[0]
    print(f"\n  wireless device: {wireless}")

    say("Step 2: enable USB debugging and plug the glasses into USB")

    usb = wait_for(
        lambda: usb_devices(),
        "Waiting for the device to appear over USB...",
    )
    if not usb:
        die("no USB device appeared.\n"
            "  On Windows this is usually a driver problem - check Device Manager\n"
            "  for a device with a warning icon and install the Google USB driver.")
    usb_serial, usb_state = usb[0]
    print(f"\n  USB device: {usb_serial} ({usb_state})")

    if usb_state != "device":
        say("Step 3: accepting the USB debugging dialog")
        got = wait_for(
            lambda: dialog_showing(wireless),
            "Waiting for the 'Allow USB debugging?' dialog...",
            timeout=120,
        )
        if not got:
            die("the USB debugging dialog never appeared")
        accept_usb_dialog(wireless)

        ok = wait_for(
            lambda: [s for s, st in usb_devices() if st == "device"],
            "Waiting for USB authorisation to take effect...",
            timeout=60,
        )
        if not ok:
            die("USB device is still not authorised")
        usb_serial = ok[0]
        print(f"\n  USB authorised: {usb_serial}")
    else:
        print("\n  USB already authorised - skipping the dialog")

    run([ADB, "devices", "-l"])

    say("Step 4: unlock confirmation")
    print("\nUnlocking the bootloader will wipe the device and may make your")
    print("device less secure.")
    try:
        answer = input("Unlock bootloader? Press Y to continue, N to exit: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"
    if answer != "y":
        print("\nAborted - nothing was changed.")
        input("\nPress Enter to close... ")
        return 0

    say(f"Step 5: rebooting {usb_serial} into the bootloader")
    run([ADB, "-s", usb_serial, "reboot", "bootloader"])

    print("\nWaiting 10 seconds for the bootloader...")
    time.sleep(10)

    say("Step 6: checking for the device in fastboot")
    run([FASTBOOT, "devices"])
    serials = fastboot_serials()

    if not serials:
        print("\n  Nothing listed. Retrying for another 20s...")
        for _ in range(10):
            time.sleep(2)
            serials = fastboot_serials()
            if serials:
                run([FASTBOOT, "devices"])
                break

    if not serials:
        die(
            "no fastboot device found.\n"
            "  In fastboot mode Windows needs a separate driver from the adb one.\n"
            "  Open Device Manager and look for 'Android' or an unknown device:\n"
            "    - Install the Google USB driver (android_winusb.inf), or\n"
            "    - Use Zadig to bind the WinUSB driver to the fastboot interface.\n"
            "  If nothing new appears in Device Manager at all, the device did\n"
            "  not enter fastboot."
        )

    print(f"\n  fastboot device: {serials[0]}")

    say("Step 7: unlocking")
    run([FASTBOOT, "flashing", "unlock"], timeout=120)

    say("ACTION REQUIRED ON THE DEVICE")
    print("\n  Press VOLUME UP once, then press POWER.")
    print("\n  (The menu opens with nothing selected, so Power alone does")
    print("   nothing. Volume Up selects 'UNLOCK THE BOOTLOADER'.)")

    input("\nPress Enter once you have done that... ")

    say("Bootloader unlocked!")
    print("\nThe device wipes userdata and reboots into recovery to do it.")
    print("Verify afterwards with: fastboot getvar unlocked")

    magisk_root_steps()
    input("\nPress Enter to close... ")
    return 0


def magisk_root_steps():
    """Post-unlock rooting flow. Magisk needs TWO passes on this device."""
    say("Step 8: root with Magisk (optional)")
    print("\nOnce the device has finished wiping and booted back into Android:")
    print("\n  1. adb reboot bootloader")
    print("  2. fastboot flash boot magisk_patched_boot.img")
    print("  3. fastboot reboot")
    print("\n  4. Install the Magisk APK and open it.")
    print("\n  IMPORTANT - Magisk needs a second pass on this device:")
    print("     * On first open Magisk reports additional setup is required")
    print("       and asks you to reboot. Do it.")
    print("     * After that reboot, Magisk asks you to flash again, this time")
    print("       from inside the app (Install > Direct Install). Do it.")
    print("     * Reboot once more. Root is then fully working.")
    print("\n  Follow whatever the Magisk app prints on screen - the first")
    print("  fastboot flash only bootstraps it, it is not the finished state.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
