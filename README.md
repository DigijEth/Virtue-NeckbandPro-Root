# VITURE Neckband Pro — reverse engineering notes and tools

Research notes and tooling for the VITURE Neckband Pro (`V1231`, device `Neckband_Pro`,
Android 13 / SDK 33, Snapdragon `lahaina`).

Everything here was derived from a retail device and its own OTA package. No vendor
binaries, firmware images or APKs are committed — see [`.gitignore`](.gitignore).

## Contents

| Doc | Covers |
|---|---|
| [docs/bootloader.md](docs/bootloader.md) | ABL unlock flow, the blind volume/power menu, EDL state |
| [docs/recovery.md](docs/recovery.md) | Why stock recovery has no display, and what a custom recovery needs |

| Tool | Purpose |
|---|---|
| [tools/viture_unlock.py](tools/viture_unlock.py) | Guided bootloader unlock (Linux) |
| [tools/viture_unlock_win.py](tools/viture_unlock_win.py) | Guided bootloader unlock (Windows) |

## Device summary

| | |
|---|---|
| Model | `V1231` (VITURE Neckband Pro) |
| Device | `Neckband_Pro`, internal codename **Eden** |
| Android | 13, SDK 33, `ro.product.first_api_level=33` |
| SoC | Qualcomm `lahaina` |
| Kernel | GKI — Qualcomm display driver is a **vendor module**, not built in |
| Partitions | A/B, `ab_ota_partitions = product,system,system_ext,vbmeta_system` |
| Boot image | header **v3** — ramdisk lives in `boot`, there is no `init_boot` |
| Display | 1920×1080 @ 120 Hz, presented as an internal panel (it is in the glasses) |

## Quick facts

- **Unlocking is blind.** The bootloader unlock menu is drawn to a display that does not
  come up, so the confirmation has to be done by feel: **Volume Up once, then Power.**
- **Stock recovery has no display at all** — not a DP alt-mode limitation, it simply has
  no display driver in its ramdisk.

## Ordering of operations

1. Enable OEM unlocking in Developer options (writes the `frp` flag ABL checks).
2. `tools/viture_unlock.py` — unlock the bootloader (wipes userdata).
3. Patch the stock `boot.img` with Magisk, flash it, then follow the Magisk app's
   on-screen prompts — it needs **two** passes (see below).
4. With root, dump `vendor_boot` / `vendor_dlkm` / `dtbo`, which the OTA does not ship.

### Magisk needs two passes

Flashing the patched `boot.img` from fastboot only bootstraps Magisk. On first launch the
app reports that additional setup is required and asks for a reboot; after that reboot it
asks you to flash *again*, this time via **Install → Direct Install**. Reboot once more and
root is complete. The intermediate state looks like a failure but is not.

### AVB / vbmeta

You do **not** need `--disable-verity --disable-verification`. ABL contains the string

```
State: Unlocked, AvbSlotVerify returned %a, continue boot
```

so with the bootloader unlocked it tolerates AVB failures and boots a modified image.
Patch with `KEEPVERITY=true` and leave `vbmeta` alone.

## Returning to stock

Stock firmware package:

```
2.1.3.30702_MC942GMS_EQ000_2774.BC07998.E1FE482.AD716D9B55_260702_100_V01_U33_ota.zip
```

| | |
|---|---|
| Version | `2.1.3.30702` |
| Size | 2,528,019,882 bytes |
| SHA-1 | `3d3218abccc19c0146c0f225955d5b92786bb991` |

**Mirror:** _(AndroidFileHost link — TBD)_

A standard A/B OTA zip containing `payload.bin`. Extract partition images with a payload
dumper and flash with fastboot. To undo root only, flash the stock `boot.img`:

```
fastboot flash boot boot.img
fastboot reboot
```

## Status

- [x] Bootloader unlock (ABL menu behaviour fully mapped)
- [x] Root via Magisk
- [ ] Custom recovery with working display output
