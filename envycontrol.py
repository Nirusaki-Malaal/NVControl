#!/usr/bin/env python3
"""EnvyControl backward-compatibility shim for NVControl."""

import sys
from nvcontrol.constants import (
    BLACKLIST_CONTENT,
    BLACKLIST_PATH,
    CACHE_FILE_PATH,
    COOLBITS,
    EXTRA_XORG_CONTENT,
    EXTRA_XORG_PATH,
    FORCE_COMP,
    LIGHTDM_CONFIG_CONTENT,
    LIGHTDM_CONFIG_PATH,
    LIGHTDM_SCRIPT_PATH,
    MODESET_CONTENT,
    MODESET_PATH,
    NVIDIA_XRANDR_SCRIPT,
    RTD3_MODES,
    SDDM_XSETUP_CONTENT,
    SDDM_XSETUP_PATH,
    SUPPORTED_DISPLAY_MANAGERS,
    SUPPORTED_MODES,
    UDEV_INTEGRATED,
    UDEV_INTEGRATED_PATH,
    UDEV_PM_CONTENT,
    UDEV_PM_PATH,
    VERSION,
    XORG_AMD,
    XORG_INTEL,
    XORG_PATH,
)
from nvcontrol.gpu import (
    get_amd_igpu_name,
    get_display_manager,
    get_igpu_vendor,
    get_nvidia_gpu_pci_bus,
)
from nvcontrol.initramfs import rebuild_initramfs
from nvcontrol.switcher import (
    CachedConfig,
    cleanup,
    create_file,
    get_current_mode,
    graphics_mode_switcher,
)
from nvcontrol.cli import assert_root, main

if __name__ == '__main__':
    main()
