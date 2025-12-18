import liberadronecore.ui.addon_pref as addon_pref
from .base_reg import RegisterBase


class UIRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        addon_pref.register()

    @classmethod
    def unregister(cls) -> None:
        addon_pref.unregister()
