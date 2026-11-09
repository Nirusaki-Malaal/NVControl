"""Unit tests for NVControl GUI."""

import os
import pytest

# Ensure Qt runs offscreen for testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

try:
    from PySide6.QtWidgets import QApplication
    from nvcontrol.gui import NVControlGUI
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 is not installed")
def test_gui_initialization(qapp):
    window = NVControlGUI()
    assert "NVControl" in window.windowTitle()
    assert window.mode_group is not None
    assert len(window.mode_group.buttons()) == 3


@pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 is not installed")
def test_gui_mode_selection(qapp):
    window = NVControlGUI()
    window.show()

    window.radio_integrated.setChecked(True)
    assert window.get_selected_mode() == "integrated"
    assert not window.options_frame.isVisible()

    window.radio_hybrid.setChecked(True)
    assert window.get_selected_mode() == "hybrid"
    assert window.options_frame.isVisible()
    assert window.hybrid_opts_widget.isVisible()
    assert not window.nvidia_opts_widget.isVisible()

    window.radio_nvidia.setChecked(True)
    assert window.get_selected_mode() == "nvidia"
    assert window.options_frame.isVisible()
    assert not window.hybrid_opts_widget.isVisible()
    assert window.nvidia_opts_widget.isVisible()
