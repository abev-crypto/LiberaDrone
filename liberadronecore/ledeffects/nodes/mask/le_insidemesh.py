import bpy
from mathutils import Matrix, Vector
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.util.modeling import delaunay


class LDLEDInsideMeshNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask based on whether a point is inside a mesh bounds."""

    bl_idname = "LDLEDInsideMeshNode"
    bl_label = "Inside Mesh"
    bl_icon = "MESH_CUBE"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        mesh = self.inputs.new("NodeSocketObject", "Mesh")
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        op = layout.operator("ldled.insidemesh_create_mesh", text="From Selection")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        obj_expr = inputs.get("Mesh", "''")
        return f"{out_var} = 1.0 if _point_in_mesh_bbox({obj_expr}, (pos[0], pos[1], pos[2])) else 0.0"


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


class LDLED_OT_insidemesh_create_mesh(bpy.types.Operator):
    bl_idname = "ldled.insidemesh_create_mesh"
    bl_label = "Create Inside Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, LDLEDInsideMeshNode):
            self.report({'ERROR'}, "Inside Mesh node not found")
            return {'CANCELLED'}

        points = _collect_points(context)
        if len(points) < 3:
            self.report({'ERROR'}, "Select at least 3 vertices or a mesh")
            return {'CANCELLED'}

        mesh = delaunay.build_planar_mesh_from_points(points)
        name = _unique_name(f"{node.name}_Inside")
        obj = bpy.data.objects.new(name, mesh)
        _ensure_collection(context).objects.link(obj)
        obj.display_type = 'BOUNDS'
        _apply_solidify(obj)
        _freeze_object_transform(obj)
        mesh_socket = node.inputs.get("Mesh")
        if mesh_socket is not None and hasattr(mesh_socket, "default_value"):
            mesh_socket.default_value = obj
        return {'FINISHED'}


class LDLED_InsideMeshOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LDLED_OT_insidemesh_create_mesh)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LDLED_OT_insidemesh_create_mesh)
