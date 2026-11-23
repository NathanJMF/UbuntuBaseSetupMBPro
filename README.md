# UbuntuBaseSetupMBPro

Recreate an Ubuntu 26.04 GNOME desktop on a 2019 13-inch MacBook Pro (`MacBookPro15,4`). Setup runs the latest UbuntuBaseSetup, installs MacBook Thermals, and configures T2 boot, Wi-Fi and Bluetooth recovery.

## Install

Start in a working Ubuntu GNOME session with a bootable generic Ubuntu kernel, an Internet connection, and the [Apple wireless firmware](https://wiki.t2linux.org/guides/wifi-bluetooth/). Open a terminal in this checkout.

| Choose | Command |
| --- | --- |
| Base desktop, Thermals and hardware fixes | `./setup` |
| Add 15% two-finger scrolling | `./setup --scroll 15` |
| Add Nightfall and the 15-minute lock | `./setup --nightfall --lock-after-15-minutes` |

Combine the options as needed. Scroll values from 1 to 200 scale finger movement as a percentage. A mouse wheel keeps its original speed. Sign in again for scrolling and shell extensions. Reboot when ready to try the T2 kernel.

If Bluetooth is switched on but stops discovering devices, disconnect active Bluetooth devices and run `sudo ./recover-bluetooth`. It resets only the Bluetooth function.

## Recovery and replay

For generic-kernel recovery, have a wired USB keyboard and a USB-C adapter if needed. The stock generic kernels tested on this model lack the T2 bridge driver for the built-in keyboard. Choose **Advanced options for Ubuntu** in GRUB to boot the generic kernel. From a desktop session, run `./setup --rollback wireless`, `./setup --rollback scroll`, or `./setup --rollback kernel` to undo that feature. Boot the generic kernel before removing the T2 image. The installer preserves a previously installed T2 image.

The install saves `~/.local/state/ubuntu-mbpro/manifest.json` by default. Keep a copy, check out its MacBook commit, then run `./setup --replay /path/to/manifest.json` in the new desktop session. The manifest pins setup repositories and the T2 kernel. Ubuntu packages and Snap applications follow their configured channels.
