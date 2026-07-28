# Unlock & Root — VITURE Neckband Pro (V1231)

**Unlocking wipes your device. I am also not responsible for any damage or broken
devices. This guide and its tool are provided as-is, without warranty.**

## You need

- **USB-C magnet adapter for the glasses** — the built-in glasses cable is the USB you
  need to use
- adb + fastboot
- Python 3

## Unlock

### 1. Developer options

Settings → About → tap **Build number** 7 times.

Then Settings → System → Developer options → turn on:

- **USB debugging**
- **Wireless debugging**
- **OEM unlocking** — unlocking fails without this

### 2. Connect over wireless

Developer options → **Wireless debugging** → *Pair device with pairing code*. It shows a
pairing IP:PORT and a 6-digit code. The main Wireless debugging page shows a **different**
IP:PORT — you need both.

```bash
adb pair 192.168.1.50:41234      # pairing IP:PORT, then type the 6-digit code
adb connect 192.168.1.50:35791   # the IP:PORT from the main page
adb devices                      # must show the device before continuing
```

The port changes every reboot.

### 3. Start the script

```bash
python3 tools/viture_unlock.py          # Linux / macOS
python  tools\viture_unlock_win.py      # Windows
```

It finds your wireless device, then prints:

```
Waiting for the device to appear over USB...
```

### 4. Plug in the USB cable

The neckband pops an **"Allow USB debugging?"** dialog you cannot see, because there's no
screen. The script handles it over the wireless connection — it prints the RSA fingerprint
so you can check it's your PC, ticks *Always allow*, and taps Allow:

```
dialog detected
RSA key fingerprint: 07:A7:26:1E:...
tap alwaysUse (959,526)
tap Allow (1398,616)
USB authorised: P8A1BM55301575
```

If it sits waiting instead, your wireless connection dropped — reconnect and rerun.

### 5. Confirm

```
Unlocking the bootloader will wipe the device...
Unlock bootloader? Press Y to continue, N to exit:
```

Press **Y**. Everything on the device is erased from here.

The script reboots to the bootloader and runs `fastboot flashing unlock`.

### 6. Press the buttons on the neckband

The script stops and prints:

```
ACTION REQUIRED ON THE DEVICE
  Press VOLUME UP once, then press POWER.
```

Do exactly that, on the neckband itself.

There's an unlock menu on screen but you can't see it. **Nothing is selected when it opens,
so pressing Power first does nothing at all.** Volume Up moves the selection onto *UNLOCK
THE BOOTLOADER*. Power then confirms it.

Press Volume Down by mistake and it selects *DO NOT UNLOCK* — the device just reboots,
nothing is harmed, run the script again.

### 7. Wait

The device wipes itself and reboots. First boot after a wipe takes several minutes.

```bash
fastboot getvar unlocked      # unlocked: yes
```

## Root

The images here are built from firmware **2.1.3.30702** — check yours matches in
Settings → About before flashing.

Set the device up again and re-enable **USB debugging** (the wipe cleared it).

```bash
adb reboot bootloader

fastboot boot magisk_patched_boot.img        # test only - loads to RAM, writes nothing
```

If that boots fine, flash it:

```bash
fastboot flash boot magisk_patched_boot.img
fastboot reboot
```

Install the Magisk APK and open it. **It needs two passes:**

1. It says additional setup is required and asks you to reboot → reboot
2. It asks you to flash again → **Install → Direct Install** → reboot again

After step 1 it looks like it failed. It hasn't. Just do what the app says.

## Undo root

```bash
fastboot flash boot stock_boot_2.1.3.30702.img
```

## Problems

| | |
|---|---|
| `fastboot devices` empty | Linux: try `sudo fastboot devices`, then add a udev rule. Windows: fastboot needs a different driver than adb — install the Google USB driver |
| `Flashing Unlock is not allowed` | OEM unlocking is off in Developer options |
| USB stays `unauthorized` | Wireless dropped, so the script couldn't tap Allow — reconnect and rerun |
| Buttons did nothing | Volume Up **then** Power. Power alone is ignored |
| Won't boot after flashing | `fastboot getvar current-slot`, then `fastboot --set-active=` the other one |
| Wireless stopped working | The port changes on every reboot |

## Files

| | |
|---|---|
| `magisk_patched_boot.img` | Magisk v30.7 — flash to root |
| `stock_boot_2.1.3.30702.img` | stock — flash to remove root |
| `tools/viture_unlock.py` | unlock script, Linux/macOS |
| `tools/viture_unlock_win.py` | unlock script, Windows |
| `docs/` | how it works internally |

---

[viture-pro-kernel](https://github.com/DigijEth/viture-pro-kernel) — custom kernel with KernelSU-Next

I am not responsible for any damage or broken devices. This guide and its tool are provided
as-is, without warranty.
