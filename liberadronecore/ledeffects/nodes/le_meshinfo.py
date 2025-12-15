import bpy


class LDLEDMeshInfoNode(bpy.types.Node):
    """Exposes mesh information for LED sampling."""

    bl_idname = "LDLEDMeshInfoNode"
    bl_label = "LED Mesh Info"
    bl_icon = "MESH_DATA"

    target_object: bpy.props.PointerProperty(
        name="Mesh",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    sample_mode: bpy.props.EnumProperty(
        name="Sample Mode",
        items=[
            ("VERT", "Vertex", "Sample vertex colors"),
            ("FACE", "Face", "Sample by face area"),
        ],
        default="VERT",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketFloat", "Intensity")
        self.outputs.new("NodeSocketVector", "Normal")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")
        layout.prop(self, "sample_mode", text="")
