import bpy
from pathlib import Path


def _get_area_region(area, region_type: str = "WINDOW"):
    for region in area.regions:
        if region.type == region_type:
            return region
    return None


def _split_area(context, screen, area, direction: str, factor: float):
    region = _get_area_region(area)
    if region is None:
        return None
    before = set(screen.areas)
    try:
        with context.temp_override(area=area, region=region, screen=screen):
            bpy.ops.screen.area_split(direction=direction, factor=factor)
    except Exception:
        return None
    after = set(screen.areas)
    new_areas = [a for a in after if a not in before]
    return new_areas[0] if new_areas else None


def _append_workspace_from_library(blend_path: Path, name: str):
    try:
        with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
            workspaces = getattr(data_from, "workspaces", None)
            if not workspaces or name not in workspaces:
                return None
            data_to.workspaces = [name]
    except Exception:
        return None
    return bpy.data.workspaces.get(name)


def _ensure_workspace(context, name: str):
    existing = bpy.data.workspaces.get(name)
    if existing is not None:
        return existing
    ws_path = Path(__file__).resolve().parents[2] / "scene" / "ws.blend"
    if not ws_path.exists():
        return None

    blend_path = ws_path.resolve()
    ws = _append_workspace_from_library(blend_path, name)
    if ws is not None:
        return ws

    workspace_dir = str(blend_path) + "/WorkSpace/"
    window = getattr(context, "window", None) or bpy.context.window
    screen = window.screen if window else None
    if window and screen:
        with context.temp_override(window=window, screen=screen):
            bpy.ops.wm.append(
                directory=workspace_dir,
                filename=name,
                filepath=workspace_dir + name,
            )
    return bpy.data.workspaces.get(name)


def setup_workspace(context, mode: str):
    if mode == "LED":
        name = "LED"
        tree_type = "LD_LedEffectsTree"
    else:
        name = "Formation"
        tree_type = "FN_FormationTree"

    ws = _ensure_workspace(context, name)
    if ws is None:
        return None
    return ws


class LD_OT_setup_workspace_formation(bpy.types.Operator):
    bl_idname = "liberadrone.setup_workspace_formation"
    bl_label = "FormationNodeWindow"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ws = setup_workspace(context, "FORMATION")
        if ws is None:
            self.report({'ERROR'}, "Failed to create workspace (missing template or window)")
            return {'CANCELLED'}
        return {'FINISHED'}


class LD_OT_setup_workspace_led(bpy.types.Operator):
    bl_idname = "liberadrone.setup_workspace_led"
    bl_label = "LEDEffectNodeWindow"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ws = setup_workspace(context, "LED")
        if ws is None:
            self.report({'ERROR'}, "Failed to create workspace (missing template or window)")
            return {'CANCELLED'}
        return {'FINISHED'}
