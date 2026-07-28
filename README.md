# Unlock & Root — VITURE Neckband Pro

Unlock the bootloader and root the VITURE Neckband Pro (`V1231`).

There's a script that does most of it. The hard part on this device is that **you can't see
the screen** — there's no display in the neckband, and neither the bootloader nor recovery
puts anything on the glasses. So every prompt has to be handled without looking at it.
That's what the script is for.

> **This wipes your device.** Unlocking the bootloader erases everything. Back up first.

---

## What you need

**A USB-C cable to your PC.** The neckband's data port is the one the glasses plug into.
You'll unplug the glasses and connect that port to your computer — so you need a USB-C
cable, or an adapter if your glasses cable isn't detachable. You won't be able to see
anything on the glasses during this anyway.

**adb and fastboot** on your PC (Android platform-tools). On Windows the script finds them
if they're on `PATH` or sitting in the same folder.

**Python 3.**

**Wireless debugging.** Not optional — see below.

---

## Why wireless debugging is required

When you plug the neckband into a new computer, Android shows an **"Allow USB debugging?"**
dialog. You have to tap Allow. On a normal phone you just do it.

Here, that dialog renders on a screen you cannot see.

The way around it: connect over **wireless** adb first. The script then uses the wireless
connection to read the dialog's layout, find the Allow button, and tap it for you. Once
that's done USB adb is authorized and everything else works.

So the order matters: **wireless first, then plug in USB.**

---

## Step by step

### 1. Turn on Developer options

Settings → About → tap **Build number** seven times.

### 2. Turn on the three toggles

In Settings → System → Developer options, enable:

- **USB debugging**
- **Wireless debugging**
- **OEM unlocking** ← easy to miss, and unlocking fails without it

If **OEM unlocking** is greyed out, connect the device to the internet, wait a few minutes,
and check again.

### 3. Pair wireless debugging

In Developer options → **Wireless debugging** → *Pair device with pairing code*. You'll get
an IP, a port and a 6-digit code. On your PC:

```bash
adb pair 192.168.1.50:41234        # the pairing IP:PORT shown on screen
# enter the 6-digit code

adb connect 192.168.1.50:35791     # the OTHER IP:PORT, from the main Wireless debugging page
```

Confirm it worked:

```bash
adb devices
# 192.168.1.50:35791    device
```

> The wireless port **changes every reboot**. If you reboot, reconnect.

### 4. Run the script

**Linux / macOS**

```bash
python3 tools/viture_unlock.py
```

**Windows**

```
python tools\viture_unlock_win.py
```

or drop it next to `adb.exe` and double-click it.

### 5. Follow it

The script walks the whole thing and prints every command it runs, so you can see what's
happening:

1. **Waits for your wireless connection.**
2. **Tells you to plug in USB.** Do it now.
3. **Handles the "Allow USB debugging?" dialog for you** — ticks *Always allow from this
   computer*, presses Allow, and prints the RSA fingerprint so you can check it's your PC.
4. **Asks you to confirm the unlock.** Press `Y`. This is the point of no return — it wipes
   the device.
5. **Reboots to the bootloader** and runs `fastboot flashing unlock`.
6. **Tells you to press the buttons.**

### 6. The blind button press

This is the only part nobody can automate.

When the script says so:

> **Press VOLUME UP once, then press POWER.**

Nothing is highlighted when the menu opens, so **pressing Power on its own does nothing**.
Volume Up moves the selection onto *UNLOCK THE BOOTLOADER*, and Power confirms it.

Pressed the wrong key? No harm — Volume Down selects *DO NOT UNLOCK*, which just reboots.
Try again.

The device then wipes itself and reboots. First boot after a wipe takes a while.

### 7. Check it worked

```bash
fastboot getvar unlocked
# unlocked: yes
```

---

## Rooting with Magisk

After unlocking, set the device up again and re-enable USB debugging (the wipe cleared it).

Grab a patched boot image from
[Releases](https://github.com/DigijEth/Virtue-NeckbandPro-Root/releases), or patch the
stock one yourself with the Magisk app.

```bash
adb reboot bootloader
fastboot flash boot magisk_patched_boot.img
fastboot reboot
```

**Match your firmware version.** The release image is built from `2.1.3.30702`. Flashing it
over a different build may not boot.

### Magisk needs two passes — don't panic in the middle

Install the Magisk APK and open it.

1. It says **additional setup is required** and asks you to reboot. Do it.
2. After that reboot it asks you to flash **again**, this time from inside the app:
   **Install → Direct Install**. Do it.
3. Reboot once more. Root now works.

The first fastboot flash only bootstraps Magisk. The middle state looks like it failed —
it hasn't. Just follow what the app tells you.

---

## If something goes wrong

**`fastboot devices` shows nothing.** On Linux it's usually udev permissions — try
`sudo fastboot devices`. If that works, add a rule:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666", GROUP="plugdev"
```

to `/etc/udev/rules.d/51-android.rules`, then `sudo udevadm control --reload`.

On Windows it's a driver — fastboot mode needs a *different* driver than adb. Check Device
Manager and install the Google USB driver, or bind WinUSB with Zadig.

**`Flashing Unlock is not allowed`.** OEM unlocking is off. Turn it on in Developer options
before rebooting to the bootloader.

**Nothing happens after the button press.** You may have pressed Power first. Volume Up
*then* Power — Power alone is ignored while nothing is selected.

**Device won't boot after flashing.** It's A/B, so the other slot still has a working
image:

```bash
fastboot getvar current-slot
fastboot --set-active=a        # or b — whichever you were NOT on
fastboot reboot
```

**Testing an image without risk.** `fastboot boot image.img` loads it into RAM without
writing the partition. If it doesn't work, power cycle and you're back to normal. Use this
before flashing anything you built yourself.

**The wireless port changed.** It changes on every reboot. Reconnect with the new one.

---

## Going back to stock

Stock firmware package:

```
2.1.3.30702_MC942GMS_EQ000_2774.BC07998.E1FE482.AD716D9B55_260702_100_V01_U33_ota.zip
```

| | |
|---|---|
| Size | 2,528,019,882 bytes |
| SHA-1 | `3d3218abccc19c0146c0f225955d5b92786bb991` |

**Mirror:** _(AndroidFileHost link — TBD)_

It's a standard A/B OTA zip. Extract the partition images from `payload.bin` with a payload
dumper and flash with fastboot. To remove root only, flash the stock `boot.img`.

---

## Related

- **[viture-pro-kernel](https://github.com/DigijEth/viture-pro-kernel)** — custom kernel
  with KernelSU-Next
- **[docs/bootloader.md](docs/bootloader.md)** — how the unlock menu actually works
- **[docs/recovery.md](docs/recovery.md)** — display and recovery findings

## No warranty

This wipes your device and can leave it unbootable. The A/B slot layout is your safety net.
Understand `fastboot --set-active=` before you start.
