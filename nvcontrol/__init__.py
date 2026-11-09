"""NVControl - Easy GPU switching for NVIDIA Optimus laptops under Linux."""

from nvcontrol.constants import VERSION


def main():
    """Deferred entrypoint to prevent cyclic runpy imports."""
    from nvcontrol.cli import main as _main
    return _main()


__all__ = ['main', 'VERSION']
__version__ = VERSION
