from __future__ import annotations

import bpy
from liberadronecore.formation.fn_nodecategory import FN_Register
from liberadronecore.formation.fn_parse import get_cached_schedule


class FN_PT_formation_panel(bpy.types.Panel, FN_Register):
    bl_idname = "FN_PT_formation_panel"
    bl_label = "Formation Nodes"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Formation"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return bool(space and getattr(space, "tree_type", "") == "FN_FormationTree")

    def draw(self, context):
        layout = self.layout
        layout.operator("fn.setup_scene", text="Setup")
        layout.operator("fn.calculate_schedule", text="Calculate")
        layout.separator()
        row = layout.row(align=True)
        row.operator("fn.render_range_current", text="CurrentFormation")
        row = layout.row(align=True)
        row.operator("fn.render_range_prev", text="PrevFormation")
        row.operator("fn.render_range_next", text="NextFormation")
        if get_cached_schedule():
            layout.label(text=f"Cached entries: {len(get_cached_schedule())}")

        node = getattr(context, "active_node", None)
        if node:
            box = layout.box()
            box.label(text="Active Node")
            box.prop(node, "label", text="Label")
            op = box.operator("fn.create_collection_from_label", text="Create Collection")
            op.node_name = node.name
            box.operator("fn.assign_selected_to_show", text="Assign Selected to Show")
