import bpy
from mathutils import Matrix, Vector
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.util.modeling import delaunay


class LDLEDInsideMeshNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask based on whether a point is inside a mesh bounds."""

    bl_idname = "LDLEDInsideMeshNode"
    bl_label = "Inside Mesh"
    bl_icon = "MESH_CUBE"

    combine_items = [
        ("MULTIPLY", "Multiply", "Multiply the mask with the value"),
        ("ADD", "Add", "Add the value to the mask"),
        ("SUB", "Subtract", "Subtract the value from the mask"),
    ]

    combine_mode: bpy.props.EnumProperty(
        name="Combine",
        items=combine_items,
        default="MULTIPLY",
        options={'LIBRARY_EDITABLE'},
    )
    invert: bpy.props.BoolProperty(
        name="Invert",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        mesh = self.inputs.new("NodeSocketObject", "Mesh")
        value = self.inputs.new("NodeSocketFloat", "Value")
        value.default_value = 1.0
        try:
            value.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        op = layout.operator("ldled.insidemesh_create_mesh", text="From Selection")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        layout.prop(self, "combine_mode", text="")
        layout.prop(self, "invert")

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        obj_expr = inputs.get("Mesh", "''")
        value = inputs.get("Value", "1.0")
        base_expr = f"1.0 if _point_in_mesh_bbox({obj_expr}, (pos[0], pos[1], pos[2])) else 0.0"
        if self.invert:
            base_expr = f"(1.0 - ({base_expr}))"
        if self.combine_mode == "ADD":
            expr = f"_clamp01(({base_expr}) + ({value}))"
        elif self.combine_mode == "SUB":
            expr = f"_clamp01(({base_expr}) - ({value}))"
        else:
            expr = f"_clamp01(({base_expr}) * ({value}))"
        return f"{out_var} = {expr}"


def _unique_name(base: str) -> str:
    if not bpy.data.objects.get(base):
        return base
    idx = 1
    while True:
        name = f"{base}.{idx:03d}"
        if not bpy.data.objects.get(name):
            return name
        idx += 1


def _ensure_collection(context) -> bpy.types.Collection:
    if context and getattr(context, "collection", None):
        return context.collection
    scene = getattr(context, "scene", None) or bpy.context.scene
    return scene.collection


def _freeze_object_transform(obj: bpy.types.Object) -> None:
    if obj is None or obj.type != 'MESH':
        return
    if obj.matrix_world != Matrix.Identity(4):
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)
        obj.data.update()


def _selected_world_vertices(context) -> list[Vector]:
    obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH':
        return []
    if obj.mode != 'EDIT':
        return []
    try:
        import bmesh
    except Exception:
        return []
    bm = bmesh.from_edit_mesh(obj.data)
    mw = obj.matrix_world
    return [mw @ v.co for v in bm.verts if v.select]


def _selected_mesh_objects(context) -> list[bpy.types.Object]:
    selected = getattr(context, "selected_objects", None) or []
    return [obj for obj in selected if obj.type == 'MESH']


def _collect_points(context) -> list[Vector]:
    verts = _selected_world_vertices(context)
    if verts:
        return verts
    points: list[Vector] = []
    for obj in _selected_mesh_objects(context):
        mw = obj.matrix_world
        for v in obj.data.vertices:
            points.append(mw @ v.co)
    return points


def _apply_solidify(obj: bpy.types.Object) -> None:
    solid = obj.modifiers.new("Solidify", type='SOLIDIFY')
    solid.thickness = 0.2
    solid.offset = 0.0
    solid.use_rim = True
    solid.use_even_offset = True
    for attr in ("use_quality_normals", "nonmanifold_boundary_mode"):
        if hasattr(solid, attr):
            try:
                setattr(solid, attr, True if isinstance(getattr(solid, attr), bool) else getattr(solid, attr))
            except Exception:
                pass


