# Unlock & Root — VITURE Neckband Pro

Unlock the bootloader and root the VITURE Neckband Pro (`V1231`).

Everything you need is in this repo — the scripts, the patched boot image, and the stock
boot image to go back.

> **Unlocking wipes your device.** Back up first.

---

## The problem this solves

There is no screen on the neckband. The display is in the glasses, and **neither the
bootloader nor the USB-debugging prompt appears on it**.

So when you plug the neckband into a new PC and Android asks **"Allow USB debugging?"**,
you cannot tap Allow. You can't see the dialog. Without that, adb never authorizes and you
can't do anything.

**`viture_unlock.py` solves that**, and it's the main reason to use it.

---

## What you need

**A USB-C cable to your PC.** The neckband's data port is the one the glasses plug into.
Unplug the glasses and connect that port to your computer — so you need a USB-C cable, or
an adapter if your glasses cable isn't detachable. You can't see anything during this
anyway.

**adb and fastboot** (Android platform-tools). On Windows the script finds them on `PATH`
or in the same folder.

**Python 3.**

---

## Part 1 — Getting adb authorized

### 1. Developer options

Settings → About → tap **Build number** seven times.

Then in Settings → System → Developer options turn on:

- **USB debugging**
- **Wireless debugging**
- **OEM unlocking** ← unlocking fails without it

### 2. Connect over wireless first

This is the trick. You can't tap the USB prompt, but you *can* reach the device over
wireless adb — and the script uses that connection to press the button for you.

Developer options → **Wireless debugging** → *Pair device with pairing code*:

```bash
adb pair 192.168.1.50:41234        # pairing IP:PORT + 6-digit code from the screen
adb connect 192.168.1.50:35791     # the OTHER IP:PORT, from the main Wireless debugging page
adb devices                        # should show    192.168.1.50:35791   device
```

> The wireless port **changes on every reboot**. Reconnect after any reboot.

### 3. Run the script

```bash
python3 tools/viture_unlock.py          # Linux / macOS
python  tools\viture_unlock_win.py      # Windows
```

### 4. Plug in USB when it asks

The script waits for the wireless device, then tells you to connect USB.

As soon as you do, Android pops the invisible **"Allow USB debugging?"** dialog. The script
then, over the wireless link:

- dumps the dialog's layout with `uiautomator`
- prints the **RSA fingerprint** so you can confirm it's your PC
- ticks **Always allow from this computer**
- taps **Allow**
- waits for the USB device to flip from `unauthorized` to `device`

That's the authorization done, permanently, without ever seeing the screen.

**Doing it by hand instead**, if you'd rather:

```bash
adb -s <wireless-ip:port> shell uiautomator dump /sdcard/ui.xml
adb -s <wireless-ip:port> shell cat /sdcard/ui.xml     # find the bounds of android:id/button1
adb -s <wireless-ip:port> shell input tap 959 526      # "Always allow" checkbox
adb -s <wireless-ip:port> shell input tap 1398 616     # "Allow"
```

Those coordinates are from a 1920×1080 panel and are what the script computes — but read
your own dump rather than trusting them.

### 5. Confirm the unlock

The script prints the wipe warning and waits for `Y`. This is the point of no return.

It then reboots to the bootloader and runs `fastboot flashing unlock`.

### 6. The blind button press

The only part nobody can automate:

> **Press VOLUME UP once, then press POWER.**

Nothing is selected when the menu opens, so **Power on its own does nothing**. Volume Up
moves onto *UNLOCK THE BOOTLOADER*; Power confirms.

Wrong key is harmless — Volume Down picks *DO NOT UNLOCK*, which just reboots. Try again.

The device wipes and reboots. First boot after a wipe is slow.

```bash
fastboot getvar unlocked
# unlocked: yes
```

---

## Part 2 — Flashing Magisk

After the wipe, set the device up again and re-enable **USB debugging** (and wireless, if
you need the script again).

The patched image is in this repo:

| File | What it is |
|---|---|
| **`magisk_patched_boot.img`** | Magisk v30.7 patched boot — flash this to root |
| **`stock_boot_2.1.3.30702.img`** | Untouched stock boot — flash this to undo root |

Both are built from firmware **`2.1.3.30702`**. **Check your version matches** —
Settings → About. Flashing a boot image from a different build may not boot.

### Test it first, without flashing

```bash
adb reboot bootloader
fastboot boot magisk_patched_boot.img
```

`fastboot boot` loads it into RAM and **does not write the partition**. If something's
wrong, power cycle and you're exactly where you started. Do this before flashing.

### Flash it

```bash
adb reboot bootloader
fastboot flash boot magisk_patched_boot.img
fastboot reboot
```

You do **not** need to touch `vbmeta` — no `--disable-verity`, no `--disable-verification`.
With the bootloader unlocked the device boots a modified image as-is.

### Magisk needs two passes — don't panic in the middle

Install the Magisk APK and open it.

1. It reports **additional setup is required** and asks you to reboot. Do it.
2. After that reboot it asks you to flash **again**, from inside the app:
   **Install → Direct Install**. Do it.
3. Reboot once more. Root works.

The fastboot flash only bootstraps Magisk. The middle state looks like a failure. It isn't.

### Removing root

```bash
fastboot flash boot stock_boot_2.1.3.30702.img
fastboot reboot
```

---

## If something goes wrong

**`fastboot devices` shows nothing.** Linux: udev permissions — try `sudo fastboot devices`.
If that works, add to `/etc/udev/rules.d/51-android.rules`:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666", GROUP="plugdev"
```

then `sudo udevadm control --reload`. Windows: fastboot needs a *different* driver than
adb — install the Google USB driver, or bind WinUSB with Zadig.

**`Flashing Unlock is not allowed`.** OEM unlocking is off. Enable it in Developer options
before rebooting to the bootloader.

**USB stays `unauthorized`.** Your wireless connection dropped, so the script had nothing to
tap with. Reconnect wireless and rerun it.

**Nothing happens after the buttons.** You probably pressed Power first. Volume Up *then*
Power — Power alone is ignored while nothing is selected.

**Won't boot after flashing.** It's A/B — the other slot still has a working image:

```bash
fastboot getvar current-slot
fastboot --set-active=a        # or b, whichever you were NOT on
fastboot reboot
```

**Wireless port changed.** It changes every reboot. Reconnect with the new one.

---

## Going back to stock completely

Full stock firmware:

```
2.1.3.30702_MC942GMS_EQ000_2774.BC07998.E1FE482.AD716D9B55_260702_100_V01_U33_ota.zip
```

| | |
|---|---|
| Size | 2,528,019,882 bytes |
| SHA-1 | `3d3218abccc19c0146c0f225955d5b92786bb991` |

**Mirror:** _(AndroidFileHost link — TBD)_

Standard A/B OTA zip — extract partition images from `payload.bin` with a payload dumper
and flash with fastboot. For root only, `stock_boot_2.1.3.30702.img` above is enough.

---

## Related

- **[viture-pro-kernel](https://github.com/DigijEth/viture-pro-kernel)** — custom kernel with
  KernelSU-Next
- **[docs/bootloader.md](docs/bootloader.md)** — how the unlock menu works internally
- **[docs/recovery.md](docs/recovery.md)** — display and recovery findings

## No warranty

This wipes your device and can leave it unbootable. A/B slots are your safety net —
understand `fastboot --set-active=` before you start.
