# Device: Qualcomm Technologies, Inc. Tuna SoC (metroid)

> **Start here:** [docs/booting.md](docs/booting.md) is the step-by-step reference to boot HakiOS on this phone.


Made by `tools/new-device.py` on 2026-11-13, from the file metroid-merged.dtb. Edit it as the port goes.

**Where the tree came from.** The phone is not rooted, so `/sys/firmware/fdt` is not readable. The tree is
rebuilt from the stock firmware of the same build as the phone (`Metroid_C5.0-260924-2115`, MetroidIND),
from the nothing_archive mirror, with every image checked against its published SHA-256:

1. `vendor_boot.img` holds 19 base DTBs. The phone reports `ro.boot.dtb_idx=16`: `base-16`, "Tuna SoC",
   `qcom,msm-id = <0x28f 0x10000>`. This matches `/sys/devices/soc0/soc_id=655` (0x28f) and `machine=TUNA`.
2. `dtbo.img` holds 149 overlays. The phone reports `ro.boot.dtbo_idx=145`: "Tuna QRD", board-id `<0xb 0>`.
   This matches `/sys/devices/soc0/platform_subtype=QRD`. The overlay carries Nothing's own nodes
   (`nothing,*`, `Nothing,matrix_leds_spi`).
3. `fdtoverlay -i base-16.dtb -o metroid-merged.dtb overlay-145.dtbo`.

The bootloader can still change the tree at boot (memory size, serial number, cmdline). Confirm any value
that matters against a tree read from the running phone (`pull-soc.sh`) when root is available. The
SoC is SM8735, which Qualcomm's trees call **Tuna**; the SoC layer here is named `sm8735`.

`soc_pas_mpss` is missing: the modem node (`remoteproc-mss@04080000`, compatible `qcom,tuna-modem-pas`)
has no `qcom,pas-id` property. Its PAS ID is decided in the driver for this compatible, not in the tree.
Do not guess it; find it before the modem driver is brought up.

| What | Value |
|---|---|
| Board (the tree's `model`) | Qualcomm Technologies, Inc. Tuna SoC |
| Compatible | `qcom,tuna` |

## The SoC addresses

**This tree differs from the reference phone's** in 11 value(s) and lacks 1: `soc_ipa_base`, `soc_gsi_base`, `soc_ipcc`, `soc_rsc`, `soc_cmd_db`, `soc_mpss_mem`, `modem_ipa_fw_at`, `soc_smem`, `soc_ipa_stream`, `soc_ipa_stream_uc`, `soc_ipa_fw`, `soc_pas_mpss`. Those are this phone's own addresses; `soc.args` carries them to the kernel and the run scripts add the file to the command line.

| Argument | Value | Against the reference |
|---|---|---|
| `soc_ipa_base` | `0x3e40000` | **differs from the reference** (`0x1e40000`) |
| `soc_gsi_base` | `0x3e04000` | **differs from the reference** (`0x1e04000`) |
| `soc_ipcc` | `0x406000` | **differs from the reference** (`0x408000`) |
| `soc_aoss` | `0xc300000` | the same as the reference |
| `soc_rsc` | `0x17a20000` | **differs from the reference** (`0x18220000`) |
| `soc_apps_smmu` | `0x15000000` | the same as the reference |
| `soc_cmd_db` | `0x81c60000` | **differs from the reference** (`0x80860000`) |
| `soc_mpss_mem` | `0x88100000` | **differs from the reference** (`0x8b800000`) |
| `modem_ipa_fw_at` | `0x94e90000` | **differs from the reference** (`0x8b710000`) |
| `soc_smem` | `0x81d00000` | **differs from the reference** (`0x80900000`) |
| `soc_imem` | `0x14600000` | the same as the reference |
| `soc_ipa_stream` | `0x4a0` | **differs from the reference** (`0x480`) |
| `soc_ipa_stream_uc` | `0x4a2` | **differs from the reference** (`0x482`) |
| `soc_pas_mpss` | `(not found)` | **missing**: the tree has no node this was read from; see the table in devices/redwood/README.md |
| `soc_pas_ipa` | `0xf` | the same as the reference |
| `soc_ipa_fw` | `ipa_fws` | **differs from the reference** (`yupik_ipa_fws`) |

`soc.args` is what `tools/soc-args.py` read out of the tree; `pull-soc.sh` makes it again from the phone on
adb. The run scripts add it to the kernel command line. Where each argument comes from in the tree:
`devices/redwood/README.md`.

## Hardware, read from the running phone

Read on 2026-11-13 from the phone with root (Magisk), build `C5.0-260924-2115`. Sources: `/sys`, `/proc`,
`dmesg`, `dumpsys display`, and the live tree `/sys/firmware/fdt`. The live tree gives the same `soc.args`
as the tree rebuilt from the firmware.

### CPUs (for the loader's platform entry and `metal.args`)

| Core | MPIDR | Part | Max (MHz) | Capacity | Cluster |
|---|---|---|---|---|---|
| cpu0-1 | `0x000`, `0x100` | `0xd81` | 2016 | 569 | 0 |
| cpu2-4 | `0x200`-`0x400` | `0xd81` | 3014 | 852 | 1 |
| cpu5-6 | `0x500`, `0x600` | `0xd81` | 2803 | 792 | 2 |
| cpu7 | `0x700` | `0xd82` | 3206 | 1024 | 3 |

- Core number is in MPIDR's second affinity field: `core_shift = 8`, as redwood.
- The fastest core is cpu7: `bootcpu=7`. The slowest are cpu0-1: `small_cores = 0x03`.
- Timer: 19.2 MHz. PSCI 1.1, method from the tree.

### Interrupt controller

`arm,gic-v3`: distributor `0x17100000` (size `0x10000`), redistributors `0x17180000` (size `0x200000`).

### Memory

- RAM: 15,554,668 kB seen by Android (16 GB part).
- The payload window `0xF0000000`-`0xF3FFFFFF` is ordinary RAM to Android (`/proc/iomem`). It overlaps
  `trust_ui_vm_region@f3800000`, which is a `reusable` `shared-dma-pool`, not `no-map`: memory lent to a
  secure VM on demand. A U-Boot tree for this phone must not reserve it. Not yet confirmed by a boot.

### Display

- Panel: `qcom,mdss_dsi_rm692j0_120hz_fhd_plus_dsc_cmd`, 1260x2800, command mode with DSC, 120/90/60 Hz.
- ABL leaves a splash framebuffer: `cont_splash` is on, `splash_region` at `0xFC800000`, size `0x2B00000`
  (non-reusable). The loader recognizes a phone by its framebuffer address; for metroid this is expected
  to be `0xFC800000`. Confirm under U-Boot, which reports what ABL handed over.
- Display controller: `ae00000.qcom,mdss_mdp`.

### Storage

UFS: `qcom,ufshc` at `0x1d84000` (PHY `1d80000.ufsphy_mem`), SK hynix, 6 SCSI disks (LUNs).

### USB

`qcom,dwc-usb3-msm` wrapper at `0xa600000` with `snps,dwc3` inside. UDC `a600000.dwc3`. An eUSB2
repeater sits on the PMIC (`pmih010x@7:eusb2-repeater@fd00`).

### Input

- Power: `pmk8550` PON `pwrkey`. Volume down: PON `resin`.
- Volume up: `gpio-keys`, `vol_up`, `KEY_VOLUMEUP` (115), PMIC GPIO controller phandle `0x2fc`, pin 6,
  active low.
- AI button (Essential Key): `gpio-keys`, `ai_button`, code 250, TLMM pin `0x4e`, active low.
- Touch: FocalTech (`spi:fts_ts`, driver tag `FTS_TS`) on SPI. HakiOS's `hakios.goodix.c` does not fit:
  this needs a driver of its own.

### Other chips seen

Haptics `haptic_hv`, speaker amplifiers `tfa98xx`, codec `wcd939x`, NFC `st21nfc`, FM `rtc6226`,
capacitive sensor `aw9380x`, Glyph Matrix `matrix_leds_spi`.

## What is this phone's own

The kernel, loader and user space know nothing about a phone: addresses, interrupts, rails and firmware
come from its tree and its Android. What is written for one phone is the list below. The head of each file
says where its numbers came from; that is the map of what to rewrite.

- [ ] **UEFI**: the firmware that starts the loader: devices/redwood/uefi/ is a port of Mu-Silicium; the vendor's drivers are extracted from your own phone (uefi/README.md)
- [ ] **Display, buttons, touch**: drivers/input/hakios.input.c, hakios.buttons.c, hakios.goodix.c (the reference phone's controller; another phone has another)
- [ ] **Storage**: hakios.ufs.c and hakios.ufshc.c (UFS); a phone with eMMC needs another driver
- [ ] **CPU clocks**: hakios.cpufreq.c
- [ ] **GPU**: hakios.adreno.c (Adreno 642L here: another generation needs its own firmware and registers)
- [ ] **Wi-Fi**: hakios.wifi.c, hakios.lx.c and wifi/lx/ (the WCN6750 radio of the reference phone)
- [ ] **Audio and battery**: hakios.adsp.c, hakios.audio.c, hakios.sound.c, hakios.speaker.c, hakios.mic.c, hakios.battery.c
- [ ] **Cellular**: hakios.mpss.c, hakios.qmi.c, hakios.nas.c, hakios.ipa.c, hakios.cell.c; soc.args carries the addresses, the IPA layout is for IPA 4.11 (docs/cellular.md)
- [ ] **Haptics and cameras**: hakios.haptic.c, hakios.camera.c

## Configuration

The kernel's settings are layered the way an Android kernel's are: the common kernel, the SoC's, this phone's
(`docs/configs.md`). Two short files make this phone a configuration:

    configs/metroid.config          CONFIG_DEVICE="metroid"   and whatever is true of this phone only
    configs/metroid_defconfig       #include common_defconfig
                                   #include <the SoC's fragment: sc7280.config for the SC7280 family>
                                   #include metroid.config

Then `make metroid_defconfig`. Turn on only what this phone has been shown to do; `tools/hakios-config.py check` says what the
choice needs.

The drivers are part of the configuration too (`docs/drivers-config.md`): every one is built unless a configuration leaves it out,
and the addresses, pins and rails in each are the reference phone's. Leave out in `configs/metroid.config` what has not been
ported to this phone yet (`# CONFIG_HAKIOS_GOODIX is not set`, ...; `configs/qemu_defconfig` leaves out all of them), and put
each one back when it has been made to work here. `tools/hakios-config.py show` lists what is built in.

## Firmware

Pulled from your own phone, never committed: `devices/redwood/pull-firmware.sh`, or
`pull-firmware-root.sh` where the firmware is readable by root only. Check with `make doctor`.

## Before you open a pull request

`tools/provenance-check.py` must pass: no vendor firmware, no UEFI drivers, no Apple files in the tree.

## The repository

A HakiOS device repository: what is true of this device and of no other. The kernel, the loader, the drivers and the tools are
the common repository's; the sm8735 family's facts are in `soc/`, carried with the device. How the three are put together:
[docs/porting/repositories.md](https://github.com/oosexgang/hakios-xnu-kernel/blob/main/docs/porting/repositories.md).

| File | What |
|---|---|
| `metal.args` | what `tools/metal-run.sh` gives this phone: its cores, its panel's rate, the threads that copy frames, the touch poll |
| `device.conf` | what the device is, and how far each part of it works: its page in the documentation is made from it |
| `configs/metroid_defconfig` | the common kernel, the SoC's fragment, this device's: `make metroid_defconfig` |
| `configs/metroid.config` | what is this device's own: the drivers built in, the arguments it needs |
| `soc/` | its SoC family's layer (sm8735): `soc.conf`, `configs/sm8735.config`, the SoC's drivers; carried here so that this one repository is all the device needs |
| `drivers/` | drivers of its own, if it needs any (`drivers/<subsystem>/conf`, as in the common repository) |

Every phone driver of the common repository is left out to begin with: their addresses and pins are the phone they were written
for. Put one back in `configs/metroid.config` when it has been made to work here, and say so in `device.conf`.

Check with `tools/hakios-device.py check metroid`.
