import liberadronecore.system.update as update
import liberadronecore.tasks.transition_task as transition_task
from .base_reg import RegisterBase


class SystemRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        update.register()
        transition_task.register()

    @classmethod
    def unregister(cls) -> None:
        transition_task.unregister()
        update.unregister()
