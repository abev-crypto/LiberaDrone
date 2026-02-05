import bpy
from liberadronecore.overlay import checker
from liberadronecore.system import sence_setup


PREVIEW_OBJ_NAME = "PreviewDrone"
PREVIEW_MOD_NAME = "PreviewDroneGN"
RANGE_OBJ_NAME = "RangeObject"


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
        mod[identifier] = value
        return
    mod[socket_name] = value
    obj = bpy.data.objects.get(obj_name)
    if obj is not None:
        data = getattr(obj, "data", None)
        if data is not None:
            data.update()
            data.update_tag()
        obj.update_tag()


def _touch_preview_object() -> None:
    obj = bpy.data.objects.get(PREVIEW_OBJ_NAME)
    if obj is None:
        return
    obj.update_tag()
    view_layer = getattr(bpy.context, "view_layer", None)
    if view_layer is not None:
        view_layer.update()


def _get_preview_show_ring(self):
    return bool(_get_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "ShowRing", False))


def _set_preview_show_ring(self, value):
    _set_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "ShowRing", bool(value))
    _touch_preview_object()


def _get_preview_scale(self):
    return float(_get_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "Scale", 0.4))


def _set_preview_scale(self, value):
    _set_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "Scale", float(value))
    _touch_preview_object()


def _get_preview_vertex_alpha_mask(self):
    mat = _get_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "Material", None)
    if isinstance(mat, bpy.types.Material):
        return mat.name == sence_setup.MAT_NAME_MASK
    return False


def _set_preview_vertex_alpha_mask(self, value):
    use_mask = bool(value)
    mat = sence_setup.get_or_create_emission_attr_material(
        sence_setup.MAT_NAME_MASK if use_mask else sence_setup.MAT_NAME,
        sence_setup.ATTR_NAME,
        image_name=sence_setup.IMG_CIRCLE_NAME,
        vertex_alpha_mask=use_mask,
    )
    ring_mat = sence_setup.get_or_create_emission_attr_material(
        sence_setup.MAT_RING_NAME_MASK if use_mask else sence_setup.MAT_RING_NAME,
        sence_setup.ATTR_NAME,
        image_name=sence_setup.IMG_RING_NAME,
        vertex_alpha_mask=use_mask,
    )
    _set_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "Material", mat)
    _set_gn_input_value(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME, "CircleMat", ring_mat)
    _touch_preview_object()

def _update_range_mesh(mesh, width: float, height: float, depth: float) -> None:
    half_w = width * 0.5
    half_d = depth * 0.5
    verts = [
        (-half_w, -half_d, 0.0),
        (half_w, -half_d, 0.0),
        (half_w, half_d, 0.0),
        (-half_w, half_d, 0.0),
        (-half_w, -half_d, height),
        (half_w, -half_d, height),
        (half_w, half_d, height),
        (-half_w, half_d, height),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    mesh.clear_geometry()
    mesh.from_pydata(verts, [], faces)
    mesh.update()


def _get_checker_enabled(self):
    return checker.is_enabled()


def _set_checker_enabled(self, value):
    checker.set_enabled(bool(value))


def _apply_limit_profile(scene, profile: str) -> None:
    if profile == "MODEL_X":
        scene.ld_proxy_max_speed_up = 4.0
        scene.ld_proxy_max_speed_down = 3.0
        scene.ld_proxy_max_speed_horiz = 5.0
        scene.ld_proxy_max_acc_vert = 3.0
        scene.ld_proxy_min_distance = 1.5


def _update_limit_profile(self, context):
    _apply_limit_profile(self, getattr(self, "ld_limit_profile", ""))


class LD_PT_libera_panel_base(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LiberaDrone"


class LD_PT_libera_panel_preview(LD_PT_libera_panel_base):
    bl_label = "PreviewDrone"
    bl_idname = "LD_PT_libera_panel_preview"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if _get_nodes_modifier(PREVIEW_OBJ_NAME, PREVIEW_MOD_NAME) is None:
            layout.label(text="PreviewDroneGN not found", icon='ERROR')
        col = layout.column(align=True)
        col.prop(scene, "ld_preview_show_ring", text="ShowRing")
        col.prop(scene, "ld_preview_vertex_alpha_mask", text="Vertex Alpha Mask")
        col.prop(scene, "ld_preview_scale", text="Scale")


class LD_PT_libera_panel_errorcheck(LD_PT_libera_panel_base):
    bl_label = "ErrorCheck"
    bl_idname = "LD_PT_libera_panel_errorcheck"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        col.prop(scene, "ld_limit_profile", text="Limit Profile")
        col.prop(scene, "ld_proxy_max_speed_up", text="MaxSpeedUp")
        col.prop(scene, "ld_proxy_max_speed_down", text="MaxSpeedDown")
        col.prop(scene, "ld_proxy_max_speed_horiz", text="MaxSpeedHoriz")
        col.prop(scene, "ld_proxy_max_acc_vert", text="MaxAcc")
        col.prop(scene, "ld_proxy_min_distance", text="MinDistance")
        col.separator()
        col.prop(scene, "ld_checker_range_object", text="Area Object")
        if scene.ld_checker_range_object is None:
            col.prop(scene, "ld_checker_range_width", text="Area Width")
            col.prop(scene, "ld_checker_range_height", text="Area Height")
            col.prop(scene, "ld_checker_range_depth", text="Area Depth")
        col.operator("liberadrone.create_range_object", text="Create Area Object")


class LD_PT_libera_panel_overlay(LD_PT_libera_panel_base):
    bl_label = "Overlay"
    bl_idname = "LD_PT_libera_panel_overlay"
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "ld_checker_enabled", text="Show Checker")
        col = layout.column(align=True)
        col.prop(scene, "ld_checker_show_speed", text="Speed")
        col.prop(scene, "ld_checker_show_acc", text="Acc")
        col.prop(scene, "ld_checker_show_distance", text="Distance")
        col.prop(scene, "ld_checker_range_enabled", text="Range")
        col.prop(scene, "ld_checker_size", text="Checker Size")
        layout.separator()
        row = layout.row(align=True)
        row.operator("liberadrone.show_check_graph", text="Show Check Graph")
        op = row.operator("liberadrone.show_check_graph", text="CurrentFormation")
        op.use_current_range = True


class LD_PT_libera_panel_view_setup(LD_PT_libera_panel_base):
    bl_label = "View Setup"
    bl_idname = "LD_PT_libera_panel_view_setup"
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("liberadrone.frame_from_neg_y", text="Frame From -Y")
        row.prop(context.scene, "ld_camera_margin", text="")


class LD_PT_libera_panel_io(LD_PT_libera_panel_base):
    bl_label = "I/O"
    bl_idname = "LD_PT_libera_panel_io"
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "ld_import_sheet_url", text="Sheet URL")
        layout.prop(scene, "ld_import_vat_dir", text="VAT/CAT Folder")
        layout.operator("liberadrone.setup_all", text="Setup Without Import Sheet")
        layout.operator("liberadrone.show_import_sheet", text="Import Sheet")
        layout.operator("liberadrone.show_export_sheet", text="Export Sheet")
        layout.separator()
        layout.operator("liberadrone.pack_scene_images", text="Pack Cache Images")


class LD_PT_libera_panel_compatibility(LD_PT_libera_panel_base):
    bl_label = "Compatibility"
    bl_idname = "LD_PT_libera_panel_compatibility"
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "ld_import_vat_dir", text="VAT/CAT Folder")
        row = layout.row(align=True)
        row.operator("liberadrone.compat_import_vatcat", text="Import VAT/CAT")
        row.operator("liberadrone.compat_preview_vatcat", text="Preview")
        layout.template_list(
            "LD_UL_CompatPreview",
            "",
            scene,
            "ld_compat_preview_items",
            scene,
            "ld_compat_preview_index",
            rows=4,
        )
        layout.operator("liberadrone.export_vatcat_renderrange", text="Export VAT/CAT (Render Range)")
        layout.operator("liberadrone.export_vatcat_transitions", text="Export VAT/CAT (Transitions)")


classes = (
    LD_PT_libera_panel_preview,
    LD_PT_libera_panel_errorcheck,
    LD_PT_libera_panel_overlay,
    LD_PT_libera_panel_view_setup,
    LD_PT_libera_panel_io,
    LD_PT_libera_panel_compatibility,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    from liberadronecore.operators import compatibility as compat_ops

    bpy.types.Scene.ld_preview_show_ring = bpy.props.BoolProperty(
        name="ShowRing",
        get=_get_preview_show_ring,
        set=_set_preview_show_ring,
    )
    bpy.types.Scene.ld_preview_vertex_alpha_mask = bpy.props.BoolProperty(
        name="Vertex Alpha Mask",
        get=_get_preview_vertex_alpha_mask,
        set=_set_preview_vertex_alpha_mask,
    )
    bpy.types.Scene.ld_limit_profile = bpy.props.EnumProperty(
        name="Limit Profile",
        items=(
            ("MODEL_X", "MODEL-X", "Default limits"),
            ("CUSTOM", "Custom", "Custom limits"),
        ),
        default="MODEL_X",
        update=_update_limit_profile,
    )
    bpy.types.Scene.ld_proxy_max_speed_up = bpy.props.FloatProperty(
        name="MaxSpeedUp",
        default=4.0,
        min=0.0,
    )
    bpy.types.Scene.ld_proxy_max_speed_down = bpy.props.FloatProperty(
        name="MaxSpeedDown",
        default=3.0,
        min=0.0,
    )
    bpy.types.Scene.ld_proxy_max_speed_horiz = bpy.props.FloatProperty(
        name="MaxSpeedHoriz",
        default=5.0,
        min=0.0,
    )
    bpy.types.Scene.ld_proxy_max_acc_vert = bpy.props.FloatProperty(
        name="MaxAcc",
        default=3.0,
        min=0.0,
    )
    bpy.types.Scene.ld_proxy_min_distance = bpy.props.FloatProperty(
        name="MinDistance",
        default=1.5,
        min=0.0,
    )
    bpy.types.Scene.ld_preview_scale = bpy.props.FloatProperty(
        name="Scale",
        get=_get_preview_scale,
        set=_set_preview_scale,
        min=0.0,
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
        name="Area Object",
        type=bpy.types.Object,
    )
    bpy.types.Scene.ld_checker_range_width = bpy.props.FloatProperty(
        name="Area Width",
        default=100.0,
        min=0.0,
    )
    bpy.types.Scene.ld_checker_range_height = bpy.props.FloatProperty(
        name="Area Height",
        default=100.0,
        min=0.0,
    )
    bpy.types.Scene.ld_checker_range_depth = bpy.props.FloatProperty(
        name="Area Depth",
        default=100.0,
        min=0.0,
    )
    bpy.types.Scene.ld_import_sheet_url = bpy.props.StringProperty(
        name="Sheet URL",
        default="",
        subtype='NONE',
    )
    bpy.types.Scene.ld_import_vat_dir = bpy.props.StringProperty(
        name="VAT/CAT Folder",
        default="",
        subtype='DIR_PATH',
    )
    bpy.types.Scene.ld_compat_preview_items = bpy.props.CollectionProperty(
        type=compat_ops.LD_CompatPreviewItem,
    )
    bpy.types.Scene.ld_compat_preview_index = bpy.props.IntProperty(
        name="Preview Index",
        default=0,
    )
    scene = getattr(bpy.context, "scene", None)
    if scene and getattr(scene, "ld_limit_profile", "") == "MODEL_X":
        defaults = (
            getattr(scene, "ld_proxy_max_speed_up", 0.0),
            getattr(scene, "ld_proxy_max_speed_down", 0.0),
            getattr(scene, "ld_proxy_max_speed_horiz", 0.0),
            getattr(scene, "ld_proxy_max_acc_vert", 0.0),
            getattr(scene, "ld_proxy_min_distance", 0.0),
        )
        if all(value == 0.0 for value in defaults):
            _apply_limit_profile(scene, "MODEL_X")


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
    if hasattr(bpy.types.Scene, "ld_import_sheet_url"):
        del bpy.types.Scene.ld_import_sheet_url
    if hasattr(bpy.types.Scene, "ld_import_vat_dir"):
        del bpy.types.Scene.ld_import_vat_dir
    if hasattr(bpy.types.Scene, "ld_compat_preview_index"):
        del bpy.types.Scene.ld_compat_preview_index
    if hasattr(bpy.types.Scene, "ld_compat_preview_items"):
        del bpy.types.Scene.ld_compat_preview_items
    if hasattr(bpy.types.Scene, "ld_checker_range_object"):
        del bpy.types.Scene.ld_checker_range_object
    if hasattr(bpy.types.Scene, "ld_checker_size"):
        del bpy.types.Scene.ld_checker_size
    if hasattr(bpy.types.Scene, "ld_checker_enabled"):
        del bpy.types.Scene.ld_checker_enabled
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
    if hasattr(bpy.types.Scene, "ld_preview_vertex_alpha_mask"):
        del bpy.types.Scene.ld_preview_vertex_alpha_mask
    if hasattr(bpy.types.Scene, "ld_preview_scale"):
        del bpy.types.Scene.ld_preview_scale

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
