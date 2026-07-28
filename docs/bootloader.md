# Bootloader unlock

The neckband's display lives in the glasses and does not come up in the bootloader, so the
unlock confirmation has to be done blind. This documents exactly what the menu does, from
disassembly of `abl_dxe.bin` (extracted from the `abl` partition image).

**Short version: run `fastboot flashing unlock`, press Volume Up once, then Power.**

## Getting into fastboot

No key combo is needed. ABL parses the reboot reason, so:

```
adb reboot bootloader
```

is enough. Reset reason `2` (`FASTBOOT_MODE`) sets `BootIntoFastboot`.

Note this ABL has **no `bootonce-bootloader` BCB handler** — that string does not exist in
the binary. It does honour `boot-recovery` and `boot-fastboot` written to `misc`, so
`adb reboot fastboot` lands you in fastbootd instead.

Key presses checked at boot (via `EFI_SIMPLE_TEXT_INPUT_EX`, before any menu):

| Scan code | Effect |
|---|---|
| `SCAN_HOME` (5) | Boot into recovery |
| `SCAN_ESC` (0x17) | `RebootDevice(0xff)` → **EDL / 9008** |
| `SCAN_DELETE` (8) | Recovery + factory mode (`androidboot.mode=factory`) |

No key at boot sets `BootIntoFastboot`.

Fastboot itself works fine with no display — the USB command loop runs regardless of
whether the menu draws.

## Prerequisite: OEM unlocking

`flashing unlock` is refused outright unless the allow-unlock flag is set:

```
"Flashing Unlock is not allowed"
```

The flag is **bit 0 of the last byte of the last block of the `frp` partition** — exactly
what Android's "OEM unlocking" toggle in Developer options writes. ABL reads it into
`DevInfo->IsAllowUnlock` and checks it before any menu logic. Exposed over fastboot as
`fastboot oem get_unlock_ability`.

Enable OEM unlocking **before** rebooting to the bootloader.

## The unlock menu

Two code paths could have skipped the menu entirely. Both are dead on this build:

- The `AVB_LE` bypass tests `cmp w0, #3` against `GetAVBVersion()`, which is a constant
  `mov w0, #2; ret`.
- `IsDisplayMenuEnabled()` is a constant `mov w0, #1; ret` — hardcoded **TRUE**, so the
  `"Display menu is not enabled!"` fallback (which would call `SetDeviceUnlockValue`
  directly with no button press) is unreachable.

There is one remaining runtime check — if `DisplayUtilsGetProperty` returns `EFI_NOT_FOUND`
ABL unlocks immediately with no menu. It fails *open*, so assume the menu appears. If
`flashing unlock` returns `OKAY` instantly instead of hanging, you got the no-menu path.

### Layout

The unlock page is a 10-row table; only rows with `Attribute == 3` are selectable:

| Selection index | Text | Action |
|---|---|---|
| 0 | `DO NOT UNLOCK THE BOOTLOADER` | 1 — normal reboot, no change |
| 1 | `UNLOCK THE BOOTLOADER` | 2 — unlock, then reboot to recovery |

### Key behaviour

`OptionIndex` is initialised to **2**, which is out of range for two options. The Power
handler returns without acting when the index is out of range, so:

- **Power alone does nothing** until a volume key has been pressed.
- **Volume Up** decrements with wrap: from the initial 2 it lands on **index 1 —
  `UNLOCK THE BOOTLOADER`**.
- **Volume Down** increments with wrap: from 2 it lands on index 0, `DO NOT UNLOCK`.
- Further presses toggle between 0 and 1.
- **Power confirms.**
- `TimeoutTime` is 0 — the menu waits forever, it never auto-dismisses.

Keys are polled by a 50 ms periodic timer with a 250 ms hold/debounce filter.

Picking the wrong option is harmless: "DO NOT UNLOCK" just reboots normally, so you can
retry with the other volume key.

### What unlocking does

Confirming writes `is_unlocked` in DeviceInfo (magic `ANDROID-BOOT!`) **and** writes a BCB
of `recovery\n--wipe_data\n--reason=MasterClearConfirm` to `misc`, then reboots to
recovery. **Userdata is wiped.**

## AVB after unlocking

You do not need to disable verity or verification in `vbmeta`. ABL contains:

```
State: Unlocked, AvbSlotVerify returned %a, continue boot
```

Unlocked devices tolerate AVB failures and continue booting, so a Magisk-patched boot image
runs without touching `vbmeta`.

## EDL

The device enters EDL (`05c6:9008`) via `SCAN_ESC` at boot, or `RebootDevice(0xff)`.

Sahara comes up in mode 0 (`IMAGE_TX_PENDING`) waiting for a programmer. Switching to
command mode (HELLO_RESP with mode 3) allows reading identity without one:

- `SERIAL_NUM_READ`
- `MSM_HW_ID_READ`
- `OEM_PK_HASH_READ` → a real 48-byte SHA-384 OEM key hash, **not** the Qualcomm test key

Because secure boot is enforced, Sahara will only accept a `prog_firehose_ddr.elf` signed
by the matching key. Without VITURE's signed programmer, **EDL can read identity but cannot
read or write a single partition.** It is not a route around the bootloader.

A Sahara `RESET` (cmd `0x07`) cleanly reboots the device out of EDL.
