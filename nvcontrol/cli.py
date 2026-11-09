"""Command-line interface parser and handler for NVControl."""

import argparse
import logging
import os
import sys
from typing import List, Optional

from nvcontrol.constants import (
    RTD3_MODES,
    SDDM_XSETUP_CONTENT,
    SDDM_XSETUP_PATH,
    SUPPORTED_DISPLAY_MANAGERS,
    SUPPORTED_MODES,
    VERSION,
)
from nvcontrol.gpu import (
    get_detailed_gpu_info,
    get_display_manager,
    get_session_type,
)
from nvcontrol.initramfs import rebuild_initramfs
from nvcontrol.switcher import (
    CachedConfig,
    cleanup,
    create_file,
    get_current_mode,
    graphics_mode_switcher,
)


def assert_root() -> None:
    """Exit if the script is not running with root privileges."""
    if os.geteuid() != 0:
        logging.error("This operation requires root privileges. Please re-run with sudo.")
        sys.exit(1)


def print_status_report() -> None:
    """Print comprehensive diagnostic and hardware report."""
    mode = get_current_mode()
    info = get_detailed_gpu_info()
    session = get_session_type()
    dm = get_display_manager() or "Unknown / Unsupported"

    print("========================================")
    print(f"       NVControl v{VERSION} Status")
    print("========================================")
    print(f"Current Mode:         {mode.upper()}")
    print(f"Session Type:         {session}")
    print(f"Display Manager:      {dm}")
    print("----------------------------------------")
    print(f"iGPU Vendor:          {info['igpu_vendor']}")
    print(f"iGPU Model:           {info['igpu_model']}")
    print("----------------------------------------")
    print(f"dGPU Model:           {info['nvidia_model']}")
    print(f"dGPU Architecture:    {info['nvidia_arch']}")
    print(f"dGPU PCI Bus:         {info['nvidia_pci_bus']}")
    print(f"NVIDIA Driver:        {info['nvidia_driver']}")
    print(f"Runtime Power Status: {info['power_status']}")
    print("========================================")


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser with full EnvyControl compatibility and modern extensions."""
    parser = argparse.ArgumentParser(
        prog='nvcontrol',
        description='Easy GPU switching and power management for NVIDIA Optimus laptops under Linux.'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {VERSION} (EnvyControl compatible)',
        help='Output the current version'
    )
    parser.add_argument(
        '-q', '--query',
        action='store_true',
        help='Query the current graphics mode (integrated, hybrid, or nvidia)'
    )
    parser.add_argument(
        '--status', '--info',
        dest='status',
        action='store_true',
        help='Display detailed hardware, driver version, architecture, and power status'
    )
    parser.add_argument(
        '--gui',
        action='store_true',
        help='Launch the NVControl graphical user interface'
    )
    parser.add_argument(
        '-s', '--switch',
        type=str,
        metavar='MODE',
        choices=SUPPORTED_MODES,
        help='Switch the graphics mode. Available choices: %(choices)s'
    )
    parser.add_argument(
        '--dm',
        type=str,
        metavar='DISPLAY_MANAGER',
        choices=SUPPORTED_DISPLAY_MANAGERS,
        help='Manually specify Display Manager for Nvidia mode. Choices: %(choices)s'
    )
    parser.add_argument(
        '--force-comp',
        action='store_true',
        help='Enable ForceCompositionPipeline on Nvidia mode'
    )
    parser.add_argument(
        '--coolbits',
        type=int,
        nargs='?',
        metavar='VALUE',
        const=28,
        help='Enable Coolbits on Nvidia mode. Default if specified without value: %(const)s'
    )
    parser.add_argument(
        '--rtd3',
        type=int,
        nargs='?',
        metavar='VALUE',
        choices=RTD3_MODES,
        const=2,
        help='Setup PCI-Express Runtime D3 (RTD3) Power Management on Hybrid mode. Choices: %(choices)s. Default if specified: %(const)s'
    )
    parser.add_argument(
        '--preserve-video-memory',
        action='store_true',
        help='Preserve video memory across suspend/resume and enable nvidia sleep services (recommended for Wayland)'
    )
    parser.add_argument(
        '--no-fbdev',
        action='store_true',
        help='Do not enable nvidia-drm.fbdev=1 (enabled by default for driver 545/550/560/615+)'
    )
    parser.add_argument(
        '--use-nvidia-current',
        action='store_true',
        help='Use nvidia-current instead of nvidia for kernel modules (Debian)'
    )
    parser.add_argument(
        '--reset-sddm',
        action='store_true',
        help='Restore default SDDM Xsetup file'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Revert all changes made by NVControl/EnvyControl'
    )
    parser.add_argument(
        '--cache-create',
        action='store_true',
        help='Create cache used by NVControl; only works in hybrid mode'
    )
    parser.add_argument(
        '--cache-delete',
        action='store_true',
        help='Delete cache created by NVControl'
    )
    parser.add_argument(
        '--cache-query',
        action='store_true',
        help='Show cache created by NVControl'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        help='Enable verbose debug output'
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Main CLI entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()

    if len(argv) == 0:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args(argv)

    logging.basicConfig(format='%(levelname)s: %(message)s')
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.query:
        print(get_current_mode())
        return

    if args.status:
        print_status_report()
        return

    if args.gui:
        from nvcontrol.gui import main as gui_main
        gui_main()
        return

    if args.cache_create:
        assert_root()
        cached = CachedConfig(args)
        cached.create_cache_file()
        print("Cache created successfully.")
        return

    if args.cache_delete:
        assert_root()
        CachedConfig.delete_cache_file()
        print("Cache deleted successfully.")
        return

    if args.cache_query:
        CachedConfig.show_cache_file()
        return

    if args.switch or args.reset_sddm or args.reset:
        cached_config = CachedConfig(args)
        with cached_config.adapter():
            if args.switch:
                assert_root()
                graphics_mode_switcher(
                    graphics_mode=args.switch,
                    user_display_manager=args.dm,
                    enable_force_comp=args.force_comp,
                    coolbits_value=args.coolbits,
                    rtd3_value=args.rtd3,
                    use_nvidia_current=args.use_nvidia_current,
                    preserve_video_memory=args.preserve_video_memory,
                    enable_fbdev=not args.no_fbdev,
                    enable_suspend_notifiers=True,
                    get_pci_bus_fn=cached_config.get_nvidia_gpu_pci_bus
                )
            elif args.reset_sddm:
                assert_root()
                create_file(SDDM_XSETUP_PATH, SDDM_XSETUP_CONTENT, executable=True)
                print('Operation completed successfully')
            elif args.reset:
                assert_root()
                cleanup()
                CachedConfig.delete_cache_file()
                rebuild_initramfs()
                print('Operation completed successfully')


if __name__ == '__main__':
    main()
