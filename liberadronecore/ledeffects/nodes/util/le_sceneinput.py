import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


_SCENE_INPUT_CACHE = {"scene": "", "frame": None, "values": {}}


@register_runtime_function
def _scene_input_value(name: str, frame: float, default: float = 0.0) -> float:
    if not name:
        return float(default)
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return float(default)
    frame_val = float(frame)
    cache = _SCENE_INPUT_CACHE
    if cache["scene"] != scene.name or cache["frame"] != frame_val:
        values = {}
        for item in getattr(scene, "ld_led_inputs", []) or []:
            try:
                values[str(item.name)] = float(item.value)
            except Exception:
                continue
        cache["scene"] = scene.name
        cache["frame"] = frame_val
        cache["values"] = values
    return float(cache["values"].get(str(name), default))


class LDLEDSceneInputNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Expose a scene-level animated input value."""

    bl_idname = "LDLEDSceneInputNode"
    bl_label = "Scene Input"
    bl_icon = "DRIVER"

    input_name: bpy.props.StringProperty(
        name="Input",
        default="",
        options={'LIBRARY_EDITABLE'},
    )
    default_value: bpy.props.FloatProperty(
        name="Default",
        default=0.0,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "Value")

    def draw_buttons(self, context, layout):
        scene = getattr(context, "scene", None)
        if scene is not None:
            layout.prop_search(self, "input_name", scene, "ld_led_inputs", text="")
        else:
            layout.prop(self, "input_name", text="")
        layout.prop(self, "default_value", text="Default")

    def build_code(self, inputs):
        out_var = self.output_var("Value")
        name = self.input_name or ""
        return f"{out_var} = _scene_input_value({name!r}, frame, {float(self.default_value)!r})"
