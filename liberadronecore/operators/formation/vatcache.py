import bpy
from bpy.props import StringProperty

from liberadronecore.formation.fn_nodecategory import FN_Register
from liberadronecore.formation.nodes import fn_vatcache


class FN_OT_build_vat_cache(bpy.types.Operator, FN_Register):
    bl_idname = "fn.build_vat_cache"
    bl_label = "Build VAT Cache"
    node_name: StringProperty()

    def execute(self, context):
        if not self.node_name:
            self.report({'ERROR'}, "Missing node name.")
            return {'CANCELLED'}
        node = None
        for ng in bpy.data.node_groups:
            if getattr(ng, "bl_idname", "") != "FN_FormationTree":
                continue
            node = ng.nodes.get(self.node_name)
            if node:
                break
        if node is None or not isinstance(node, fn_vatcache.FN_VATCacheNode):
            self.report({'ERROR'}, "Node not found.")
            return {'CANCELLED'}
        try:
            node.build_cache(context)
        except Exception as exc:
            self.report({'ERROR'}, f"VAT cache failed: {exc}")
            return {'CANCELLED'}
        return {'FINISHED'}
