from __future__ import annotations

from typing import Callable, Dict, List, Optional

import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


def _sanitize_identifier(text: str) -> str:
    safe = []
    for ch in text or "":
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch == "_":
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe) or "node"
    if result[0].isdigit():
        result = f"n_{result}"
    return result


def _default_for_socket(socket: bpy.types.NodeSocket) -> str:
    if getattr(socket, "bl_idname", "") == "NodeSocketColor":
        return "(0.0, 0.0, 0.0, 1.0)"
    if getattr(socket, "bl_idname", "") == "NodeSocketFloat":
        return "0.0"
    return "0.0"


def _default_for_input(socket: bpy.types.NodeSocket) -> str:
    if hasattr(socket, "default_value"):
        value = socket.default_value
        if isinstance(value, (float, int)):
            return repr(float(value))
        if isinstance(value, (list, tuple)):
            return repr(tuple(float(v) for v in value))
    return _default_for_socket(socket)


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _alpha_over(dst: List[float], src: List[float], alpha: float) -> List[float]:
    inv = 1.0 - alpha
    return [
        src[0] * alpha + dst[0] * inv,
        src[1] * alpha + dst[1] * inv,
        src[2] * alpha + dst[2] * inv,
        1.0,
    ]


def _get_output_var(node: bpy.types.Node, socket: bpy.types.NodeSocket) -> str:
    mapping = getattr(node, "_codegen_output_vars", {})
    if socket.name in mapping:
        return mapping[socket.name]
    node_id = _sanitize_identifier(getattr(node, "name", "") or node.bl_idname)
    return f"{node_id}_{_sanitize_identifier(socket.name)}"


def _collect_outputs(tree: bpy.types.NodeTree) -> List[bpy.types.Node]:
    outputs = [n for n in tree.nodes if n.bl_idname == "LDLEDOutputNode"]
    outputs.sort(key=lambda n: (getattr(n, "priority", 0), n.name))
    return outputs


def compile_led_effect(tree: bpy.types.NodeTree) -> Optional[Callable]:
    outputs = _collect_outputs(tree)
    if not outputs:
        return None

    emitted: set[int] = set()
    lines: List[str] = []

    def emit_node(node: bpy.types.Node) -> None:
        if node.as_pointer() in emitted:
            return
        if not isinstance(node, LDLED_CodeNodeBase):
            return

        inputs: Dict[str, str] = {}
        for sock in getattr(node, "inputs", []):
            inputs[sock.name] = resolve_input(sock)

        output_vars = {
            sock.name: f"{node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(node, "outputs", [])
        }
        node._set_codegen_output_vars(output_vars)

        snippet = node.build_code(inputs) or ""
        for line in snippet.splitlines():
            lines.append(line)
        emitted.add(node.as_pointer())

    def resolve_input(socket: Optional[bpy.types.NodeSocket]) -> str:
        if socket is None:
            return "0.0"
        if socket.is_linked and socket.links:
            link = socket.links[0]
            from_node = link.from_node
            from_socket = link.from_socket
            emit_node(from_node)
            if isinstance(from_node, LDLED_CodeNodeBase):
                return _get_output_var(from_node, from_socket)
            return _default_for_socket(from_socket)
        return _default_for_input(socket)

    for output in outputs:
        color_in = resolve_input(output.inputs.get("Color"))
        intensity_in = resolve_input(output.inputs.get("Intensity"))
        alpha_in = resolve_input(output.inputs.get("Alpha"))
        entry_in = resolve_input(output.inputs.get("Entry"))
        influence_in = resolve_input(output.inputs.get("Influence"))

        out_id = _sanitize_identifier(output.name)
        exposure = float(getattr(output, "exposure", 0.0))
        intensity_with_exposure = f"({intensity_in}) * (2.0 ** ({exposure!r}))"

        lines.append(f"_color_{out_id} = {color_in}")
        lines.append(f"_intensity_{out_id} = {intensity_with_exposure}")
        lines.append(f"_alpha_{out_id} = {alpha_in}")
        lines.append(f"_entry_{out_id} = {entry_in}")
        lines.append(f"_influence_{out_id} = {influence_in}")
        lines.append(f"if _entry_{out_id} > 0.0:")
        lines.append(
            "    _src_alpha = _clamp01(_alpha_{0} * _influence_{0} * ("
            "_color_{0}[3] if len(_color_{0}) > 3 else 1.0))".format(out_id)
        )
        lines.append(
            "    _src_color = ["
            "_color_{0}[0] * _intensity_{0}, "
            "_color_{0}[1] * _intensity_{0}, "
            "_color_{0}[2] * _intensity_{0}, "
            "1.0]".format(out_id)
        )
        lines.append("    color = _alpha_over(color, _src_color, _src_alpha)")

    body = ["def _led_effect(idx, pos, frame, random_seq):", "    color = [0.0, 0.0, 0.0, 1.0]"]
    body.extend([f"    {line}" for line in lines])
    body.append("    return color")

    code = "\n".join(body)
    env = {
        "_clamp01": _clamp01,
        "_alpha_over": _alpha_over,
    }
    exec(code, env)
    return env["_led_effect"]


_TREE_CACHE: Dict[int, Callable] = {}


def get_compiled_effect(tree: bpy.types.NodeTree) -> Optional[Callable]:
    key = tree.as_pointer()
    if key in _TREE_CACHE and not tree.is_updated:
        return _TREE_CACHE[key]
    compiled = compile_led_effect(tree)
    if compiled is not None:
        _TREE_CACHE[key] = compiled
    return compiled


def get_active_tree(scene: bpy.types.Scene) -> Optional[bpy.types.NodeTree]:
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", "") == "LD_LedEffectsTree":
            return tree
    return None
