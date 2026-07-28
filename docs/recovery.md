# Recovery and display output

Everything here is measured on hardware. Where an earlier conclusion was wrong, the
correction and the evidence that overturned it are both kept.

## The display is DisplayPort alt mode over USB-C

Proven by attaching and detaching the glasses and sampling every DRM connector:

| Connector | Glasses **attached** | Glasses **detached** |
|---|---|---|
| **`card0-DP-1`** | **`connected`**, mode `1920x1080` | **`disconnected`**, no mode |
| `card0-DSI-1` | `connected`, `1920x1080x120x150221vid` | *identical* |
| `card0-Virtual-1` | `connected`, `4096x2160` | *identical* |

Only `DP-1` tracks the glasses. `DSI-1` and `Virtual-1` are unchanged in both states.

Corroborated by the boot log:

```
[ 7.18] [drm:dp_panel_read_sink_caps][msm-dp-info] fec_en=0, dsc_en=0, widebus_en=0
[ 8.59] [drm:dp_panel_resolution_info][msm-dp-info]
        DP RESOLUTION: 1920(43|32|5|0)x1200(36|9|5|0)@90fps 24bpp 225000Khz 10LR 4Ln
```

That is the DP controller enumerating a real sink — 4 lanes, 24 bpp.

### `DSI-1` is a phantom — do not be fooled by it

`card0-DSI-1` reports `connected` with a plausible-looking `1920x1080@120` mode **whether
or not anything is plugged in**. Android compounds this by labelling the primary display
"Built-in Screen", which is just the framework's default name.

The device tree explains it: this is largely Qualcomm's stock IDP reference tree and it
carries a menu of candidate panels that were never fitted —

```
"nt36672e fhd plus 144Hz video panel"
"r66451 amoled cmd mode dsi visionox panel with DSC"
"ILI9881P 720p video signal panel"
"Simulator video mode dsi panel"
"ext video mode dsi bridge"
```

Board compatible is `qcom,yupikp-iot-idp`. There is no VITURE-specific panel node, and no
third-party bridge silicon (no ANX / LT / PS parts). Nothing on the kernel command line
selects a display either, and the vendor_boot cmdline carries
`video=vfb:640x400,bpp=32,memsize=3072000` — a *virtual* framebuffer.

**Reading connector names alone will lead you to the wrong output.** Only the
attach/detach test settles it.

## Correction: recovery *does* have the display driver

An earlier version of this document claimed stock recovery has no display driver at all.
That was wrong.

`msm_drm.ko` ships in the **vendor_boot** ramdisk, and it is the sole entry in the
top-level `lib/modules/modules.load`, so first-stage init loads it — and first-stage init
runs in recovery too.

Extracted from `vendor_boot_a` (header v3, vendor_ramdisk 1.7 MiB, dtb 9.4 MiB):

```
lib/modules/msm_drm.ko            <- the only entry in modules.load
lib/modules/5.4-gki/              <- 45 first-stage modules, loaded separately
    gcc-yupik.ko  pinctrl-yupik.ko  qnoc-yupik.ko
    phy-qcom-ufs-qmp-v4-yupik.ko  ufs-qcom.ko  sdhci-msm.ko
    rpmh-regulator.ko  qcom-arm-smmu-mod.ko  ...
```

What misled the earlier analysis: the **boot.img** ramdisk (which *is* the recovery, this
being a recovery-as-boot device) contains zero `.ko` files, and `CONFIG_DRM_MSM` is absent
from the kernel config. Both true, and both irrelevant — the modules come from vendor_boot,
not from the recovery ramdisk.

## So why is recovery blind?

Not a missing driver. The DP alt-mode chain is never brought up.

Lighting a DP alt-mode display is not just a display driver. In order:

1. USB-C **PD contract** negotiated with the sink
2. **Alt-mode entry** (DisplayPort mode) agreed
3. **Lane configuration** — here 4 lanes, via the `usb-ssphy-qmp-dp-combo` PHY
4. Only then does the DP controller have a link, and `minui` a connector with a mode

The kernel side is all present and built in, so it exists in recovery:

```
CONFIG_TYPEC=y            CONFIG_TYPEC_TCPM=y
CONFIG_TYPEC_UCSI=y       CONFIG_UCSI_QTI_GLINK=y
CONFIG_QTI_PMIC_GLINK=y
```

Device tree has the matching pieces: `qcom,usb-ssphy-qmp-dp-combo`, `qcom,qpnp-pdphy`,
`qcom,dp-display`, `qcom,edp-display`.

But on Qualcomm platforms the negotiation is *driven from userspace* through the
PMIC-glink / UCSI path. Recovery's minimal init does not run that, so steps 1–3 never
complete, `DP-1` stays `disconnected`, and `minui` has nothing to draw on.

**This is the actual problem a custom recovery has to solve on this device.** It is harder
than a DSI panel would have been — a DSI panel is described in the DTB and comes up with no
negotiation at all.

## Debugging recovery is itself blocked

Recovery runs `adbd`, but it comes up **`unauthorized`**, and the "Allow USB debugging"
prompt renders on the display we cannot see.

Options, none yet tested:

- Pre-authorize by placing the host's public key where recovery's `adbd` reads it
  (`/data/misc/adb/adb_keys`, if recovery mounts `/data`)
- Bake `/adb_keys` into the recovery ramdisk and flash it — small and reversible, and
  needed anyway when building a custom recovery
- Serial console: the vendor_boot cmdline has `console=ttyMSM0,115200n8`

Without one of these there is no way to inspect DRM state inside recovery.

## Boot image facts

| | |
|---|---|
| `boot` header | v3, ramdisk **in `boot`**, no `init_boot` |
| kernel | 40.4 MiB, ARM64 `MZ` |
| ramdisk | 8.6 MiB gzip — contains `system/bin/recovery`, `recovery.fstab`, `librecovery_ui.so`, `init.recovery.qcom.rc` |
| `vendor_boot` header | v3, vendor_ramdisk 1.7 MiB, dtb 9.4 MiB |

## Status

Unfinished. Established: the output is DP alt mode, the driver is present in recovery, and
the missing piece is USB-C alt-mode negotiation in a recovery environment. Not yet done:
getting adb authorized in recovery, confirming `DP-1` state from inside recovery, and
building a recovery that triggers the negotiation.
