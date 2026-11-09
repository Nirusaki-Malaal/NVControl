"""Dynamic initramfs detection and rebuild utilities for NVControl."""

import logging
import os
import shutil
import subprocess
from typing import List, Optional


def detect_initramfs_command() -> List[str]:
    """Dynamically determine the appropriate initramfs rebuild command based on system tools."""
    # OSTree systems first (Fedora Silverblue, Kinoite, etc.)
    if any(os.path.exists(d) for d in ['/ostree', '/sysroot/ostree']) and shutil.which('rpm-ostree'):
        return ['rpm-ostree', 'initramfs', '--enable', '--arg=--force']

    # Debian / Ubuntu derivatives
    if shutil.which('update-initramfs'):
        return ['update-initramfs', '-u', '-k', 'all']

    # EndeavourOS / Garuda / Arch dracut wrapper
    if shutil.which('dracut-rebuild'):
        return ['dracut-rebuild']

    # dracut (Fedora, RHEL, openSUSE, Void, Gentoo, Arch)
    if shutil.which('dracut'):
        return ['dracut', '--force', '--regenerate-all']

    # Limine bootloader wrapper on Arch Linux (fixes Issue #237)
    if shutil.which('limine-mkinitcpio'):
        return ['limine-mkinitcpio']

    # Arch Linux mkinitcpio
    if shutil.which('mkinitcpio'):
        return ['mkinitcpio', '-P']

    # Booster generator (Arch, Void, modern Linux)
    if os.path.exists('/usr/lib/booster/regenerate_images'):
        return ['/usr/lib/booster/regenerate_images']
    if shutil.which('booster-build'):
        return ['booster-build']

    # ALT Linux make-initrd
    if shutil.which('make-initrd'):
        return ['make-initrd']

    return []


def rebuild_initramfs(custom_command: Optional[List[str]] = None) -> bool:
    """Rebuild initramfs non-interactively using detected or custom tool."""
    command = custom_command if custom_command is not None else detect_initramfs_command()

    if not command:
        logging.warning("No supported initramfs generator found (update-initramfs, dracut, mkinitcpio, booster, make-initrd, rpm-ostree). Skipping rebuild.")
        return False

    # Inhibit sleep/shutdown during initramfs rebuild if systemd-inhibit is available
    if shutil.which('systemd-inhibit'):
        command = [
            'systemd-inhibit',
            '--who=nvcontrol',
            '--why', 'Rebuilding initramfs for GPU switching',
            '--',
            *command
        ]

    cmd_str = ' '.join(command)
    print(f"Rebuilding the initramfs with '{cmd_str}'...")

    try:
        if logging.getLogger().level == logging.DEBUG:
            p = subprocess.run(command, stdin=subprocess.DEVNULL)
        else:
            p = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if p.returncode == 0:
            print("Successfully rebuilt the initramfs!")
            return True
        else:
            logging.error(f"An error occurred while rebuilding initramfs (exit code {p.returncode})")
            return False
    except (OSError, subprocess.SubprocessError) as e:
        logging.error(f"Failed to execute initramfs rebuild command: {e}")
        return False
