import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDMeshInfoNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Exposes mesh information for LED sampling."""

    bl_idname = "LDLEDMeshInfoNode"
    bl_label = "Mesh Info"
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
        self.outputs.new("NodeSocketObject", "Mesh")
        self.outputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketFloat", "Intensity")
        self.outputs.new("NodeSocketVector", "Normal")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")
        layout.prop(self, "sample_mode", text="")

    def build_code(self, inputs):
        out_mesh = self.output_var("Mesh")
        out_color = self.output_var("Color")
        out_intensity = self.output_var("Intensity")
        out_normal = self.output_var("Normal")
        obj_name = self.target_object.name if self.target_object else ""
        enabled = 1.0 if obj_name else 0.0
        return "\n".join(
            [
                f"{out_mesh} = bpy.data.objects.get({obj_name!r}) if {obj_name!r} else None",
                f"{out_intensity} = {enabled}",
                f"{out_color} = (1.0, 1.0, 1.0, 1.0) if {enabled} > 0.0 else (0.0, 0.0, 0.0, 1.0)",
                f"{out_normal} = (0.0, 1.0, 0.0)",
            ]
        )
