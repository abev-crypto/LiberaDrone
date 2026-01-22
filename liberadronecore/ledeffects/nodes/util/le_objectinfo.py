import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDObjectInfoNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Expose world-space object transform as separate float outputs."""

    bl_idname = "LDLEDObjectInfoNode"
    bl_label = "Object Info"
    bl_icon = "OBJECT_DATA"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketObject", "Object")
        self.outputs.new("NodeSocketFloat", "Position X")
        self.outputs.new("NodeSocketFloat", "Position Y")
        self.outputs.new("NodeSocketFloat", "Position Z")
        self.outputs.new("NodeSocketFloat", "Rotation X")
        self.outputs.new("NodeSocketFloat", "Rotation Y")
        self.outputs.new("NodeSocketFloat", "Rotation Z")
        self.outputs.new("NodeSocketFloat", "Scale X")
        self.outputs.new("NodeSocketFloat", "Scale Y")
        self.outputs.new("NodeSocketFloat", "Scale Z")

    def build_code(self, inputs):
        obj_name = inputs.get("Object", "None")

        out_px = self.output_var("Position X")
        out_py = self.output_var("Position Y")
        out_pz = self.output_var("Position Z")
        out_rx = self.output_var("Rotation X")
        out_ry = self.output_var("Rotation Y")
        out_rz = self.output_var("Rotation Z")
        out_sx = self.output_var("Scale X")
        out_sy = self.output_var("Scale Y")
        out_sz = self.output_var("Scale Z")

        cache_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        pos_var = f"_pos_{cache_key}"
        rot_var = f"_rot_{cache_key}"
        scale_var = f"_scale_{cache_key}"
        transform_var = f"_xf_{cache_key}"

        return "\n".join(
            [
                f"{transform_var} = _object_world_transform({obj_name})",
                f"{pos_var}, {rot_var}, {scale_var} = {transform_var} if {transform_var} else ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))",
                f"{out_px} = float({pos_var}[0])",
                f"{out_py} = float({pos_var}[1])",
                f"{out_pz} = float({pos_var}[2])",
                f"{out_rx} = float({rot_var}[0])",
                f"{out_ry} = float({rot_var}[1])",
                f"{out_rz} = float({rot_var}[2])",
                f"{out_sx} = float({scale_var}[0])",
                f"{out_sy} = float({scale_var}[1])",
                f"{out_sz} = float({scale_var}[2])",
            ]
        )
