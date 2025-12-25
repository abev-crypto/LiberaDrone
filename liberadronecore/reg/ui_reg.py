import liberadronecore.ui.addon_pref as addon_pref
import liberadronecore.ui.liberadrone_operators as liberadrone_operators
import liberadronecore.ui.liberadrone_panel as liberadrone_panel
from .base_reg import RegisterBase


class UIRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        addon_pref.register()
        liberadrone_operators.register()
        liberadrone_panel.register()

    @classmethod
    def unregister(cls) -> None:
        liberadrone_panel.unregister()
        liberadrone_operators.unregister()
        addon_pref.unregister()
