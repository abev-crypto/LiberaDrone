import bpy
from liberadronecore.ui import import_sheet


class LD_OT_show_import_sheet(bpy.types.Operator):
    bl_idname = "liberadrone.show_import_sheet"
    bl_label = "Show Import Sheet"
    bl_options = {'REGISTER'}

    def execute(self, context):
        import_sheet.SheetImportWindow.show_window(import_sheet.SHEET_URL_DEFAULT)
        return {'FINISHED'}
