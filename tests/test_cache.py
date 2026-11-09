"""Unit tests for cache configuration adapter."""

import os
from unittest.mock import MagicMock, patch
import pytest
from nvcontrol.switcher import CachedConfig


def test_cached_config_read_write(tmp_path):
    test_cache = str(tmp_path / "cache.json")
    with patch("nvcontrol.switcher.CachedConfig.get_active_cache_path", return_value=test_cache):
        args = MagicMock()
        args.switch = 'nvidia'
        cfg = CachedConfig(args)
        cfg.current_mode = 'hybrid'

        with patch("nvcontrol.switcher.get_nvidia_gpu_pci_bus", return_value="PCI:1:0:0"):
            cfg.create_cache_file()

        assert os.path.exists(test_cache)
        assert cfg.get_nvidia_gpu_pci_bus() == "PCI:1:0:0"

        # Read back in a fresh instance
        cfg2 = CachedConfig(args)
        cfg2.read_cache_file()
        assert cfg2.get_nvidia_gpu_pci_bus() == "PCI:1:0:0"


def test_cached_config_adapter_only_when_leaving_hybrid(tmp_path):
    # Test PR #234 fix: when switching TO hybrid, do not create cache
    test_cache = str(tmp_path / "cache.json")
    with patch("nvcontrol.switcher.CachedConfig.get_active_cache_path", return_value=test_cache):
        args = MagicMock()
        args.switch = 'hybrid'
        cfg = CachedConfig(args)
        cfg.current_mode = 'hybrid'

        with patch.object(cfg, "create_cache_file") as mock_create:
            with cfg.adapter():
                pass
            mock_create.assert_not_called()
