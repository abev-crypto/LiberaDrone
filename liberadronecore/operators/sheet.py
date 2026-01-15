import bpy

from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.ui.import_sheet import export_ui, import_ui, sheetutils


class LD_OT_show_import_sheet(bpy.types.Operator):
    bl_idname = "liberadrone.show_import_sheet"
    bl_label = "Show Import Sheet"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        sheet_url = getattr(scene, "ld_import_sheet_url", "") or sheetutils.SHEET_URL_DEFAULT
        vat_dir = getattr(scene, "ld_import_vat_dir", "")
        import_ui.SheetImportWindow.show_window(sheet_url, vat_dir)
        return {'FINISHED'}


class LD_OT_show_export_sheet(bpy.types.Operator):
    bl_idname = "liberadrone.show_export_sheet"
    bl_label = "Show Export Sheet"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        sheet_url = getattr(scene, "ld_import_sheet_url", "") or sheetutils.SHEET_URL_DEFAULT
        export_dir = getattr(scene, "ld_import_vat_dir", "")
        export_ui.SheetExportWindow.show_window(sheet_url, export_dir)
        return {'FINISHED'}


class SheetOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LD_OT_show_import_sheet)
        bpy.utils.register_class(LD_OT_show_export_sheet)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LD_OT_show_export_sheet)
        bpy.utils.unregister_class(LD_OT_show_import_sheet)
