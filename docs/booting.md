# Booting HakiOS on the Nothing Phone (3)

This is the reference procedure to boot the Darwin kernel (XNU) of HakiOS on the Nothing Phone (3)
(`metroid`, Qualcomm SM8735, which Qualcomm's trees call "Tuna"). Every step was done on a real phone on
2026-11-13. Each step says what it does to the phone.

## What this is, and what it is not

- HakiOS runs Apple's open-source Darwin kernel (XNU) on Android phones. It is not iOS, and it is not
  affiliated with Apple or with Nothing.
- The Darwin user space (lock screen, home screen, apps) is not in any repository. You build it from an
  Apple restore image (IPSW) that you get yourself. Apple's services (activation, Apple ID, iCloud, App
  Store) do not work.
- The boot is from RAM with `fastboot boot`. Nothing is flashed by the boot itself. A reset gives the phone
  back to Android.

## Status

| Part | Status | Note |
|---|---|---|
| ABL starts the HakiOS U-Boot image (`fastboot boot`) | works | header v1, gzip U-Boot with the phone's tree appended |
| U-Boot on SM8735 | works | no SM8735 clock or pinctrl driver: only what needs no driver |
| Display | partial | ABL's framebuffer at `0xFC800000`, 1260x2800, 32 bits; no GPU |
| USB (`xl`) | partial | the controller, eUSB2 PHY and repeater as ABL left them |
| XNU kernel and `hello` in user space | works | on cpu0; the log is fetched over USB |
| Other cores | not tried | the GIC redistributor stride is unchecked |
| UFS, touch, buttons, GPU, audio, Wi-Fi, modem | missing | see `device.conf` |

`device.conf` is the record. A part is `works` only after it was seen on the phone.

## The repositories

| Repository | Contents |
|---|---|
| [hakios-device-metroid](https://github.com/hakios-metroid-sm8735/hakios-device-metroid) | this repository: the device configuration, the SM8735 SoC layer, the U-Boot files, the tools, this document |
| [hakios-xnu-kernel](https://github.com/hakios-metroid-sm8735/hakios-xnu-kernel), branch `metroid` | the common HakiOS repository with the loader's `metroid` platform, `end_hold=`, and `soc-args.py` for vendor (Tuna) device trees |

## Requirements

- A Nothing Phone (3) with an unlocked boot loader. Unlocking erases the phone.
- A computer with `adb` and `fastboot`. These steps were done on macOS (Apple silicon).
- For the analysis steps: root on the phone (Magisk). The boot itself does not need root.
- Tools (macOS, Homebrew):

  ```sh
  brew install dtc lld aarch64-elf-gcc flock make
  ```

  - `dtc`: the device-tree compiler and `fdtoverlay`, `fdtget`.
  - `lld`: `lld-link`, for the loader (a UEFI application).
  - `aarch64-elf-gcc`: the cross compiler for U-Boot.
  - `flock`: for `xl`.
  - `make`: GNU make 4 (`gmake`), for U-Boot.

## 1. Get the source

```sh
git clone -b metroid https://github.com/hakios-metroid-sm8735/hakios-xnu-kernel.git hakios
cd hakios
tools/hakios-device.py sync         # devices/metroid, devices/redwood (the reference) and uefi/
make doctor                         # reports what this machine lacks
```

## 2. Get the stock firmware (for the device tree and a way back)

1. Read the phone's build:

   ```sh
   adb shell getprop ro.build.display.id        # e.g. C5.0-260924-2115
   ```

2. Download the images of the same build. The nothing_archive project mirrors them
   (`https://github.com/spike0en/nothing_archive`, release `Metroid_<build>`). The `image-boot` and
   `image-firmware` archives are enough (about 150 MB).
3. Extract them and check each image against the release's `-hash.sha256` file. Do not continue if an
   image does not match.
4. Keep `init_boot.img` and `boot.img`: they are the way back to stock.

The images are the vendor's. Keep them on your computer. Never commit them.

## 3. Get the device tree

The kernel and U-Boot need the phone's own addresses. Two ways:

**From the running phone (root):**

```sh
adb shell 'su -c "cat /sys/firmware/fdt"' > metroid-live.dtb
```

**From the stock firmware (no root):**

```sh
devices/metroid/tools/dtextract.py vendor_boot.img dtbo.img dt/
adb shell getprop ro.boot.dtb_idx               # 16 on build C5.0-260924-2115: dt/base-16.dtb
adb shell getprop ro.boot.dtbo_idx              # 145: dt/overlay-145.dtbo
fdtoverlay -i dt/base-16.dtb -o metroid.dtb dt/overlay-145.dtbo
```

The phone reports `/sys/devices/soc0/soc_id = 655` (`0x28f`, Tuna) and `platform_subtype = QRD`. The base
tree must have `qcom,msm-id = <0x28f ...>`, and the overlay must be "Tuna QRD" (board-id `0xb`).

Then:

```sh
python3 tools/soc-args.py metroid.dtb           # must match devices/metroid/soc.args
```

On build `C5.0-260924-2115`, the tree from the firmware and the live tree give the same 15 values.
`soc_pas_mpss` is not in the tree (the modem node has no `qcom,pas-id`). It is not needed to boot.

## 4. Build U-Boot

```sh
uefi/u-boot/apply.sh                # U-Boot v2026.07 into u-boot/, with every device's files
uefi/u-boot/build.sh metroid        # u-boot/build-metroid/u-boot.bin
```

U-Boot v2026.07 has no SM8735 clock, pinctrl or PHY driver. Metroid's U-Boot tree
(`u-boot/files/dts/upstream/src/arm64/qcom/sm8735-nothing-metroid.dts`) therefore holds only:

- the framebuffer ABL leaves (`simple-framebuffer` at `0xFC800000`);
- PSCI;
- the SMMU (`0x15000000`) and the USB controller (`0xa600000`, flat `qcom,snps-dwc3` as SM8750's), with no
  clocks, resets or PHY: they stay as ABL left them after its own fastboot;
- the 40 fixed `no-map` reservations of the live tree, and the HakiOS payload window (`0xF0000000`, 64 MiB).

The tree is generated from the live tree. Do not edit the reservations by hand:

```sh
devices/metroid/tools/gen-u-boot-dts.py metroid-live.dtb \
    devices/metroid/u-boot/files/dts/upstream/src/arm64/qcom/sm8735-nothing-metroid.dts
```

The reusable pools (`trust_ui_vm`, `oem_vm`) are left out on purpose: Android lends them on demand, and
they cover the payload window.

## 5. Build the loader and the boot image

```sh
make loader-open                    # xnuloader/loader.efi, with a placeholder identity (no Apple data)
cp <your stock dir>/base-16.dtb devices/metroid/prebuilt/device-tree.dtb   # for ABL; ignored by git
mkdir -p build
xnuloader/mkpayload.py -o build/metroid-payload.bin --usb \
    kernel=prebuilt/hakios-kernel ramdisk=prebuilt/userland/hello "--cmdline=-v end_hold=120"
tools/mkubootimg.py -d metroid -u u-boot/build-metroid/u-boot.bin -l xnuloader/loader.efi \
    -p build/metroid-payload.bin -o build/hakios-u-boot-metroid.img
```

- The loader knows the phone by the framebuffer address: `0xFC800000` selects `platform_metroid`
  (GIC at `0x17100000`/`0x17180000`, 8 cores, MPIDR core field in bits 8-15).
- `--usb`: the loader waits for `xl` over USB. If USB does not come up, it runs the kernel once.
- `end_hold=120`: after a run with no host, the last screen stays for 120 s before the reset.
- With no `cpus=`, the kernel runs on one core (cpu0).

## 6. Boot

```sh
adb reboot bootloader
fastboot boot build/hakios-u-boot-metroid.img       # RAM only: nothing is flashed
./xl state                                          # loader
XL_RAMDISK=prebuilt/userland/hello XL_SECS=60 XL_CMDLINE="-v" ./xl run
./xl reboot                                         # back to Android
```

Expected result: `result: returned <n> 0`, and in `logs/<time>-run.log`:

```
Hello from user space on Darwin!
gic: v3, distributor ..., cpu 0's redistributor ...
MiniIOMobileFramebuffer: display 1125x2436 on a panel of 1260x2800 (5040 bytes per row)
panic(cpu 0 caller ...): initproc failed to start ...
```

The panic is expected: `hello` is the first process, and it exits when it has printed.

## If something goes wrong

| You see | Do |
|---|---|
| `fastboot boot` fails | the boot loader is locked, or the image is not a boot image |
| The screen stays black | U-Boot did not start: report it, with the image you used |
| No `18d1:d00d` device after the boot | USB did not come up under U-Boot; the loader runs the kernel once, holds the screen (`end_hold=`), then resets |
| The phone does not respond | hold power for about 15 s: the phone restarts into Android |

Nothing in these steps writes to the phone's storage. The U-Boot here has no UFS driver, so the loader
does not even write its log to `logdump`.

## Root (optional, for analysis)

Root was used to read the live tree, `/proc/iomem` and `dmesg`. It is not needed to boot.

1. Install Magisk (official release from `https://github.com/topjohnwu/Magisk`; check its SHA-256).
2. Patch the stock `init_boot.img` of the running build with Magisk (`KEEPVERITY=true`,
   `KEEPFORCEENCRYPT=true`).
3. `fastboot flash init_boot_<active slot> magisk_patched.img` (the active slot: `fastboot getvar current-slot`).

This writes `init_boot` of one slot. To remove root, flash the stock `init_boot.img` to the same slot.
Before a system update, use Magisk's "Install to inactive slot", or patch the new `init_boot` again.

## Next steps

1. The Darwin user space from your own IPSW (`docs/getting-started/qemu.md` in the common repository).
2. Touch (FocalTech on SPI) and the buttons (PMK8550 PON, a PMIC GPIO).
3. All 8 cores: check the GIC redistributor stride (`0x200000` for 8 cores in the tree).
4. UFS, then the GPU.
