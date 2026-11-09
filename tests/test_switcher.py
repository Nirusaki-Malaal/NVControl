"""Unit tests for configuration generation and mode switching."""

from unittest.mock import patch
from nvcontrol.constants import (
    BLACKLIST_CONTENT,
    BLACKLIST_PATH,
    UDEV_INTEGRATED,
    UDEV_INTEGRATED_PATH,
    XORG_PATH,
    MODESET_PATH,
)
from nvcontrol.switcher import (
    build_modprobe_config,
    get_current_mode,
)


def test_build_modprobe_config_default():
    config = build_modprobe_config(driver_module='nvidia')
    assert "options nvidia-drm modeset=1 fbdev=1" in config
    assert "options nvidia NVreg_UsePageAttributeTable=1" in config
    assert "NVreg_InitializeSystemMemoryAllocations=0" in config
    assert "NVreg_UseKernelSuspendNotifiers=1" in config


def test_build_modprobe_config_preserve_memory():
    config = build_modprobe_config(
        driver_module='nvidia',
        preserve_video_memory=True
    )
    assert "NVreg_PreserveVideoMemoryAllocations=1" in config
    assert "NVreg_TemporaryFilePath=/var/tmp" in config
    assert "NVreg_InitializeSystemMemoryAllocations=0" not in config


def test_build_modprobe_config_rtd3():
    config = build_modprobe_config(
        driver_module='nvidia',
        rtd3_value=2
    )
    assert 'options nvidia "NVreg_DynamicPowerManagement=0x02"' in config


def test_build_modprobe_config_no_fbdev():
    config = build_modprobe_config(
        driver_module='nvidia',
        enable_fbdev=False
    )
    assert "options nvidia-drm modeset=1" in config
    assert "fbdev=1" not in config


def test_build_modprobe_config_nvidia_current():
    config = build_modprobe_config(
        driver_module='nvidia-current',
        rtd3_value=3
    )
    assert "options nvidia-current-drm modeset=1" in config
    assert 'options nvidia-current "NVreg_DynamicPowerManagement=0x03"' in config


def test_udev_integrated_rules():
    # Verify that add|bind|change is used to prevent suspend/resume zombie dGPU
    assert 'ACTION=="add|bind|change"' in UDEV_INTEGRATED
    assert 'ATTR{remove}="1"' in UDEV_INTEGRATED


def test_blacklist_content():
    # Verify modern module blacklisting
    assert "blacklist nouveau" in BLACKLIST_CONTENT
    assert "blacklist nova_core" in BLACKLIST_CONTENT
    assert "blacklist nova_drm" in BLACKLIST_CONTENT
    assert "blacklist nvidia" in BLACKLIST_CONTENT
    assert "blacklist nvidia_peermem" in BLACKLIST_CONTENT


def test_get_current_mode():
    with patch("os.path.exists", side_effect=lambda p: p == BLACKLIST_PATH):
        # PR #234 fix: Even if only BLACKLIST_PATH exists, mode is integrated
        assert get_current_mode() == 'integrated'

    with patch("os.path.exists", side_effect=lambda p: p in [XORG_PATH, MODESET_PATH]):
        assert get_current_mode() == 'nvidia'

    with patch("os.path.exists", return_value=False):
        assert get_current_mode() == 'hybrid'
