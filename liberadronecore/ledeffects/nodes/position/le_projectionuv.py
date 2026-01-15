import bpy
from mathutils import Matrix, Vector
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDProjectionUVNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Project position into a mesh bbox to produce UV."""

    bl_idname = "LDLEDProjectionUVNode"
    bl_label = "Projection UV"
    bl_icon = "MOD_UVPROJECT"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketObject", "Mesh")
        self.outputs.new("NodeSocketFloat", "U")
        self.outputs.new("NodeSocketFloat", "V")

    def draw_buttons(self, context, layout):
        row = layout.row()
        row = layout.row(align=True)
        op = row.operator("ldled.projectionuv_create_mesh", text="Area XZ")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op.mode = "AREA"
        op = row.operator("ldled.projectionuv_create_mesh", text="Formation XZ")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op.mode = "FORMATION"
        op = row.operator("ldled.projectionuv_create_mesh", text="Selection XZ")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op.mode = "SELECT"

    def build_code(self, inputs):
        out_u = self.output_var("U")
        out_v = self.output_var("V")
        obj_expr = inputs.get("Mesh", "''")
        return "\n".join(
            [
                f"_uv = _project_bbox_uv({obj_expr}, (pos[0], pos[1], pos[2]))",
                f"{out_u} = _uv[0]",
                f"{out_v} = _uv[1]",
            ]
        )


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


def _world_bbox_from_points(points: list[Vector]) -> tuple[Vector, Vector] | None:
    if not points:
        return None
    min_v = Vector((float("inf"), float("inf"), float("inf")))
    max_v = Vector((float("-inf"), float("-inf"), float("-inf")))
    for p in points:
        min_v.x = min(min_v.x, p.x)
        min_v.y = min(min_v.y, p.y)
        min_v.z = min(min_v.z, p.z)
        max_v.x = max(max_v.x, p.x)
        max_v.y = max(max_v.y, p.y)
        max_v.z = max(max_v.z, p.z)
    return min_v, max_v


def _world_bbox_from_object(obj: bpy.types.Object) -> tuple[Vector, Vector] | None:
    if obj is None or obj.type != 'MESH':
        return None
    bbox = obj.bound_box
    if not bbox:
        return None
    mw = obj.matrix_world
    points = [mw @ Vector(corner) for corner in bbox]
    return _world_bbox_from_points(points)


def _world_bbox_from_collection(col: bpy.types.Collection) -> tuple[Vector, Vector] | None:
    if col is None:
        return None
    bounds = None
    for obj in col.all_objects:
        if obj.type != 'MESH':
            continue
        obj_bounds = _world_bbox_from_object(obj)
        if obj_bounds is None:
            continue
        min_v, max_v = obj_bounds
        if bounds is None:
            bounds = (min_v.copy(), max_v.copy())
        else:
            bounds[0].x = min(bounds[0].x, min_v.x)
            bounds[0].y = min(bounds[0].y, min_v.y)
            bounds[0].z = min(bounds[0].z, min_v.z)
            bounds[1].x = max(bounds[1].x, max_v.x)
            bounds[1].y = max(bounds[1].y, max_v.y)
            bounds[1].z = max(bounds[1].z, max_v.z)
    return bounds


def _selected_world_vertices(context) -> list[Vector]:
    obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
        return []
    try:
        import bmesh
    except Exception:
        return []
    bm = bmesh.from_edit_mesh(obj.data)
    verts = []
    mw = obj.matrix_world
    for v in bm.verts:
        if v.select:
            verts.append(mw @ v.co)
    return verts


def _selected_mesh_objects(context) -> list[bpy.types.Object]:
    selected = getattr(context, "selected_objects", None) or []
    return [obj for obj in selected if obj.type == 'MESH']


def _create_xz_plane(name: str, bounds: tuple[Vector, Vector], context) -> bpy.types.Object:
    min_v, max_v = bounds
    y = (min_v.y + max_v.y) * 0.5
    verts = [
        (min_v.x, y, min_v.z),
        (max_v.x, y, min_v.z),
        (max_v.x, y, max_v.z),
        (min_v.x, y, max_v.z),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    _ensure_collection(context).objects.link(obj)
    _freeze_object_transform(obj)
    return obj


