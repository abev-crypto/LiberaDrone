import bpy
from liberadronecore.formation.fn_nodecategory import FN_Register

class FN_FormationTree(bpy.types.NodeTree, FN_Register):
    bl_idname = "FN_FormationTree"
    bl_label  = "FN Formaiton"
    bl_icon   = 'NODETREE'  # Icon
    bl_use_link_search = True

    @classmethod
    def poll(cls, context):
        # Tree can always be created
        return True

    def is_link_valid(self, from_socket, to_socket):
        # Restrict links to matching socket types; allow reroutes.
        if from_socket is None or to_socket is None:
            return False
        if getattr(from_socket, "is_output", False) == getattr(to_socket, "is_output", False):
            return False
        if getattr(from_socket, "bl_idname", "") == "NodeSocketVirtual" or getattr(to_socket, "bl_idname", "") == "NodeSocketVirtual":
            return True
        return getattr(from_socket, "bl_idname", "") == getattr(to_socket, "bl_idname", "")
