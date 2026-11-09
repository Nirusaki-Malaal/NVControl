"""GPU and hardware detection utilities for NVControl."""

import logging
import os
import re
import subprocess
from typing import Dict, Optional, Tuple


def parse_pci_bus_id(raw_bus_id: str) -> str:
    """Convert raw PCI address (e.g. '01:00.0' or '0000:01:00.0') to 'PCI:bus:device:function' in decimal."""
    clean_id = raw_bus_id.replace("0000:", "").strip()
    bus, dev_fn = clean_id.split(":")
    device, function = dev_fn.split(".")
    return f"PCI:{int(bus, 16)}:{int(device, 16)}:{int(function, 16)}"


def get_nvidia_gpu_pci_bus(lspci_output: Optional[str] = None) -> str:
    """Find the NVIDIA GPU PCI bus and format as 'PCI:bus:device:function'."""
    if lspci_output is None:
        try:
            lspci_output = subprocess.check_output(['lspci'], stderr=subprocess.DEVNULL).decode('utf-8')
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.error(f"Failed to execute lspci: {e}")
            raise RuntimeError("lspci command failed or is not installed") from e

    for line in lspci_output.splitlines():
        if 'NVIDIA' in line and ('VGA compatible controller' in line or '3D controller' in line):
            raw_bus_id = line.split()[0]
            pci_bus = parse_pci_bus_id(raw_bus_id)
            logging.info(f"Found Nvidia GPU at {raw_bus_id} ({pci_bus})")
            return pci_bus

    logging.error("Could not find Nvidia GPU")
    raise RuntimeError("Nvidia GPU not found via lspci. If in integrated mode, switch to hybrid first.")


def detect_nvidia_architecture(model_name: str) -> str:
    """Detect NVIDIA microarchitecture from GPU model name or chip code."""
    name_upper = model_name.upper()
    if any(code in name_upper for code in ['GB10', 'GB20', 'RTX 50', 'BLACKWELL']):
        return 'Blackwell (RTX 50 Series)'
    if any(code in name_upper for code in ['AD10', 'RTX 40', 'ADA LOVELACE']):
        return 'Ada Lovelace (RTX 40 Series)'
    if any(code in name_upper for code in ['GA10', 'RTX 30', 'AMPERE']):
        return 'Ampere (RTX 30 Series)'
    if any(code in name_upper for code in ['TU10', 'TU11', 'RTX 20', 'GTX 16', 'TURING']):
        return 'Turing (RTX 20 / GTX 16 Series)'
    if any(code in name_upper for code in ['GP10', 'GTX 10', 'PASCAL']):
        return 'Pascal (GTX 10 Series)'
    if any(code in name_upper for code in ['GM10', 'GM20', 'GTX 9', 'MAXWELL']):
        return 'Maxwell'
    return 'NVIDIA Architecture (Generic)'


def get_nvidia_driver_version() -> Optional[str]:
    """Read the active NVIDIA driver version from /proc/driver/nvidia/version or modinfo."""
    proc_version = '/proc/driver/nvidia/version'
    if os.path.exists(proc_version):
        try:
            with open(proc_version, 'r', encoding='utf-8') as f:
                content = f.read()
            match = re.search(r'NVRM version:\s+NVIDIA UNIX [^\s]+ Kernel Module\s+([0-9.]+)', content)
            if match:
                return match.group(1)
            # Generic fallback regex
            match_generic = re.search(r'([0-9]+\.[0-9]+(?:\.[0-9]+)?)', content)
            if match_generic:
                return match_generic.group(1)
        except OSError:
            pass

    # Try modinfo nvidia
    try:
        modinfo_out = subprocess.check_output(['modinfo', '-F', 'version', 'nvidia'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if modinfo_out:
            return modinfo_out
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def get_gpu_runtime_power_status(pci_bus: Optional[str] = None) -> Optional[str]:
    """Check RTD3 / runtime power management status in /sys/bus/pci/devices/."""
    pci_dir = '/sys/bus/pci/devices'
    if not os.path.exists(pci_dir):
        return None

    # Search for NVIDIA PCI devices (vendor 0x10de)
    try:
        for dev in os.listdir(pci_dir):
            dev_path = os.path.join(pci_dir, dev)
            vendor_path = os.path.join(dev_path, 'vendor')
            if os.path.exists(vendor_path):
                with open(vendor_path, 'r', encoding='utf-8') as vf:
                    if vf.read().strip() == '0x10de':
                        # Check class
                        class_path = os.path.join(dev_path, 'class')
                        if os.path.exists(class_path):
                            with open(class_path, 'r', encoding='utf-8') as cf:
                                c = cf.read().strip()
                                # 0x030000 (VGA) or 0x030200 (3D controller)
                                if c.startswith('0x03'):
                                    status_file = os.path.join(dev_path, 'power', 'runtime_status')
                                    if os.path.exists(status_file):
                                        with open(status_file, 'r', encoding='utf-8') as sf:
                                            return sf.read().strip()
    except OSError:
        pass
    return None


def get_detailed_gpu_info() -> Dict[str, str]:
    """Return dictionary with detected GPU models, architectures, driver version, and power status."""
    info = {
        'igpu_vendor': 'Unknown',
        'igpu_model': 'Unknown',
        'nvidia_model': 'Not Detected (Powered Off or Absent)',
        'nvidia_pci_bus': 'None',
        'nvidia_arch': 'Unknown',
        'nvidia_driver': 'Not Loaded',
        'power_status': 'Unknown'
    }

    try:
        lspci_output = subprocess.check_output(['lspci'], stderr=subprocess.DEVNULL).decode('utf-8')
    except (subprocess.CalledProcessError, FileNotFoundError):
        lspci_output = ""

    for line in lspci_output.splitlines():
        if 'VGA compatible controller' in line or '3D controller' in line or 'Display controller' in line:
            if 'NVIDIA' in line:
                raw_bus = line.split()[0]
                model = line.split(':', 2)[-1].strip()
                info['nvidia_model'] = model
                info['nvidia_pci_bus'] = parse_pci_bus_id(raw_bus)
                info['nvidia_arch'] = detect_nvidia_architecture(model)
            elif 'Intel' in line:
                info['igpu_vendor'] = 'Intel'
                info['igpu_model'] = line.split(':', 2)[-1].strip()
            elif any(amd in line for amd in ['AMD', 'ATI', 'AMD/ATI']):
                info['igpu_vendor'] = 'AMD'
                info['igpu_model'] = line.split(':', 2)[-1].strip()

    driver_ver = get_nvidia_driver_version()
    if driver_ver:
        info['nvidia_driver'] = driver_ver

    pwr_status = get_gpu_runtime_power_status()
    if pwr_status:
        info['power_status'] = pwr_status

    return info


def get_igpu_vendor(lspci_output: Optional[str] = None) -> Optional[str]:
    """Detect whether iGPU is Intel or AMD."""
    if lspci_output is None:
        try:
            lspci_output = subprocess.check_output(["lspci"], stderr=subprocess.DEVNULL).decode('utf-8')
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    for line in lspci_output.splitlines():
        if 'VGA compatible controller' in line or 'Display controller' in line:
            if 'Intel' in line:
                logging.info("Found Intel iGPU")
                return 'intel'
            elif any(amd in line for amd in ['ATI', 'AMD', 'AMD/ATI']):
                logging.info("Found AMD iGPU")
                return 'amd'

    logging.warning("Could not find Intel or AMD iGPU")
    return None


def get_amd_igpu_name() -> Optional[str]:
    """Get AMD iGPU provider name from xrandr (safe against failures)."""
    if not os.path.exists('/usr/bin/xrandr'):
        logging.warning("The 'xrandr' command is not available. Make sure the package is installed!")
        return None

    try:
        xrandr_output = subprocess.check_output(['xrandr', '--listproviders'], stderr=subprocess.DEVNULL).decode('utf-8')
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.warning("Failed to run the 'xrandr' command.")
        return None

    pattern = re.compile(r'(name:).*(ATI*|AMD*|AMD\/ATI)*')
    if pattern.findall(xrandr_output):
        match = re.search(pattern, xrandr_output)
        if match:
            return match.group(0)[5:]

    logging.warning("Could not find AMD iGPU in 'xrandr' output.")
    return None


def get_display_manager() -> Optional[str]:
    """Detect the active display manager from systemd configuration."""
    service_path = '/etc/systemd/system/display-manager.service'
    try:
        with open(service_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'ExecStart=(.+)\n', content)
            if match:
                dm = os.path.basename(match.group(1).strip().split()[0])
                logging.info(f"Found {dm} Display Manager")
                return dm
    except (FileNotFoundError, OSError):
        pass

    # Fallback: check if symlink target
    if os.path.islink(service_path):
        try:
            target = os.readlink(service_path)
            dm = os.path.basename(target).replace('.service', '')
            logging.info(f"Found {dm} Display Manager via symlink")
            return dm
        except OSError:
            pass

    logging.warning("Display Manager detection is not available")
    return None


def get_session_type() -> str:
    """Detect if running under Wayland, X11, or TTY."""
    session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
    if session_type in ['wayland', 'x11']:
        return session_type
    if os.environ.get('WAYLAND_DISPLAY'):
        return 'wayland'
    if os.environ.get('DISPLAY'):
        return 'x11'
    return 'tty/headless'
