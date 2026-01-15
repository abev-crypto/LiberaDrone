import liberadronecore.ui.addon_pref as addon_pref
import liberadronecore.ui.fn_parse_ui as fn_parse_ui
import liberadronecore.ui.liberadrone_panel as liberadrone_panel
from .base_reg import RegisterBase


class UIRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        addon_pref.register()
        liberadrone_panel.register()

    @classmethod
    def unregister(cls) -> None:
        liberadrone_panel.unregister()
        addon_pref.unregister()
