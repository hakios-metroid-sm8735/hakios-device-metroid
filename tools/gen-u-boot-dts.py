#!/usr/bin/env python3
"""Write HakiOS's U-Boot device tree for the Nothing Phone (3) from the phone's own live tree.

usage: tools/gen-u-boot-dts.py LIVE_DTB OUT_DTS

Only the fixed no-map reservations are copied: reusable pools are memory Android lends out on demand, and the
HakiOS payload window (0xF0000000, 64 MiB) lies on two of them.
"""
import subprocess
import sys

PAYLOAD = (0xF0000000, 0x4000000)
SPLASH = (0xFC800000, 0x2B00000)
WIDTH, HEIGHT = 1260, 2800


def fdtget(*args):
    return subprocess.run(["fdtget", *args], capture_output=True, text=True, check=False).stdout


def reservations(dtb):
    out = []
    for name in fdtget("-l", dtb, "/reserved-memory").split():
        path = "/reserved-memory/" + name
        props = fdtget("-p", dtb, path).split()
        if "no-map" not in props or "reg" not in props:
            continue
        cells = [int(x, 16) for x in fdtget("-t", "x", dtb, path, "reg").split()]
        for i in range(0, len(cells) - 3, 4):
            base = (cells[i] << 32) | cells[i + 1]
            size = (cells[i + 2] << 32) | cells[i + 3]
            label = name.split("@")[0].replace("_region", "").replace("_", "-")
            out.append((base, size, label))
    out.sort()
    for base, size, label in out:
        if base < PAYLOAD[0] + PAYLOAD[1] and base + size > PAYLOAD[0]:
            sys.exit("gen-u-boot-dts.py: %s overlaps the payload window" % label)
    return out


def main():
    dtb, out_path = sys.argv[1:3]
    rows = reservations(dtb)
    lines = []
    for base, size, label in rows:
        lines.append("\t\t%s@%x {\n\t\t\treg = <0x0 0x%x 0x0 0x%x>;\n\t\t\tno-map;\n\t\t};\n" % (label, base, base, size))
    text = HEAD % {"count": len(rows), "w": WIDTH, "h": HEIGHT, "fb": SPLASH[0], "fbsize": SPLASH[1]}
    text += "\n".join(lines) + TAIL
    open(out_path, "w").write(text)
    print("gen-u-boot-dts.py: %d no-map reservations written to %s" % (len(rows), out_path))


HEAD = """// SPDX-License-Identifier: BSD-3-Clause
/*
 * The Nothing Phone (3) (metroid, SM8735 "Tuna") for HakiOS's U-Boot: first light only.
 *
 * U-Boot has no clock, pinctrl or PHY support for SM8735 (v2026.07), so this tree describes only what needs no
 * driver: the panel's framebuffer as ABL left it, the PSCI firmware interface, and the memory that firmware and the
 * remote processors keep. No USB, no UFS, no keys yet: the loader and its payload come in the boot image's ramdisk.
 *
 * The size of RAM is not here: ABL writes it into the device tree it hands over, and U-Boot reads it from there
 * (arch/arm/mach-snapdragon/board.c, board_fdt_blob_setup()).
 *
 * The reservations are the %(count)d fixed no-map regions of the phone's own live tree (/sys/firmware/fdt, build
 * C5.0-260924-2115), generated, not edited by hand. The reusable pools are left out: Android lends them on demand,
 * and two of them (trust_ui_vm, oem_vm) cover the HakiOS payload window at 0xF0000000.
 */

/dts-v1/;

/ {
	model = "Nothing Phone (3)";
	compatible = "nothing,metroid", "qcom,sm8735";
	chassis-type = "handset";
	#address-cells = <2>;
	#size-cells = <2>;

	/* what ABL matches against: SM8735 (soc_id 655 = 0x28f) v1, the QRD board (ro.boot.dtbo_idx=145) */
	qcom,msm-id = <0x28f 0x10000>;
	qcom,board-id = <0xb 0>;

	chosen {
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;

		/*
		 * The panel as ABL left it (cont_splash, splash_region): 1260 x 2800. 32 bits a pixel is assumed, as on
		 * redwood; not yet seen on this phone. At 0xFC800000 the HakiOS loader knows the phone by it
		 * (xnuloader/loader.c, platform_metroid). No clocks: U-Boot keeps the display running by not touching it.
		 */
		framebuffer0: framebuffer@%(fb)x {
			compatible = "simple-framebuffer";
			reg = <0x0 0x%(fb)x 0x0 (%(w)d * %(h)d * 4)>;
			width = <%(w)d>;
			height = <%(h)d>;
			stride = <(%(w)d * 4)>;
			format = "a8r8g8b8";
		};
	};

	psci {
		compatible = "arm,psci-1.0";
		method = "smc";
	};

	soc@0 {
		compatible = "simple-bus";
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;

		/*
		 * The SMMU that USB's DMA goes through (stream 0x40 in the phone's tree). U-Boot's qcom-hyp-smmu only maps
		 * the streams of the devices it uses as bypass, on an SMMU ABL has already set up.
		 */
		apps_smmu: iommu@15000000 {
			compatible = "qcom,smmu-500", "arm,mmu-500";
			reg = <0x0 0x15000000 0x0 0x100000>;
			#iommu-cells = <2>;
		};

		/*
		 * USB as a device, for the HakiOS loader's fastboot (xl). Laid out as SM8750's upstream node (flat
		 * qcom,snps-dwc3, qscratch at +0xf8800), which the phone's core_base (0xa600000) matches.
		 * No clocks, resets, power domain or PHY on purpose: U-Boot has no SM8735 clock driver, so the controller,
		 * the eUSB2 PHY and its repeater are used as ABL left them after its own fastboot. Not yet seen to work.
		 */
		usb_1: usb@a600000 {
			compatible = "qcom,snps-dwc3";
			reg = <0x0 0x0a600000 0x0 0xfc100>;
			iommus = <&apps_smmu 0x40 0x0>;
			dr_mode = "peripheral";
			maximum-speed = "high-speed";
			snps,hird-threshold = /bits/ 8 <0x0>;
			snps,usb2-gadget-lpm-disable;
			snps,usb2-lpm-disable;
			snps,dis_u2_susphy_quirk;
			snps,dis_enblslpm_quirk;
			snps,has-lpm-erratum;
		};
	};

	reserved-memory {
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;

		/* the panel's memory, as ABL reserved it */
		cont-splash@%(fb)x {
			reg = <0x0 0x%(fb)x 0x0 0x%(fbsize)x>;
			no-map;
		};

		/*
		 * Where the HakiOS loader takes its payload from (PAYLOAD_BASE, 64 MiB with the panic log in its last MiB).
		 * Mapped (no no-map): the hakios command writes the payload here, and nothing else in U-Boot may take it.
		 */
		hakios-payload@f0000000 {
			reg = <0x0 0xf0000000 0x0 0x4000000>;
		};

"""

TAIL = """	};
};
"""

if __name__ == "__main__":
    main()
