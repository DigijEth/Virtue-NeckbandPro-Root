# Unlock & Root — VITURE Neckband Pro (V1231)

**Unlocking wipes your device.**

## You need

- USB-C cable — the glasses port is the data port, so unplug the glasses
- adb + fastboot
- Python 3

## Unlock

**1.** Developer options → turn on **USB debugging**, **Wireless debugging**, **OEM unlocking**

**2.** Connect wireless adb:

```bash
adb pair 192.168.1.50:41234      # pairing IP:PORT + code from the device
adb connect 192.168.1.50:35791   # the other IP:PORT
```

**3.** Run it:

```bash
python3 tools/viture_unlock.py          # Linux / macOS
python  tools\viture_unlock_win.py      # Windows
```

**4.** Plug in USB when it asks. You can't see the "Allow USB debugging?" dialog — the
script taps it for you over wireless. That's what wireless is for.

**5.** Press `Y` to confirm.

**6.** When it tells you to, press **Volume Up once, then Power**.

Power on its own does nothing — nothing is selected until you press Volume Up.
Wrong key just reboots, so try again.

Device wipes and reboots.

```bash
fastboot getvar unlocked      # unlocked: yes
```

## Root

Images in this repo are for firmware **2.1.3.30702**. Check yours matches.

```bash
adb reboot bootloader
fastboot boot magisk_patched_boot.img     # test in RAM, nothing written
fastboot flash boot magisk_patched_boot.img
fastboot reboot
```

Install the Magisk APK and open it. **It needs two passes:**

1. It asks you to reboot → do it
2. It asks you to flash again → **Install → Direct Install** → reboot

Looks like it failed in the middle. It didn't.

## Undo root

```bash
fastboot flash boot stock_boot_2.1.3.30702.img
```

## Problems

| | |
|---|---|
| `fastboot devices` empty | Linux: `sudo fastboot devices`, then add a udev rule. Windows: install the Google USB driver |
| `Flashing Unlock is not allowed` | OEM unlocking is off |
| USB stays `unauthorized` | Wireless dropped — reconnect and rerun |
| Buttons did nothing | Volume Up **then** Power |
| Won't boot | `fastboot --set-active=` the other slot |
| Wireless stopped working | The port changes every reboot |

## Files

| | |
|---|---|
| `magisk_patched_boot.img` | Magisk v30.7, rooted |
| `stock_boot_2.1.3.30702.img` | stock, removes root |
| `tools/viture_unlock*.py` | the unlock script |
| `docs/` | how it all works, if you care |

---

[viture-pro-kernel](https://github.com/DigijEth/viture-pro-kernel) — custom kernel with KernelSU-Next

No warranty. This can leave your device unbootable.
