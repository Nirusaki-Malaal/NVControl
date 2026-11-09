"""Graphical User Interface for NVControl using PySide6.

Styled natively for Wayland and Noctalia / Niri environments without emojis.
"""

import logging
import os
import shutil
import subprocess
import sys
from typing import List, Optional

# Ensure native Wayland QPA platform is preferred under Wayland sessions
if "QT_QPA_PLATFORM" not in os.environ and os.environ.get("WAYLAND_DISPLAY"):
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

try:
    from PySide6.QtCore import QObject, Qt, QThread, Signal
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSpinBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False


class ProcessWorker(QThread):
    """Background worker to run privileged commands with live output streaming."""
    output_line = Signal(str)
    finished = Signal(int)

    def __init__(self, command: List[str], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.command = command
        self._process: Optional[subprocess.Popen] = None

    def run(self) -> None:
        try:
            self._process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            if self._process.stdout:
                for line in iter(self._process.stdout.readline, ''):
                    if line:
                        self.output_line.emit(line.rstrip('\r\n'))
                self._process.stdout.close()
            ret_code = self._process.wait()
            self.finished.emit(ret_code)
        except Exception as e:
            self.output_line.emit(f"Execution failed: {e}")
            self.finished.emit(1)


class NVControlGUI(QMainWindow):
    """Main window for NVControl GUI - Noctalia / Wayland edition."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NVControl - Optimus GPU Switcher")
        self.setObjectName("NVControlWindow")
        self.setMinimumSize(660, 760)
        self.resize(700, 800)
        self.worker: Optional[ProcessWorker] = None

        self._load_icon()
        self._setup_noctalia_theme()
        self._init_ui()
        self.refresh_status()

    def _load_icon(self) -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "logos", "dark.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _setup_noctalia_theme(self) -> None:
        """Apply Noctalia Material-Dark palette (Cyan / Deep Teal / Nord Navy)."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #031726;
                color: #f2f2f3;
            }
            QWidget {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Noto Sans", sans-serif;
                color: #f2f2f3;
                font-size: 13px;
            }
            QFrame#card {
                background-color: #082337;
                border: 1px solid #143d5c;
                border-radius: 10px;
                padding: 14px;
            }
            QFrame#modeCard {
                background-color: #082337;
                border: 1px solid #143d5c;
                border-radius: 10px;
                padding: 12px;
            }
            QFrame#modeCard:hover {
                border-color: #4db6fe;
                background-color: #0c2e47;
            }
            QRadioButton {
                font-weight: 600;
                font-size: 14px;
                color: #f2f2f3;
                spacing: 10px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #4db6fe;
                background-color: #4db6fe;
                border-radius: 9px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #295577;
                background-color: #061d2e;
                border-radius: 9px;
            }
            QRadioButton::indicator:unchecked:hover {
                border-color: #8dcff1;
            }
            QLabel#title {
                font-size: 19px;
                font-weight: 700;
                color: #ffffff;
                letter-spacing: 0.5px;
            }
            QLabel#badge {
                font-size: 11px;
                font-weight: 600;
                padding: 3px 9px;
                border-radius: 10px;
                background-color: #0c2b42;
                border: 1px solid #1b4b70;
                color: #8dcff1;
            }
            QLabel#statusPill {
                font-size: 12px;
                font-weight: 700;
                padding: 4px 14px;
                border-radius: 12px;
                letter-spacing: 0.8px;
            }
            QLabel#muted {
                color: #7a99ad;
                font-size: 12px;
            }
            QPushButton#primaryBtn {
                background-color: #4db6fe;
                color: #031726;
                font-weight: 700;
                font-size: 13px;
                border-radius: 8px;
                padding: 9px 24px;
                border: none;
            }
            QPushButton#primaryBtn:hover {
                background-color: #80cbfe;
            }
            QPushButton#primaryBtn:pressed {
                background-color: #3445fe;
                color: #ffffff;
            }
            QPushButton#primaryBtn:disabled {
                background-color: #09283f;
                color: #355873;
            }
            QPushButton#secondaryBtn {
                background-color: #09273d;
                color: #f2f2f3;
                font-weight: 500;
                border-radius: 8px;
                padding: 7px 16px;
                border: 1px solid #1a4566;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #0e3452;
                border-color: #4db6fe;
                color: #ffffff;
            }
            QPushButton#dangerBtn {
                background-color: #261217;
                color: #fd4663;
                font-weight: 500;
                border-radius: 8px;
                padding: 7px 16px;
                border: 1px solid #4a1c24;
            }
            QPushButton#dangerBtn:hover {
                background-color: #36171e;
                border-color: #802332;
            }
            QComboBox, QSpinBox {
                background-color: #051a2a;
                border: 1px solid #164061;
                border-radius: 6px;
                padding: 5px 10px;
                color: #f2f2f3;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #4db6fe;
            }
            QComboBox QAbstractItemView {
                background-color: #082337;
                border: 1px solid #164061;
                selection-background-color: #4db6fe;
                selection-color: #031726;
            }
            QTextEdit#terminal {
                background-color: #020f1a;
                border: 1px solid #0e304a;
                border-radius: 8px;
                font-family: "JetBrains Mono", "Fira Code", monospace;
                font-size: 12px;
                color: #8dcff1;
                padding: 8px;
            }
            QCheckBox {
                spacing: 8px;
                color: #f2f2f3;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #234f73;
                border-radius: 4px;
                background-color: #051a2a;
            }
            QCheckBox::indicator:checked {
                background-color: #4db6fe;
                border-color: #4db6fe;
            }
            QCheckBox::indicator:hover {
                border-color: #8dcff1;
            }
            QScrollBar:vertical {
                border: none;
                background: #031726;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #143d5c;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4db6fe;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header Bar
        header_layout = QHBoxLayout()
        title_label = QLabel("NVControl")
        title_label.setObjectName("title")
        version_label = QLabel("v3.6.0")
        version_label.setObjectName("badge")
        header_layout.addWidget(title_label)
        header_layout.addWidget(version_label)
        header_layout.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("secondaryBtn")
        self.refresh_btn.clicked.connect(self.refresh_status)
        header_layout.addWidget(self.refresh_btn)
        main_layout.addLayout(header_layout)

        # Scroll Area for main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        # 2. System Status Card
        self.status_card = QFrame()
        self.status_card.setObjectName("card")
        card_layout = QVBoxLayout(self.status_card)
        card_layout.setSpacing(10)

        status_header = QHBoxLayout()
        status_title = QLabel("Hardware Diagnostics")
        status_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        self.mode_pill = QLabel("INITIALIZING")
        self.mode_pill.setObjectName("statusPill")
        status_header.addWidget(status_title)
        status_header.addStretch()
        status_header.addWidget(self.mode_pill)
        card_layout.addLayout(status_header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(5)

        self.lbl_igpu = QLabel("Detecting...")
        self.lbl_dgpu = QLabel("Detecting...")
        self.lbl_arch = QLabel("Detecting...")
        self.lbl_driver = QLabel("Detecting...")
        self.lbl_power = QLabel("Detecting...")
        self.lbl_session = QLabel("Detecting...")

        grid.addWidget(self._make_label("Integrated GPU:"), 0, 0)
        grid.addWidget(self.lbl_igpu, 0, 1)
        grid.addWidget(self._make_label("NVIDIA GPU:"), 1, 0)
        grid.addWidget(self.lbl_dgpu, 1, 1)
        grid.addWidget(self._make_label("Architecture:"), 2, 0)
        grid.addWidget(self.lbl_arch, 2, 1)
        grid.addWidget(self._make_label("Driver Version:"), 3, 0)
        grid.addWidget(self.lbl_driver, 3, 1)
        grid.addWidget(self._make_label("Runtime Power State:"), 4, 0)
        grid.addWidget(self.lbl_power, 4, 1)
        grid.addWidget(self._make_label("Display Server / DM:"), 5, 0)
        grid.addWidget(self.lbl_session, 5, 1)

        card_layout.addLayout(grid)
        content_layout.addWidget(self.status_card)

        # 3. Graphics Mode Selection
        modes_label = QLabel("Graphics Mode")
        modes_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        content_layout.addWidget(modes_label)

        self.mode_group = QButtonGroup(self)

        # Integrated Card
        self.card_integrated = self._create_mode_card(
            "integrated",
            "Integrated Graphics",
            "Discrete NVIDIA GPU is powered down via kernel udev rules. Maximizes battery life and eliminates idle power consumption (suspend/resume zombie-state protected)."
        )
        content_layout.addWidget(self.card_integrated)

        # Hybrid Card
        self.card_hybrid = self._create_mode_card(
            "hybrid",
            "Hybrid Graphics (PRIME Offload)",
            "Integrated GPU drives internal and external displays. Discrete GPU wakes up on-demand for games and 3D workloads."
        )
        content_layout.addWidget(self.card_hybrid)

        # Nvidia Card
        self.card_nvidia = self._create_mode_card(
            "nvidia",
            "Dedicated NVIDIA Graphics",
            "NVIDIA GPU directly drives displays. Provides maximum graphics performance and dedicated multi-monitor output."
        )
        content_layout.addWidget(self.card_nvidia)

        # 4. Mode Options Box (Dynamic)
        self.options_frame = QFrame()
        self.options_frame.setObjectName("card")
        opt_layout = QVBoxLayout(self.options_frame)
        opt_layout.setSpacing(10)

        opt_title = QLabel("Power and Tuning Options")
        opt_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        opt_layout.addWidget(opt_title)

        # Hybrid options
        self.hybrid_opts_widget = QWidget()
        h_layout = QVBoxLayout(self.hybrid_opts_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        rtd3_row = QHBoxLayout()
        self.chk_rtd3 = QCheckBox("Enable PCI-Express Runtime D3 (RTD3) Power Management")
        self.chk_rtd3.setChecked(True)
        self.cmb_rtd3 = QComboBox()
        self.cmb_rtd3.addItem("Mode 2: Fine-Grained (Recommended)", 2)
        self.cmb_rtd3.addItem("Mode 3: Fine + Video Memory Sleep (Ada/Blackwell)", 3)
        self.cmb_rtd3.addItem("Mode 1: Coarse-Grained", 1)
        self.cmb_rtd3.addItem("Mode 0: Disabled", 0)
        rtd3_row.addWidget(self.chk_rtd3)
        rtd3_row.addWidget(self.cmb_rtd3)
        h_layout.addLayout(rtd3_row)

        self.chk_preserve_mem = QCheckBox("Preserve Video Memory across Suspend/Resume (Recommended for Wayland)")
        self.chk_preserve_mem.setChecked(True)
        h_layout.addWidget(self.chk_preserve_mem)

        opt_layout.addWidget(self.hybrid_opts_widget)

        # Nvidia options
        self.nvidia_opts_widget = QWidget()
        n_layout = QVBoxLayout(self.nvidia_opts_widget)
        n_layout.setContentsMargins(0, 0, 0, 0)
        n_layout.setSpacing(8)

        self.chk_force_comp = QCheckBox("Enable ForceCompositionPipeline (Fixes screen tearing)")
        n_layout.addWidget(self.chk_force_comp)

        coolbits_row = QHBoxLayout()
        self.chk_coolbits = QCheckBox("Enable Coolbits (GPU Overclocking / Fan Control)")
        self.spin_coolbits = QSpinBox()
        self.spin_coolbits.setRange(1, 31)
        self.spin_coolbits.setValue(28)
        self.spin_coolbits.setEnabled(False)
        self.chk_coolbits.toggled.connect(self.spin_coolbits.setEnabled)
        coolbits_row.addWidget(self.chk_coolbits)
        coolbits_row.addWidget(self.spin_coolbits)
        coolbits_row.addStretch()
        n_layout.addLayout(coolbits_row)

        dm_row = QHBoxLayout()
        dm_lbl = QLabel("Display Manager:")
        self.cmb_dm = QComboBox()
        self.cmb_dm.addItem("Auto-detect", None)
        self.cmb_dm.addItem("sddm", "sddm")
        self.cmb_dm.addItem("gdm / gdm3", "gdm")
        self.cmb_dm.addItem("lightdm", "lightdm")
        dm_row.addWidget(dm_lbl)
        dm_row.addWidget(self.cmb_dm)
        dm_row.addStretch()
        n_layout.addLayout(dm_row)

        opt_layout.addWidget(self.nvidia_opts_widget)

        content_layout.addWidget(self.options_frame)

        # Connect radio button changes to update options visibility
        self.radio_integrated.toggled.connect(self._on_mode_toggled)
        self.radio_hybrid.toggled.connect(self._on_mode_toggled)
        self.radio_nvidia.toggled.connect(self._on_mode_toggled)

        # 5. Output Terminal Log
        content_layout.addWidget(QLabel("Process Log:"))
        self.log_view = QTextEdit()
        self.log_view.setObjectName("terminal")
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(120)
        content_layout.addWidget(self.log_view)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # 6. Action Bar
        action_layout = QHBoxLayout()
        self.btn_reset = QPushButton("Reset Defaults")
        self.btn_reset.setObjectName("dangerBtn")
        self.btn_reset.clicked.connect(self.reset_system)
        action_layout.addWidget(self.btn_reset)

        action_layout.addStretch()

        self.btn_apply = QPushButton("Apply and Switch Mode")
        self.btn_apply.setObjectName("primaryBtn")
        self.btn_apply.clicked.connect(self.apply_switch)
        action_layout.addWidget(self.btn_apply)

        main_layout.addLayout(action_layout)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("muted")
        return lbl

    def _create_mode_card(self, mode_id: str, title: str, description: str) -> QFrame:
        card = QFrame()
        card.setObjectName("modeCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        radio = QRadioButton(title)
        radio.setProperty("mode_id", mode_id)
        layout.addWidget(radio)

        desc = QLabel(description)
        desc.setObjectName("muted")
        desc.setWordWrap(True)
        desc.setContentsMargins(28, 0, 0, 0)
        layout.addWidget(desc)

        self.mode_group.addButton(radio)
        setattr(self, f"radio_{mode_id}", radio)
        return card

    def _on_mode_toggled(self) -> None:
        if self.radio_integrated.isChecked():
            self.options_frame.setVisible(False)
        elif self.radio_hybrid.isChecked():
            self.options_frame.setVisible(True)
            self.hybrid_opts_widget.setVisible(True)
            self.nvidia_opts_widget.setVisible(False)
        elif self.radio_nvidia.isChecked():
            self.options_frame.setVisible(True)
            self.hybrid_opts_widget.setVisible(False)
            self.nvidia_opts_widget.setVisible(True)

    def refresh_status(self) -> None:
        from nvcontrol.switcher import get_current_mode
        from nvcontrol.gpu import get_detailed_gpu_info, get_session_type, get_display_manager

        mode = get_current_mode()
        info = get_detailed_gpu_info()
        session = get_session_type()
        dm = get_display_manager() or "Unknown"

        # Update mode pill with Noctalia palette styling
        self.mode_pill.setText(mode.upper())
        if mode == 'integrated':
            self.mode_pill.setStyleSheet("background-color: #0c3628; border: 1px solid #1e694d; color: #4ade80;")
            self.radio_integrated.setChecked(True)
        elif mode == 'hybrid':
            self.mode_pill.setStyleSheet("background-color: #092c44; border: 1px solid #195b8a; color: #4db6fe;")
            self.radio_hybrid.setChecked(True)
        elif mode == 'nvidia':
            self.mode_pill.setStyleSheet("background-color: #3b1d1d; border: 1px solid #6e2e2e; color: #ff8a7a;")
            self.radio_nvidia.setChecked(True)

        self.lbl_igpu.setText(f"{info['igpu_vendor']} - {info['igpu_model']}")
        self.lbl_dgpu.setText(info['nvidia_model'])
        self.lbl_arch.setText(info['nvidia_arch'])
        self.lbl_driver.setText(info['nvidia_driver'])
        self.lbl_power.setText(info['power_status'])
        self.lbl_session.setText(f"{session} ({dm})")

        self.log_view.append(f"Refreshed status: Current Mode is {mode.upper()}.")

    def get_selected_mode(self) -> str:
        for radio in self.mode_group.buttons():
            if radio.isChecked():
                return radio.property("mode_id")
        return "hybrid"

    def apply_switch(self) -> None:
        mode = self.get_selected_mode()
        args = ["-s", mode]

        if mode == "hybrid":
            if self.chk_rtd3.isChecked():
                rtd3_val = self.cmb_rtd3.currentData()
                args.extend(["--rtd3", str(rtd3_val)])
            if self.chk_preserve_mem.isChecked():
                args.append("--preserve-video-memory")
        elif mode == "nvidia":
            if self.chk_force_comp.isChecked():
                args.append("--force-comp")
            if self.chk_coolbits.isChecked():
                args.extend(["--coolbits", str(self.spin_coolbits.value())])
            dm_override = self.cmb_dm.currentData()
            if dm_override:
                args.extend(["--dm", dm_override])

        self.run_elevated_command(args)

    def reset_system(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Confirm Reset",
            "This will revert all configuration files, udev rules, and modprobe parameters generated by NVControl/EnvyControl.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.run_elevated_command(["--reset"])

    def run_elevated_command(self, args: List[str]) -> None:
        # Ensure that when running under pkexec/sudo as root, python can reliably import nvcontrol
        package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bootstrap = (
            "import sys; "
            f"sys.path.insert(0, {repr(package_root)}); "
            "from nvcontrol.cli import main; "
            "sys.exit(main())"
        )
        cli_cmd = [sys.executable, "-c", bootstrap, *args]

        if os.geteuid() == 0:
            full_cmd = cli_cmd
        elif shutil.which("pkexec"):
            full_cmd = ["pkexec", *cli_cmd]
        elif shutil.which("sudo"):
            full_cmd = ["sudo", *cli_cmd]
        else:
            QMessageBox.critical(self, "Error", "Neither pkexec nor sudo is available to acquire root privileges.")
            return

        self.btn_apply.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.log_view.clear()
        self.log_view.append(f"Executing: {' '.join(full_cmd)}\n")

        self.worker = ProcessWorker(full_cmd)
        self.worker.output_line.connect(self.log_view.append)
        self.worker.finished.connect(self._on_command_finished)
        self.worker.start()

    def _on_command_finished(self, exit_code: int) -> None:
        self.btn_apply.setEnabled(True)
        self.btn_reset.setEnabled(True)
        self.refresh_btn.setEnabled(True)

        if exit_code == 0:
            self.log_view.append("\nOperation completed successfully.")
            self.refresh_status()

            reboot_box = QMessageBox.question(
                self,
                "Reboot Recommended",
                "Mode switch completed successfully!\n\nA system reboot is required for GPU kernel modules and udev power rules to take full effect.\n\nWould you like to reboot now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reboot_box == QMessageBox.Yes:
                subprocess.run(["systemctl", "reboot"])
        else:
            self.log_view.append(f"\nOperation failed with exit code {exit_code}.")
            QMessageBox.warning(self, "Operation Failed", f"Command exited with code {exit_code}. Check the output log for details.")


def main() -> None:
    """Launch the native Wayland Noctalia GUI application."""
    if not PYSIDE6_AVAILABLE:
        print("ERROR: PySide6 is required to run the NVControl GUI.", file=sys.stderr)
        print("Please install PySide6 via your system package manager or 'pip install PySide6'.", file=sys.stderr)
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("nvcontrol")
    app.setDesktopFileName("nvcontrol")
    window = NVControlGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
