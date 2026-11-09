"""Graphics mode switching and configuration generation for NVControl."""

import json
import logging
import os
import subprocess
import sys
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

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
    NVCONTROL_CACHE_FILE_PATH,
    SDDM_XSETUP_CONTENT,
    SDDM_XSETUP_PATH,
    UDEV_INTEGRATED,
    UDEV_INTEGRATED_PATH,
    UDEV_PM_CONTENT,
    UDEV_PM_PATH,
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


def create_file(path: str, content: str, executable: bool = False) -> bool:
    """Create a file and its parent directories with specified content."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode='w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"Created file {path}")
        if logging.getLogger().level == logging.DEBUG:
            print(content)

        if executable:
            os.chmod(path, 0o755)
            logging.info(f"Added execution privilege to file {path}")
        return True
    except OSError as e:
        logging.error(f"Failed to create file '{path}': {e}")
        return False


def cleanup() -> None:
    """Remove EnvyControl/NVControl generated files and restore backups."""
    to_remove = [
        BLACKLIST_PATH,
        UDEV_INTEGRATED_PATH,
        UDEV_PM_PATH,
        XORG_PATH,
        EXTRA_XORG_PATH,
        MODESET_PATH,
        LIGHTDM_SCRIPT_PATH,
        LIGHTDM_CONFIG_PATH,
        # legacy paths
        '/etc/X11/xorg.conf.d/90-nvidia.conf',
        '/lib/udev/rules.d/50-remove-nvidia.rules',
        '/lib/udev/rules.d/80-nvidia-pm.rules'
    ]

    for file_path in to_remove:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Removed file {file_path}")
        except OSError as e:
            if e.errno != 2:
                logging.error(f"Failed to remove file '{file_path}': {e}")

    # Restore SDDM Xsetup backup if found
    backup_path = SDDM_XSETUP_PATH + ".bak"
    if os.path.exists(backup_path):
        logging.info("Restoring Xsetup backup")
        try:
            with open(backup_path, mode="r", encoding="utf-8") as f:
                create_file(SDDM_XSETUP_PATH, f.read())
            os.remove(backup_path)
            logging.info(f"Removed file {backup_path}")
        except OSError as e:
            logging.error(f"Failed to restore SDDM backup: {e}")


def get_current_mode() -> str:
    """Detect current graphics mode: 'integrated', 'hybrid', or 'nvidia'."""
    # PR #234 fix: OR logic for integrated mode markers handles partial state cleanly
    if (os.path.exists(BLACKLIST_PATH) or
            os.path.exists(UDEV_INTEGRATED_PATH) or
            os.path.exists('/lib/udev/rules.d/50-remove-nvidia.rules')):
        return 'integrated'
    elif os.path.exists(XORG_PATH) and os.path.exists(MODESET_PATH):
        return 'nvidia'
    return 'hybrid'


def build_modprobe_config(
    driver_module: str = 'nvidia',
    rtd3_value: Optional[int] = None,
    enable_fbdev: bool = True,
    preserve_video_memory: bool = False,
    enable_suspend_notifiers: bool = True,
    extra_options: str = ''
) -> str:
    """Generate modprobe configuration for NVIDIA driver with modern 615+ / Wayland parameters."""
    fbdev_str = " fbdev=1" if enable_fbdev else ""

    preserve_parts = []
    if preserve_video_memory:
        preserve_parts.append("NVreg_PreserveVideoMemoryAllocations=1")
        preserve_parts.append("NVreg_TemporaryFilePath=/var/tmp")
    else:
        preserve_parts.append("NVreg_InitializeSystemMemoryAllocations=0")

    if enable_suspend_notifiers:
        preserve_parts.append("NVreg_UseKernelSuspendNotifiers=1")

    extra_parts = []
    if rtd3_value is not None:
        extra_parts.append(f'"NVreg_DynamicPowerManagement=0x0{rtd3_value}"')
    if extra_options:
        extra_parts.append(extra_options.strip())

    preserve_str = (" " + " ".join(preserve_parts)) if preserve_parts else ""
    extra_str = ("\noptions " + driver_module + " " + " ".join(extra_parts)) if extra_parts else ""

    return MODESET_CONTENT.format(
        driver_module=driver_module,
        fbdev_option=fbdev_str,
        preserve_mem_options=preserve_str,
        extra_opts=extra_str
    )


def generate_xrandr_script(igpu_vendor: Optional[str]) -> str:
    """Generate Xrandr provider script for SDDM and LightDM."""
    if igpu_vendor == 'amd':
        amd_igpu_name = get_amd_igpu_name()
        provider = amd_igpu_name if amd_igpu_name else 'modesetting'
    else:
        provider = 'modesetting'
    return NVIDIA_XRANDR_SCRIPT.format(provider)


def set_systemd_service(service_name: str, enable: bool) -> None:
    """Enable or disable a systemd service quietly or in debug mode."""
    action = "enable" if enable else "disable"
    cmd = ["systemctl", action, service_name]
    try:
        if logging.getLogger().level == logging.DEBUG:
            p = subprocess.run(cmd)
        else:
            p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if p.returncode == 0:
            print(f"Successfully {action}d {service_name}")
        else:
            logging.debug(f"systemctl {action} {service_name} returned code {p.returncode}")
    except (OSError, subprocess.SubprocessError) as e:
        logging.debug(f"Unable to run systemctl {action} for {service_name}: {e}")


def manage_sleep_services(enable: bool) -> None:
    """Enable or disable nvidia sleep services for video memory preservation."""
    for srv in ["nvidia-suspend.service", "nvidia-hibernate.service", "nvidia-resume.service"]:
        set_systemd_service(srv, enable)


def graphics_mode_switcher(
    graphics_mode: str,
    user_display_manager: Optional[str] = None,
    enable_force_comp: bool = False,
    coolbits_value: Optional[int] = None,
    rtd3_value: Optional[int] = None,
    use_nvidia_current: bool = False,
    preserve_video_memory: bool = False,
    enable_fbdev: bool = True,
    enable_suspend_notifiers: bool = True,
    get_pci_bus_fn: Optional[Callable[[], str]] = None
) -> None:
    """Execute switching procedure between integrated, hybrid, and nvidia modes."""
    driver_module = 'nvidia-current' if use_nvidia_current else 'nvidia'
    print(f"Switching to {graphics_mode} mode")

    if graphics_mode == 'integrated':
        set_systemd_service("nvidia-persistenced.service", enable=False)
        manage_sleep_services(enable=False)
        cleanup()

        create_file(BLACKLIST_PATH, BLACKLIST_CONTENT)
        create_file(UDEV_INTEGRATED_PATH, UDEV_INTEGRATED)
        rebuild_initramfs()

    elif graphics_mode == 'hybrid':
        print(f"Enable PCI-Express Runtime D3 (RTD3) Power Management: {rtd3_value is not None}")
        if rtd3_value is not None:
            print(f"RTD3 Mode: {rtd3_value}")
        if preserve_video_memory:
            print("Preserve Video Memory Allocations across suspend/resume: Enabled")

        cleanup()
        set_systemd_service("nvidia-persistenced.service", enable=True)

        if preserve_video_memory:
            manage_sleep_services(enable=True)

        modprobe_text = build_modprobe_config(
            driver_module=driver_module,
            rtd3_value=rtd3_value,
            enable_fbdev=enable_fbdev,
            preserve_video_memory=preserve_video_memory,
            enable_suspend_notifiers=enable_suspend_notifiers
        )
        create_file(MODESET_PATH, modprobe_text)

        if rtd3_value is not None:
            create_file(UDEV_PM_PATH, UDEV_PM_CONTENT)

        rebuild_initramfs()

    elif graphics_mode == 'nvidia':
        print(f"Enable ForceCompositionPipeline: {enable_force_comp}")
        print(f"Enable Coolbits: {coolbits_value if coolbits_value is not None else False}")
        if preserve_video_memory:
            print("Preserve Video Memory Allocations across suspend/resume: Enabled")

        set_systemd_service("nvidia-persistenced.service", enable=True)
        if preserve_video_memory:
            manage_sleep_services(enable=True)

        cleanup()

        # Retrieve GPU PCI bus (from cache or live query)
        pci_fn = get_pci_bus_fn if get_pci_bus_fn is not None else get_nvidia_gpu_pci_bus
        nvidia_gpu_pci_bus = pci_fn()

        igpu_vendor = get_igpu_vendor()

        # Create X.org configuration
        if igpu_vendor == 'amd':
            create_file(XORG_PATH, XORG_AMD.format(nvidia_gpu_pci_bus))
        else:
            create_file(XORG_PATH, XORG_INTEL.format(nvidia_gpu_pci_bus))

        # Create modprobe configuration
        modprobe_text = build_modprobe_config(
            driver_module=driver_module,
            rtd3_value=None,
            enable_fbdev=enable_fbdev,
            preserve_video_memory=preserve_video_memory,
            enable_suspend_notifiers=enable_suspend_notifiers
        )
        create_file(MODESET_PATH, modprobe_text)

        # Extra Xorg options
        extra_content = EXTRA_XORG_CONTENT
        if enable_force_comp:
            extra_content += FORCE_COMP
        if coolbits_value is not None:
            extra_content += COOLBITS.format(coolbits_value)
        if enable_force_comp or coolbits_value is not None:
            extra_content += 'EndSection\n'
            create_file(EXTRA_XORG_PATH, extra_content)

        # Display manager setup
        display_manager = user_display_manager if user_display_manager is not None else get_display_manager()
        if display_manager == 'sddm':
            if os.path.exists(SDDM_XSETUP_PATH):
                logging.info("Creating Xsetup backup")
                try:
                    with open(SDDM_XSETUP_PATH, mode='r', encoding='utf-8') as f:
                        create_file(SDDM_XSETUP_PATH + '.bak', f.read())
                except OSError as e:
                    logging.warning(f"Failed to read SDDM Xsetup for backup: {e}")
            create_file(SDDM_XSETUP_PATH, generate_xrandr_script(igpu_vendor), executable=True)
        elif display_manager == 'lightdm':
            create_file(LIGHTDM_SCRIPT_PATH, generate_xrandr_script(igpu_vendor), executable=True)
            create_file(LIGHTDM_CONFIG_PATH, LIGHTDM_CONFIG_CONTENT)

        rebuild_initramfs()

    print('Operation completed successfully')
    print('Please reboot your computer for changes to take effect!')


class CachedConfig:
    """Manages cached NVIDIA PCI bus ID for switching modes when dGPU is powered down."""

    def __init__(self, app_args: Any) -> None:
        self.app_args = app_args
        self.current_mode = get_current_mode()
        self.nvidia_gpu_pci_bus: Optional[str] = None
        self.obj: Dict[str, Any] = {}

    @contextmanager
    def adapter(self):
        """Context manager adapting PCI bus detection with cache fallback."""
        # PR #234 fix: Only recreate cache when leaving hybrid mode.
        # Switching *to* hybrid never needs the cached value and the GPU
        # may not be visible via lspci if old udev rules are still present.
        if self.is_hybrid() and getattr(self.app_args, 'switch', None) != 'hybrid':
            try:
                self.create_cache_file()
            except Exception as e:
                logging.warning(f"Could not create cache file: {e}")

        use_cache = os.path.exists(self.get_active_cache_path())
        if use_cache:
            try:
                self.read_cache_file()
            except Exception as e:
                logging.warning(f"Could not read cache file: {e}")

        yield

    @staticmethod
    def get_active_cache_path() -> str:
        if os.path.exists(CACHE_FILE_PATH):
            return CACHE_FILE_PATH
        return NVCONTROL_CACHE_FILE_PATH

    def create_cache_file(self) -> None:
        if not self.is_hybrid():
            raise ValueError('--cache-create requires that the system be in the hybrid Optimus mode')

        self.nvidia_gpu_pci_bus = get_nvidia_gpu_pci_bus()
        self.obj = {'nvidia_gpu_pci_bus': self.nvidia_gpu_pci_bus}
        self.write_cache_file()

    def is_hybrid(self) -> bool:
        return self.current_mode == 'hybrid'

    def get_nvidia_gpu_pci_bus(self) -> str:
        if self.nvidia_gpu_pci_bus is not None:
            return self.nvidia_gpu_pci_bus
        return get_nvidia_gpu_pci_bus()

    @classmethod
    def delete_cache_file(cls) -> None:
        for p in [CACHE_FILE_PATH, NVCONTROL_CACHE_FILE_PATH]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                    logging.info(f"Removed cache file {p}")
                    parent = os.path.dirname(p)
                    if not os.listdir(parent):
                        os.rmdir(parent)
                except OSError as e:
                    logging.error(f"Failed to delete cache file {p}: {e}")

    def read_cache_file(self) -> None:
        cache_path = self.get_active_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                self.obj = json.load(f)
            self.nvidia_gpu_pci_bus = self.obj.get('nvidia_gpu_pci_bus')
        elif self.is_hybrid():
            self.nvidia_gpu_pci_bus = get_nvidia_gpu_pci_bus()
        else:
            raise ValueError('No cache present. Operation requires that the system be in the hybrid Optimus mode')

    @classmethod
    def show_cache_file(cls) -> None:
        cache_path = cls.get_active_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    print(f.read())
                return
            except OSError:
                pass
        print(f'ERROR: Could not read {cache_path}')

    def write_cache_file(self) -> None:
        cache_path = self.get_active_cache_path()
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.obj, fp=f, indent=4, sort_keys=False)
        logging.info(f"Created cache file {cache_path}")
