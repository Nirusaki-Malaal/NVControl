<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/bayasdev/envycontrol/raw/main/logos/dark.png">
  <img alt="NVControl Logo" src="https://github.com/bayasdev/envycontrol/raw/main/logos/light.png" height="100px">
</picture>
<br>
<h3>Optimus Made Easy — Modernized for NVIDIA 615+ & Blackwell</h3>
</div>
<br>

# 👁‍🗨 NVControl (EnvyControl Next)

**NVControl** is a fast, modernized CLI tool for managing GPU switching and power states on NVIDIA Optimus laptops (hybrid Intel + NVIDIA or AMD + NVIDIA) under Linux.

It is the maintained and extended successor to [EnvyControl](https://github.com/bayasdev/envycontrol), engineered to support modern Linux distributions, Wayland compositors, the latest GPU architectures (**Blackwell RTX 50 Series** and **Ada Lovelace RTX 40 Series**), and the **NVIDIA 615+ driver family**.

Both `nvcontrol` and `envycontrol` CLI commands are provided for 100% drop-in compatibility.

---

### 📖 License

NVControl is free and open-source software released under the [MIT](LICENSE) license.

### ⚠️ Disclaimer

**This software is provided 'as-is' without any express or implied warranty.**  
Custom X.org configuration files may get replaced when switching to NVIDIA mode.

---

## ✨ Features & Improvements

- ⚡ **NVIDIA 615+ Driver & Open Kernel Modules Ready**: Native support for the modern `nvidia-open` driver stack and module parameters.
- 🚀 **Latest Microarchitecture Support**: Full support for **Blackwell (RTX 50-series)**, **Ada Lovelace (RTX 40-series)**, Ampere (RTX 30-series), and Turing.
- 🪟 **Wayland First-Class Support**:
  - Automatically configures `nvidia-drm.modeset=1 fbdev=1` required for smooth Wayland rendering and DRM consoles.
  - `--preserve-video-memory`: Preserves VRAM across system sleep/suspend to eliminate freezes, session crashes, and resume corruption.
- 🔋 **Zero Zombie dGPU Power Draw**:
  - Enhanced udev power rules trigger on `add|bind|change` to prevent the discrete GPU from re-enumerating into an unmanaged high-power state after ACPI suspend/resume in integrated mode.
- ⚙️ **Dynamic & Non-Interactive Initramfs Generation**:
  - Intelligently detects the active initramfs generator (`dracut`, `dracut-rebuild`, `mkinitcpio`, `limine-mkinitcpio`, `booster`, `update-initramfs`, `make-initrd`, `rpm-ostree`).
  - Runs with non-blocking execution to avoid hanging indefinitely on interactive prompts (e.g. Limine bootloader).
- 📊 **Detailed Hardware Diagnostics**: Built-in `--status` command reveals GPU models, microarchitecture family, driver version, runtime power state, display manager, and Wayland/X11 session.
- 🖥️ **Modern Desktop GUI**: Beautiful, native Qt/PySide6 graphical interface (`nvcontrol-gui` or `nvcontrol --gui`) with live diagnostics, one-click mode switching, terminal log streaming, and desktop entry.
- 🐍 **Modern Python Packaging**: Packaged via PEP 517/PEP 621 with `pyproject.toml` and Nix flake support.

---

## 📖 Graphics Modes

### 1. Integrated Mode (`-s integrated`)
- Discrete NVIDIA GPU is completely powered down via kernel udev rules to maximize battery life.
- Only the integrated Intel or AMD GPU is active.
- Re-enumeration on sleep/wake is suppressed to prevent battery drain.
- Note: External monitors directly wired to the dGPU will not display video in integrated mode.

### 2. Hybrid Mode (`-s hybrid`)
- Enables NVIDIA PRIME render offloading: run games and 3D workloads on the dGPU on-demand using `prime-run` or standard PRIME variables.
- Supports PCI-Express Runtime D3 (RTD3) Power Management:
  - `--rtd3 0`: Disabled
  - `--rtd3 1`: Coarse-grained
  - `--rtd3 2`: Fine-grained (default)
  - `--rtd3 3`: Fine-grained with video memory power-down (supported on Ada Lovelace and Blackwell)
- Optional `--preserve-video-memory` ensures stable sleep/resume under Wayland.

### 3. Nvidia Mode (`-s nvidia`)
- Discrete NVIDIA GPU is used as the primary display controller.
- Maximum performance for multi-monitor setups and dedicated desktop docks.
- Supports Coolbits overclocking (`--coolbits`) and ForceCompositionPipeline (`--force-comp`).

---

## 🖥️ Graphical User Interface (GUI)

Launch the native graphical user interface:

```bash
nvcontrol-gui
# or
nvcontrol --gui
```

The GUI offers:
- **Live System Card**: Current mode, iGPU & dGPU model, microarchitecture (Ada Lovelace, Blackwell, etc.), active driver version, and runtime power status.
- **Visual Mode Switcher**: Quick-switch between **Integrated**, **Hybrid (PRIME)**, and **Dedicated NVIDIA** modes with real-time tuning options.
- **Polkit Privilege Escalation**: Safely executes privileged operations via `pkexec` without needing to run the whole graphical interface as root.
- **Live Command Terminal**: Real-time streaming logs as `initramfs` and kernel configurations are generated.
- **One-Click Reboot Prompt**: Clean confirmation dialog to reboot once switching completes.

---

## ⚡️ Usage

```text
usage: nvcontrol [-h] [-v] [-q] [--status] [-s MODE] [--dm DISPLAY_MANAGER]
                 [--force-comp] [--coolbits [VALUE]] [--rtd3 [VALUE]]
                 [--preserve-video-memory] [--no-fbdev] [--use-nvidia-current]
                 [--reset-sddm] [--reset] [--cache-create] [--cache-delete]
                 [--cache-query] [--verbose]

options:
  -h, --help            Show this help message and exit
  -v, --version         Output the current version
  -q, --query           Query the current graphics mode
  --status, --info      Display detailed hardware, driver version, architecture, and power status
  -s MODE, --switch MODE
                        Switch graphics mode (integrated, hybrid, nvidia)
  --dm DISPLAY_MANAGER  Manually specify Display Manager (gdm, gdm3, sddm, lightdm)
  --force-comp          Enable ForceCompositionPipeline on Nvidia mode
  --coolbits [VALUE]    Enable Coolbits on Nvidia mode. Default if specified without value: 28
  --rtd3 [VALUE]        Setup RTD3 Power Management on Hybrid mode (0, 1, 2, 3). Default: 2
  --preserve-video-memory
                        Preserve video memory across suspend/resume (recommended for Wayland)
  --no-fbdev            Do not enable nvidia-drm.fbdev=1
  --use-nvidia-current  Use nvidia-current instead of nvidia for kernel modules (Debian)
  --reset-sddm          Restore default SDDM Xsetup file
  --reset               Revert all changes made by NVControl/EnvyControl
  --cache-create        Create cache used by NVControl (hybrid mode only)
  --cache-delete        Delete cache created by NVControl
  --cache-query         Show cache created by NVControl
  --verbose             Enable verbose debug output
```

---

## 💡 Examples

### Check Detailed System & GPU Status:
```bash
nvcontrol --status
```
*Example Output:*
```text
========================================
       NVControl v3.6.0 Status
========================================
Current Mode:         HYBRID
Session Type:         wayland
Display Manager:      sddm
----------------------------------------
iGPU Vendor:          Intel
iGPU Model:           Intel Corporation Alder Lake-S [UHD Graphics]
----------------------------------------
dGPU Model:           NVIDIA Corporation AD107M [GeForce RTX 4050 Max-Q / Mobile]
dGPU Architecture:    Ada Lovelace (RTX 40 Series)
dGPU PCI Bus:         PCI:1:0:0
NVIDIA Driver:        615.78.08
Runtime Power Status: active
========================================
```

### Switch to Integrated Mode (Battery Saver):
```bash
sudo nvcontrol -s integrated
```

### Switch to Hybrid Mode with RTD3 Power Management:
```bash
sudo nvcontrol -s hybrid --rtd3
```

### Switch to Hybrid Mode with Wayland Video Memory Preservation:
```bash
sudo nvcontrol -s hybrid --rtd3 2 --preserve-video-memory
```

### Switch to Dedicated NVIDIA Mode:
```bash
sudo nvcontrol -s nvidia
```

### Query Active Mode:
```bash
nvcontrol -q
```

### Reset All Configurations:
```bash
sudo nvcontrol --reset
```

*(You can also substitute `envycontrol` for `nvcontrol` in all commands.)*

---

## 📦 Installation

### From Source (pip / pyproject)
```bash
git clone https://github.com/Nirusaki-Malaal/NVControl.git
cd NVControl
sudo pip install .
```

### Using Nix Flakes
```bash
nix profile install github:Nirusaki-Malaal/NVControl
# or run directly:
nix run github:Nirusaki-Malaal/NVControl#nvcontrol -- --status
```

---

## 🤝 Upstream Acknowledgment

NVControl is based on the foundational work by [Victor Bayas](https://github.com/bayasdev) ([EnvyControl](https://github.com/bayasdev/envycontrol)) and incorporates fixes and contributions from the open-source community.
