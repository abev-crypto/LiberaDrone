import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.le_nodecategory import LDLED_Register
from liberadronecore.ledeffects.util import paint as paint_util


class LDLEDPaintItem(bpy.types.PropertyGroup, LDLED_Register):
    index: bpy.props.IntProperty(
        name="Index",
        default=0,
        min=0,
        options={'LIBRARY_EDITABLE'},
    )
    color: bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=4,
        default=(0.0, 0.0, 0.0, 0.0),
        min=0.0,
        max=1.0,
        options={'LIBRARY_EDITABLE'},
    )


class LDLEDPaintNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Paint virtual colors by vertex index."""

    bl_idname = "LDLEDPaintNode"
    bl_label = "Paint"
    bl_icon = "BRUSH_DATA"

    paint_color: bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=3,
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        options={'LIBRARY_EDITABLE'},
    )
    paint_alpha: bpy.props.FloatProperty(
        name="Alpha",
        default=1.0,
        min=0.0,
        max=1.0,
        options={'LIBRARY_EDITABLE'},
    )
    blend_mode: bpy.props.EnumProperty(
        name="Blend Mode",
        items=paint_util.PAINT_BLEND_MODES,
        default="MIX",
        options={'LIBRARY_EDITABLE'},
    )
    remap_rows: bpy.props.BoolProperty(
        name="Remap Rows",
        description="Remap Paint IDs to match the current drone index",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )
    remap_frame: bpy.props.IntProperty(
        name="Remap Frame",
        description="Use formation IDs from this frame when remapping",
        default=-1,
        options={'LIBRARY_EDITABLE'},
    )
    paint_radius: bpy.props.FloatProperty(
        name="Radius",
        default=paint_util.DEFAULT_BRUSH_RADIUS_PX,
        min=1.0,
        options={'LIBRARY_EDITABLE'},
    )
    paint_hard_brush: bpy.props.BoolProperty(
        name="Hard Brush",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )
    paint_erase: bpy.props.BoolProperty(
        name="Eraser",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )
    paint_items: bpy.props.CollectionProperty(type=LDLEDPaintItem, options={'LIBRARY_EDITABLE'})

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def code_inputs(self):
        return []

    def draw_buttons(self, context, layout):
        op = layout.operator("ldled.paint_start", text="Paint")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op = layout.operator("ldled.paint_take", text="Take")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        layout.prop(self, "remap_rows")
        row = layout.row(align=True)
        row.enabled = self.remap_rows
        row.prop(self, "remap_frame")
        op = row.operator("ldled.remapframe_fill_current", text="Now")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

    def build_code(self, inputs):
        out_var = self.output_var("Color")
        tree_name = self.id_data.name
        node_name = self.name
        idx_expr = "_formation_id(idx)"
        if self.remap_rows:
            if int(self.remap_frame) >= 0:
                idx_expr = f"_cat_ref_fid_locked(idx, frame, {int(self.remap_frame)})"
            else:
                idx_expr = "_cat_ref_fid(idx)"
        return f"{out_var} = _paint_color({tree_name!r}, {node_name!r}, {idx_expr})"
