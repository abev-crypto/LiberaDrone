import liberadronecore.system.update as update
from .base_reg import RegisterBase


class SystemRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        update.register()

    @classmethod
    def unregister(cls) -> None:
        update.unregister()
