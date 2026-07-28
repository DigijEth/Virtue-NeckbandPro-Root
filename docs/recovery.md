# Recovery and display output

## Stock recovery is blind

Not because it lacks DisplayPort alt-mode support specifically — because it has **no
display driver at all**.

Evidence:

- The device is recovery-as-boot. `boot.img`'s ramdisk contains `system/bin/recovery`,
  `system/etc/recovery.fstab`, `librecovery_ui.so`, `init.recovery.qcom.rc`.
- That ramdisk contains **zero `.ko` files**.
- `CONFIG_DRM_MSM` is **absent** from the kernel config. This is a GKI kernel; the
  Qualcomm display stack is a vendor module (`msm_drm.ko`), loaded from the vendor
  partitions at runtime.

No `msm_drm.ko` in the recovery ramdisk means no DRM device, which means `minui` has
nothing to open. Recovery renders to nothing.

## What is already in the kernel

The USB-C side is built in, so PD/alt-mode negotiation is not the missing piece:

```
CONFIG_TYPEC=y
CONFIG_TYPEC_TCPM=y
CONFIG_TYPEC_UCSI=y
CONFIG_UCSI_QTI_GLINK=y
CONFIG_QTI_PMIC_GLINK=y
```

DRM core and helpers are present (`CONFIG_DRM=y`, `CONFIG_DRM_KMS_HELPER=y`,
`CONFIG_DRM_MIPI_DSI=y`, `CONFIG_DRM_PANEL=y`, `CONFIG_DRM_BRIDGE=y`). What is missing is
the Qualcomm driver itself.

## Boot image layout

`boot.img` is header **version 3**:

| Field | Value |
|---|---|
| header_version | 3 |
| kernel_size | 42,387,968 (40.4 MiB), ARM64 `MZ` image |
| ramdisk_size | 8,987,250 (8.6 MiB), gzip |
| page_size | 4096 |
| cmdline | *(empty)* |

Header v3 means the ramdisk lives in `boot` and there is **no `init_boot`** — relevant
both for recovery work and for Magisk, which patches `boot` directly here.

## What a custom recovery needs

1. **`msm_drm.ko` and its full dependency chain**, plus any firmware blobs it loads,
   present in the recovery ramdisk.
2. **Module loading early in recovery init**, before `minui` initialises.
3. The DP connector brought up as a DRM connector so `minui` finds a usable device.

## Blocker: the vendor partitions

The OTA only ships `product`, `system`, `system_ext`, `vbmeta_system`. The display modules
live in `vendor_boot` (vendor_ramdisk) and `vendor_dlkm`, neither of which is in the OTA.

They are readable once the device is rooted — `dd` from `/dev/block/by-name/`. This is the
prerequisite for any recovery with working output:

```
vendor_boot
vendor_dlkm
dtbo
```

EDL is not an alternative for obtaining them (see [bootloader.md](bootloader.md) — secure
boot is enforced and the signed programmer is not available).

## Status

Unfinished. The module set has not yet been dumped, and no custom recovery has been built.
