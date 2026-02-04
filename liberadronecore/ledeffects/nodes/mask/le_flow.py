from __future__ import annotations

import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.overlay import checker as overlay_checker

register_runtime_function(overlay_checker.get_flow_values, name="_flow_values")
register_runtime_function(overlay_checker.get_flow_direction, name="_flow_direction")


@register_runtime_function
def _flow_vel_limits():
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return 0.0, 1.0
    max_up = float(getattr(scene, "ld_proxy_max_speed_up", 0.0))
    max_down = float(getattr(scene, "ld_proxy_max_speed_down", 0.0))
    max_horiz = float(getattr(scene, "ld_proxy_max_speed_horiz", 0.0))
    candidates = [val for val in (max_up, max_down, max_horiz) if val > 0.0]
    max_vel = max(candidates) if candidates else 1.0
    return 0.0, float(max_vel)


class LDLEDFlowMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask by velocity (remapped 0-1)."""

    NODE_CATEGORY_ID = "LD_LED_SIMULATE"
    NODE_CATEGORY_LABEL = "Simulate"

    bl_idname = "LDLEDFlowMaskNode"
    bl_label = "Flow"
    bl_icon = "FORCE_TURBULENCE"

    auto_range: bpy.props.BoolProperty(
        name="Auto",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        min_vel = self.inputs.new("NodeSocketFloat", "Min Vel")
        min_vel.default_value = 0.0
        max_vel = self.inputs.new("NodeSocketFloat", "Max Vel")
        max_vel.default_value = 1.0
        try:
            min_vel.min_value = 0.0
            max_vel.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Vel")
        self.outputs.new("NodeSocketColor", "Dir")

    def draw_buttons(self, context, layout):
        layout.prop(self, "auto_range")

    def build_code(self, inputs):
        min_vel = inputs.get("Min Vel", "0.0")
        max_vel = inputs.get("Max Vel", "1.0")
        out_vel = self.output_var("Vel")
        out_dir = self.output_var("Dir")
        flow_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        lines = [
            f"_flow_{flow_id} = _flow_values(idx, frame)",
            f"_flow_dir_{flow_id} = _flow_direction(idx, frame)",
            f"{out_dir} = (_flow_dir_{flow_id}[0], _flow_dir_{flow_id}[1], _flow_dir_{flow_id}[2], 1.0)",
        ]
        if self.auto_range:
            lines.extend(
                [
                    f"_flow_min_{flow_id}, _flow_max_{flow_id} = _flow_vel_limits()",
                    f"_flow_span_{flow_id} = _flow_max_{flow_id} - _flow_min_{flow_id}",
                    (
                        f"{out_vel} = _clamp01((_flow_{flow_id} - _flow_min_{flow_id}) / "
                        f"_flow_span_{flow_id}) if _flow_span_{flow_id} > 0.0 else 0.0"
                    ),
                ]
            )
        else:
            lines.extend(
                [
                    f"_flow_span_{flow_id} = ({max_vel}) - ({min_vel})",
                    (
                        f"{out_vel} = _clamp01((_flow_{flow_id} - ({min_vel})) / "
                        f"_flow_span_{flow_id}) if _flow_span_{flow_id} > 0.0 else 0.0"
                    ),
                ]
            )
        return "\n".join(lines)
