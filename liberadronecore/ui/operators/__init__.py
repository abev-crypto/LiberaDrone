from .addon import LD_OT_dummy, LD_OT_install_deps
from .workspace import (
    LD_OT_setup_workspace,
    LD_OT_setup_workspace_formation,
    LD_OT_setup_workspace_led,
)
from .graph import LD_OT_show_check_graph
from .import_sheet import LD_OT_show_import_sheet


_classes = (
    LD_OT_setup_workspace,
    LD_OT_setup_workspace_formation,
    LD_OT_setup_workspace_led,
    LD_OT_show_check_graph,
    LD_OT_show_import_sheet,
)


def register():
    import bpy
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    import bpy
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
