import liberadronecore.overlay.checker as checker
from .base_reg import RegisterBase


class OverlayRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        checker.register()

    @classmethod
    def unregister(cls) -> None:
        checker.unregister()
