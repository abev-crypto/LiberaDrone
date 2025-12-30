import liberadronecore.ui.addon_pref as addon_pref
import liberadronecore.ui.operators as operators
import liberadronecore.ui.liberadrone_panel as liberadrone_panel
from liberadronecore.util import view_setup
from .base_reg import RegisterBase


class UIRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        view_setup.register()
        addon_pref.register()
        operators.register()
        liberadrone_panel.register()

    @classmethod
    def unregister(cls) -> None:
        liberadrone_panel.unregister()
        operators.unregister()
        addon_pref.unregister()
        view_setup.unregister()
