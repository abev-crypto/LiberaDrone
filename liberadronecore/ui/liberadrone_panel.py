import bpy
from liberadronecore.overlay import checker


PREVIEW_OBJ_NAME = "PreviewDrone"
PREVIEW_MOD_NAME = "PreviewDroneGN"
PROXY_OBJ_NAME = "ProxyPoints"
PROXY_MOD_NAME = "ProxyPointsGN"


def _get_nodes_modifier(obj_name: str, mod_name: str) -> bpy.types.Modifier | None:
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        return None
    mod = obj.modifiers.get(mod_name)
    if mod and mod.type == 'NODES':
        return mod
    for m in obj.modifiers:
        if m.type == 'NODES':
            return m
    return None


def _find_input_identifier(mod: bpy.types.Modifier, name: str) -> str | None:
    node_group = getattr(mod, "node_group", None)
    if node_group is None:
        return None
    iface = getattr(node_group, "interface", None)
    if iface is not None:
        for sock in iface.items_tree:
            if getattr(sock, "in_out", None) != 'INPUT':
                continue
            if getattr(sock, "name", None) == name:
                return getattr(sock, "identifier", None)
    for inp in getattr(node_group, "inputs", []):
        if inp.name == name:
            return inp.identifier
    return None


def _get_input_default(mod: bpy.types.Modifier, name: str, default):
    node_group = getattr(mod, "node_group", None)
    if node_group is None:
        return default
    iface = getattr(node_group, "interface", None)
    if iface is not None:
        for sock in iface.items_tree:
            if getattr(sock, "in_out", None) != 'INPUT':
                continue
            if getattr(sock, "name", None) == name:
                return getattr(sock, "default_value", default)
    for inp in getattr(node_group, "inputs", []):
        if inp.name == name:
            return getattr(inp, "default_value", default)
    return default


def _get_gn_input_value(obj_name: str, mod_name: str, socket_name: str, default):
    mod = _get_nodes_modifier(obj_name, mod_name)
    if mod is None:
        return default
    identifier = _find_input_identifier(mod, socket_name)
    if identifier and identifier in mod:
        return mod[identifier]
    if socket_name in mod:
        return mod[socket_name]
    return _get_input_default(mod, socket_name, default)


def _set_gn_input_value(obj_name: str, mod_name: str, socket_name: str, value) -> None:
    mod = _get_nodes_modifier(obj_name, mod_name)
    if mod is None:
        return
    identifier = _find_input_identifier(mod, socket_name)
    if identifier:
        try:
            mod[identifier] = value
            return
        except Exception:
            pass
    try:
        mod[socket_name] = value
    except Exception:
        pass
    obj = bpy.data.objects.get(obj_name)
    if obj is not None:
        data = getattr(obj, "data", None)
        if data is not None:
            data.update()
            data.update_tag()
        obj.update_tag()


def _get_preview_show_ring(self):
    return bool(_get_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "ShowRing", False))


def _set_preview_show_ring(self, value):
    _set_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "ShowRing", bool(value))


def _get_proxy_max_speed_up(self):
    return float(_get_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Max Speed Up", 0.0))


def _set_proxy_max_speed_up(self, value):
    _set_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Max Speed Up", float(value))


def _get_proxy_max_speed_down(self):
    return float(_get_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Max Speed Down", 0.0))


def _set_proxy_max_speed_down(self, value):
    _set_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Max Speed Down", float(value))


def _get_proxy_max_speed_horiz(self):
    return float(_get_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Max Speed Horiz", 0.0))


def _set_proxy_max_speed_horiz(self, value):
    _set_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Max Speed Horiz", float(value))


def _get_proxy_max_acc_vert(self):
    return float(_get_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Max Acc", 0.0))


def _set_proxy_max_acc_vert(self, value):
    value = float(value)
    _set_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Max Acc", value)


def _get_proxy_min_distance(self):
    return float(_get_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Min Distance", 0.0))


def _set_proxy_min_distance(self, value):
    _set_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "Min Distance", float(value))


def _get_proxy_skip_check(self):
    return bool(_get_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "SkipCheck", False))


def _set_proxy_skip_check(self, value):
    _set_gn_input_value(PROXY_OBJ_NAME, PROXY_MOD_NAME, "SkipCheck", bool(value))


def _get_checker_enabled(self):
    return checker.is_enabled()


def _set_checker_enabled(self, value):
    checker.set_enabled(bool(value))


class LD_PT_libera_panel(bpy.types.Panel):
    bl_label = "LiberaDrone"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LiberaDrone"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="PreviewDrone")
        if _get_nodes_modifier(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME) is None:
            box.label(text="PreviewDroneGN not found", icon='ERROR')
        box.prop(scene, "ld_preview_show_ring", text="ShowRing")

        box = layout.box()
        box.label(text="ProxyPoints")
        if _get_nodes_modifier(PROXY_OBJ_NAME, PROXY_MOD_NAME) is None:
            box.label(text="ProxyPointsGN not found", icon='ERROR')
        col = box.column(align=True)
        col.prop(scene, "ld_limit_profile", text="Limit Profile")
        col.prop(scene, "ld_proxy_max_speed_up", text="MaxSpeedUp")
        col.prop(scene, "ld_proxy_max_speed_down", text="MaxSpeedDown")
        col.prop(scene, "ld_proxy_max_speed_horiz", text="MaxSpeedHoriz")
        col.prop(scene, "ld_proxy_max_acc_vert", text="MaxAcc")
        col.prop(scene, "ld_proxy_min_distance", text="MinDistance")
        col.prop(scene, "ld_proxy_skip_check", text="SkipCheck")
        col.separator()
        col.prop(scene, "ld_checker_range_enabled", text="Range Check")
        col.prop(scene, "ld_checker_range_object", text="Range Object")
        col.prop(scene, "ld_checker_range_width", text="Range Width")
        col.prop(scene, "ld_checker_range_height", text="Range Height")
        col.prop(scene, "ld_checker_range_depth", text="Range Depth")

        box = layout.box()
        box.label(text="Overlay")
        box.prop(scene, "ld_checker_enabled", text="Show Checker")
        col = box.column(align=True)
        col.prop(scene, "ld_checker_show_speed", text="Speed")
        col.prop(scene, "ld_checker_show_acc", text="Acc")
        col.prop(scene, "ld_checker_show_distance", text="Distance")
        col.prop(scene, "ld_checker_range_enabled", text="Range")
        col.prop(scene, "ld_checker_size", text="Checker Size")

        box = layout.box()
        box.label(text="Workspace")
        row = box.row(align=True)
        row.operator("liberadrone.setup_workspace_formation", text="FormationNodeWindow")
        row.operator("liberadrone.setup_workspace_led", text="LEDEffectNodeWindow")


classes = (
    LD_PT_libera_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.ld_preview_show_ring = bpy.props.BoolProperty(
        name="ShowRing",
        get=_get_preview_show_ring,
        set=_set_preview_show_ring,
    )
    bpy.types.Scene.ld_limit_profile = bpy.props.EnumProperty(
        name="Limit Profile",
        items=(
            ("MODEL_X", "MODEL-X", "Default limits"),
            ("CUSTOM", "Custom", "Custom limits"),
        ),
        default="MODEL_X",
    )
    bpy.types.Scene.ld_proxy_max_speed_up = bpy.props.FloatProperty(
        name="MaxSpeedUp",
        get=_get_proxy_max_speed_up,
        set=_set_proxy_max_speed_up,
    )
    bpy.types.Scene.ld_proxy_max_speed_down = bpy.props.FloatProperty(
        name="MaxSpeedDown",
        get=_get_proxy_max_speed_down,
        set=_set_proxy_max_speed_down,
    )
    bpy.types.Scene.ld_proxy_max_speed_horiz = bpy.props.FloatProperty(
        name="MaxSpeedHoriz",
        get=_get_proxy_max_speed_horiz,
        set=_set_proxy_max_speed_horiz,
    )
    bpy.types.Scene.ld_proxy_max_acc_vert = bpy.props.FloatProperty(
        name="MaxAcc",
        get=_get_proxy_max_acc_vert,
        set=_set_proxy_max_acc_vert,
    )
    bpy.types.Scene.ld_proxy_min_distance = bpy.props.FloatProperty(
        name="MinDistance",
        get=_get_proxy_min_distance,
        set=_set_proxy_min_distance,
    )
    bpy.types.Scene.ld_proxy_skip_check = bpy.props.BoolProperty(
        name="SkipCheck",
        get=_get_proxy_skip_check,
        set=_set_proxy_skip_check,
    )
    bpy.types.Scene.ld_checker_enabled = bpy.props.BoolProperty(
        name="Show Checker",
        get=_get_checker_enabled,
        set=_set_checker_enabled,
    )
    bpy.types.Scene.ld_checker_size = bpy.props.FloatProperty(
        name="Checker Size",
        default=6.0,
        min=1.0,
    )
    bpy.types.Scene.ld_checker_show_speed = bpy.props.BoolProperty(
        name="Speed",
        default=True,
    )
    bpy.types.Scene.ld_checker_show_acc = bpy.props.BoolProperty(
        name="Acc",
        default=True,
    )
    bpy.types.Scene.ld_checker_show_distance = bpy.props.BoolProperty(
        name="Distance",
        default=True,
    )
    bpy.types.Scene.ld_checker_range_enabled = bpy.props.BoolProperty(
        name="Range",
        default=True,
    )
    bpy.types.Scene.ld_checker_range_object = bpy.props.PointerProperty(
        name="Range Object",
        type=bpy.types.Object,
    )
    bpy.types.Scene.ld_checker_range_width = bpy.props.FloatProperty(
        name="Range Width",
        default=0.0,
        min=0.0,
    )
    bpy.types.Scene.ld_checker_range_height = bpy.props.FloatProperty(
        name="Range Height",
        default=0.0,
        min=0.0,
    )
    bpy.types.Scene.ld_checker_range_depth = bpy.props.FloatProperty(
        name="Range Depth",
        default=0.0,
        min=0.0,
    )


def unregister():
    if hasattr(bpy.types.Scene, "ld_limit_profile"):
        del bpy.types.Scene.ld_limit_profile
    if hasattr(bpy.types.Scene, "ld_checker_range_enabled"):
        del bpy.types.Scene.ld_checker_range_enabled
    if hasattr(bpy.types.Scene, "ld_checker_show_distance"):
        del bpy.types.Scene.ld_checker_show_distance
    if hasattr(bpy.types.Scene, "ld_checker_show_acc"):
        del bpy.types.Scene.ld_checker_show_acc
    if hasattr(bpy.types.Scene, "ld_checker_show_speed"):
        del bpy.types.Scene.ld_checker_show_speed
    if hasattr(bpy.types.Scene, "ld_checker_range_width"):
        del bpy.types.Scene.ld_checker_range_width
    if hasattr(bpy.types.Scene, "ld_checker_range_height"):
        del bpy.types.Scene.ld_checker_range_height
    if hasattr(bpy.types.Scene, "ld_checker_range_depth"):
        del bpy.types.Scene.ld_checker_range_depth
    if hasattr(bpy.types.Scene, "ld_checker_range_object"):
        del bpy.types.Scene.ld_checker_range_object
    if hasattr(bpy.types.Scene, "ld_checker_size"):
        del bpy.types.Scene.ld_checker_size
    if hasattr(bpy.types.Scene, "ld_checker_enabled"):
        del bpy.types.Scene.ld_checker_enabled
    if hasattr(bpy.types.Scene, "ld_proxy_skip_check"):
        del bpy.types.Scene.ld_proxy_skip_check
    if hasattr(bpy.types.Scene, "ld_proxy_min_distance"):
        del bpy.types.Scene.ld_proxy_min_distance
    if hasattr(bpy.types.Scene, "ld_proxy_max_acc_vert"):
        del bpy.types.Scene.ld_proxy_max_acc_vert
    if hasattr(bpy.types.Scene, "ld_proxy_max_speed_horiz"):
        del bpy.types.Scene.ld_proxy_max_speed_horiz
    if hasattr(bpy.types.Scene, "ld_proxy_max_speed_down"):
        del bpy.types.Scene.ld_proxy_max_speed_down
    if hasattr(bpy.types.Scene, "ld_proxy_max_speed_up"):
        del bpy.types.Scene.ld_proxy_max_speed_up
    if hasattr(bpy.types.Scene, "ld_preview_show_ring"):
        del bpy.types.Scene.ld_preview_show_ring

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
