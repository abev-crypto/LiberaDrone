import bpy


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


def _ensure_workspace(context, name: str):
    bpy.ops.workspace.append_activate(
        context,
        idname=name,
        filepath="",
    )
    ws = context.workspace
    ws.name = name
    return ws


def _configure_workspace_screen(context, screen, tree_type: str):
    areas = list(screen.areas)
    if not areas:
        return

    top_area = max(areas, key=lambda a: a.height * a.width)
    timeline_area = None

    if not any(a.type == 'TIMELINE' for a in screen.areas):
        new_area = _split_area(context, screen, top_area, 'HORIZONTAL', 0.75)
        if new_area is not None:
            bottom = min([top_area, new_area], key=lambda a: a.y)
            timeline_area = bottom
            top_area = max([top_area, new_area], key=lambda a: a.y)

    if timeline_area is None:
        for area in screen.areas:
            if area.type == 'TIMELINE':
                timeline_area = area
                break

    if not any(a.type == 'NODE_EDITOR' for a in screen.areas):
        new_area = _split_area(context, screen, top_area, 'VERTICAL', 0.5)
        if new_area is not None:
            left = min([top_area, new_area], key=lambda a: a.x)
            right = max([top_area, new_area], key=lambda a: a.x)
            left.type = 'VIEW_3D'
            right.type = 'NODE_EDITOR'
            space = right.spaces.active
            if hasattr(space, "tree_type"):
                space.tree_type = tree_type
            if hasattr(right, "ui_type"):
                right.ui_type = tree_type

    if timeline_area is not None:
        timeline_area.type = 'DOPESHEET_EDITOR'
        space = timeline_area.spaces.active
        if hasattr(space, "ui_type"):
            space.ui_type = 'TIMELINE'

    for area in screen.areas:
        if area.type == 'VIEW_3D':
            break


class LD_OT_setup_workspace(bpy.types.Operator):
    bl_idname = "liberadrone.setup_workspace"
    bl_label = "Setup Workspace"
    bl_options = {'REGISTER'}

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=(
            ("FORMATION", "Formation", "Formation node workspace"),
            ("LED", "LED Effect", "LED effect node workspace"),
        ),
        default="FORMATION",
    )

    def execute(self, context):
        if self.mode == "LED":
            name = "LEDEffectNodeWindow"
            tree_type = "LD_LedEffectsTree"
        else:
            name = "FormationNodeWindow"
            tree_type = "FN_FormationTree"

        ws = _ensure_workspace(context, name)
        if ws is None:
            self.report({'ERROR'}, "Failed to create workspace (missing template or window)")
            return {'CANCELLED'}

        window = context.window
        if window is None:
            self.report({'ERROR'}, "No active window")
            return {'CANCELLED'}

        window.workspace = ws
        screen = window.screen
        _configure_workspace_screen(context, screen, tree_type)
        return {'FINISHED'}


class LD_OT_setup_workspace_formation(LD_OT_setup_workspace):
    bl_idname = "liberadrone.setup_workspace_formation"
    bl_label = "FormationNodeWindow"

    def invoke(self, context, event):
        self.mode = "FORMATION"
        return self.execute(context)


class LD_OT_setup_workspace_led(LD_OT_setup_workspace):
    bl_idname = "liberadrone.setup_workspace_led"
    bl_label = "LEDEffectNodeWindow"

    def invoke(self, context, event):
        self.mode = "LED"
        return self.execute(context)
