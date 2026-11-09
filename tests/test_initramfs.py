"""Unit tests for initramfs tool detection and execution."""

from unittest.mock import patch
from nvcontrol.initramfs import detect_initramfs_command, rebuild_initramfs


def test_detect_initramfs_ostree():
    with patch("os.path.exists", side_effect=lambda p: p == "/ostree"), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/bin/rpm-ostree" if cmd == "rpm-ostree" else None):
        cmd = detect_initramfs_command()
        assert cmd == ['rpm-ostree', 'initramfs', '--enable', '--arg=--force']


def test_detect_initramfs_debian():
    with patch("os.path.exists", return_value=False), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/sbin/update-initramfs" if cmd == "update-initramfs" else None):
        cmd = detect_initramfs_command()
        assert cmd == ['update-initramfs', '-u', '-k', 'all']


def test_detect_initramfs_dracut_rebuild():
    with patch("os.path.exists", return_value=False), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/bin/dracut-rebuild" if cmd == "dracut-rebuild" else None):
        cmd = detect_initramfs_command()
        assert cmd == ['dracut-rebuild']


def test_detect_initramfs_dracut():
    with patch("os.path.exists", return_value=False), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/bin/dracut" if cmd == "dracut" else None):
        cmd = detect_initramfs_command()
        assert cmd == ['dracut', '--force', '--regenerate-all']


def test_detect_initramfs_limine():
    with patch("os.path.exists", return_value=False), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/bin/limine-mkinitcpio" if cmd == "limine-mkinitcpio" else None):
        cmd = detect_initramfs_command()
        assert cmd == ['limine-mkinitcpio']


def test_detect_initramfs_mkinitcpio():
    with patch("os.path.exists", return_value=False), \
         patch("shutil.which", side_effect=lambda cmd: "/usr/bin/mkinitcpio" if cmd == "mkinitcpio" else None):
        cmd = detect_initramfs_command()
        assert cmd == ['mkinitcpio', '-P']


def test_rebuild_initramfs_empty():
    with patch("nvcontrol.initramfs.detect_initramfs_command", return_value=[]):
        assert rebuild_initramfs() is False
