"""Unit tests for GPU and hardware detection functions."""

import pytest
from nvcontrol.gpu import (
    detect_nvidia_architecture,
    get_igpu_vendor,
    get_nvidia_gpu_pci_bus,
    parse_pci_bus_id,
)

SAMPLE_LSPCI_INTEL_NVIDIA = """00:00.0 Host bridge: Intel Corporation 12th Gen Core Processor Host Bridge/DRAM Registers (rev 02)
00:02.0 VGA compatible controller: Intel Corporation Alder Lake-S [UHD Graphics] (rev 0c)
01:00.0 VGA compatible controller: NVIDIA Corporation AD107M [GeForce RTX 4050 Max-Q / Mobile] (rev a1)
01:00.1 Audio device: NVIDIA Corporation Device 22be (rev a1)
"""

SAMPLE_LSPCI_AMD_NVIDIA = """00:00.0 Host bridge: Advanced Micro Devices, Inc. [AMD] Renoir/Cezanne Root Complex
01:00.0 3D controller: NVIDIA Corporation GA106M [GeForce RTX 3060 Mobile / Max-Q] (rev a1)
05:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Cezanne [Radeon Vega Series / Radeon Vega Mobile Series] (rev c5)
"""

SAMPLE_LSPCI_BLACKWELL = """00:02.0 VGA compatible controller: Intel Corporation Arrow Lake-H [UHD Graphics] (rev 01)
01:00.0 VGA compatible controller: NVIDIA Corporation GB206M [GeForce RTX 5070 Mobile] (rev a1)
"""


def test_parse_pci_bus_id():
    assert parse_pci_bus_id("01:00.0") == "PCI:1:0:0"
    assert parse_pci_bus_id("0000:01:00.0") == "PCI:1:0:0"
    assert parse_pci_bus_id("0a:01.2") == "PCI:10:1:2"
    assert parse_pci_bus_id("0000:10:00.0") == "PCI:16:0:0"


def test_get_nvidia_gpu_pci_bus():
    bus_intel = get_nvidia_gpu_pci_bus(SAMPLE_LSPCI_INTEL_NVIDIA)
    assert bus_intel == "PCI:1:0:0"

    bus_amd = get_nvidia_gpu_pci_bus(SAMPLE_LSPCI_AMD_NVIDIA)
    assert bus_amd == "PCI:1:0:0"

    bus_blackwell = get_nvidia_gpu_pci_bus(SAMPLE_LSPCI_BLACKWELL)
    assert bus_blackwell == "PCI:1:0:0"


def test_get_nvidia_gpu_pci_bus_missing():
    with pytest.raises(RuntimeError):
        get_nvidia_gpu_pci_bus("00:02.0 VGA compatible controller: Intel Corporation UHD Graphics\n")


def test_detect_nvidia_architecture():
    assert detect_nvidia_architecture("AD107M [GeForce RTX 4050 Max-Q / Mobile]") == "Ada Lovelace (RTX 40 Series)"
    assert detect_nvidia_architecture("GB206M [GeForce RTX 5070 Mobile]") == "Blackwell (RTX 50 Series)"
    assert detect_nvidia_architecture("GA106M [GeForce RTX 3060 Mobile / Max-Q]") == "Ampere (RTX 30 Series)"
    assert detect_nvidia_architecture("TU116 [GeForce GTX 1660 Ti]") == "Turing (RTX 20 / GTX 16 Series)"
    assert detect_nvidia_architecture("GP106 [GeForce GTX 1060 6GB]") == "Pascal (GTX 10 Series)"


def test_get_igpu_vendor():
    assert get_igpu_vendor(SAMPLE_LSPCI_INTEL_NVIDIA) == "intel"
    assert get_igpu_vendor(SAMPLE_LSPCI_AMD_NVIDIA) == "amd"
    assert get_igpu_vendor("01:00.0 VGA compatible controller: NVIDIA Corporation AD107M\n") is None
