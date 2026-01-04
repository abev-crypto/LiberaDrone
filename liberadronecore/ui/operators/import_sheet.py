import bpy
from liberadronecore.ui import import_sheet


class LD_OT_show_import_sheet(bpy.types.Operator):
    bl_idname = "liberadrone.show_import_sheet"
    bl_label = "Show Import Sheet"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        sheet_url = getattr(scene, "ld_import_sheet_url", "") or import_sheet.SHEET_URL_DEFAULT
        vat_dir = getattr(scene, "ld_import_vat_dir", "")
        import_sheet.SheetImportWindow.show_window(sheet_url, vat_dir)
        return {'FINISHED'}
