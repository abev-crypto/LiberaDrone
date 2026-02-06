from __future__ import annotations

import math
import mathutils
from typing import Callable, Dict, List, Optional, Tuple, Any

import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects import le_codegen_base
from liberadronecore.ledeffects.runtime_registry import runtime_functions
from liberadronecore.ledeffects.nodes.sampler import le_image

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
    if getattr(socket, "bl_idname", "") == "NodeSocketVector":
        return "(0.0, 0.0, 0.0)"
    if getattr(socket, "bl_idname", "") == "NodeSocketString":
        return "''"
    if getattr(socket, "bl_idname", "") == "NodeSocketObject":
        return "None"
    if getattr(socket, "bl_idname", "") == "NodeSocketCollection":
        return "None"
    if getattr(socket, "bl_idname", "") == "LDLEDEntrySocket":
        return "_entry_empty()"
    if getattr(socket, "bl_idname", "") == "LDLEDIDSocket":
        return "None"
    return "0.0"


def _default_for_input(socket: bpy.types.NodeSocket) -> str:
    if hasattr(socket, "default_value"):
        value = socket.default_value
        if isinstance(value, bpy.types.Object):
            return repr(value.name)
        if isinstance(value, bpy.types.Collection):
            return repr(value.name)
        if isinstance(value, bpy.types.Image):
            return repr(value.name)
        if isinstance(value, (float, int)):
            return repr(float(value))
        if isinstance(value, (list, tuple, mathutils.Vector)) or (
            hasattr(value, "__iter__") and not isinstance(value, (str, bytes))
        ):
            return repr(tuple(float(v) for v in value))
    return _default_for_socket(socket)


def _get_output_var(node: bpy.types.Node, socket: bpy.types.NodeSocket) -> str:
    override = le_codegen_base.get_codegen_output_vars_override(node)
    if override and socket.name in override:
        return override[socket.name]
    mapping = getattr(node, "_codegen_output_vars", {})
    if socket.name in mapping:
        return mapping[socket.name]
    node_id = _sanitize_identifier(getattr(node, "name", "") or node.bl_idname)
    return f"{node_id}_{_sanitize_identifier(socket.name)}"


def _collect_outputs(tree: bpy.types.NodeTree) -> List[bpy.types.Node]:
    outputs = [n for n in tree.nodes if n.bl_idname == "LDLEDOutputNode"]
    outputs.sort(key=lambda n: (getattr(n, "priority", 0), n.name))
    return outputs


def _output_seed(name: str) -> float:
    seed = 0
    for ch in name or "":
        seed = (seed * 131 + ord(ch)) % 100000
    return float(seed)


def compile_led_effect(tree: bpy.types.NodeTree) -> Optional[Callable]:
    outputs = _collect_outputs(tree)
    if not outputs:
        return None

    output_counts: Dict[int, int] = {}
    for output in outputs:
        priority = int(getattr(output, "priority", 0))
        output_counts[priority] = output_counts.get(priority, 0) + 1
    output_indices = {priority: 0 for priority in output_counts}

    lines: List[str] = []

    def emit_node(
        node: bpy.types.Node,
        target_lines: List[str],
        emitted_nodes: set[int],
        *,
        fallback_entry: Optional[str] = None,
        allow_entry_fallback: bool = True,
    ) -> None:
        if node.as_pointer() in emitted_nodes:
            return
        if not isinstance(node, LDLED_CodeNodeBase):
            return
        node_idname = getattr(node, "bl_idname", "")
        if node_idname == "LDLEDSwitchNode":
            emit_switch_node(
                node,
                target_lines,
                emitted_nodes,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            emitted_nodes.add(node.as_pointer())
            return
        if node_idname == "LDLEDValueCacheNode":
            emit_value_cache_node(
                node,
                target_lines,
                emitted_nodes,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            emitted_nodes.add(node.as_pointer())
            return

        inputs: Dict[str, str] = {}
        allowed_inputs = set(node.code_inputs())
        for sock in getattr(node, "inputs", []):
            if allowed_inputs is not None and sock.name not in allowed_inputs:
                continue
            inputs[sock.name] = resolve_input(
                sock,
                target_lines,
                emitted_nodes,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )

        output_vars = {
            sock.name: f"{node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(node, "outputs", [])
        }
        node._set_codegen_output_vars(output_vars)

        snippet = node.build_code(inputs) or ""
        for line in snippet.splitlines():
            target_lines.append(line)
        emitted_nodes.add(node.as_pointer())

    def resolve_input(
        socket: Optional[bpy.types.NodeSocket],
        target_lines: List[str],
        emitted_nodes: set[int],
        *,
        fallback_entry: Optional[str] = None,
        allow_entry_fallback: bool = True,
    ) -> str:
        if socket is None:
            return "0.0"
        is_entry = getattr(socket, "bl_idname", "") == "LDLEDEntrySocket"
        if is_entry and socket.is_linked and socket.links:
            entry_vars: List[str] = []
            for link in socket.links:
                if not getattr(link, "is_valid", True):
                    continue
                from_node = link.from_node
                from_socket = link.from_socket
                emit_node(
                    from_node,
                    target_lines,
                    emitted_nodes,
                    fallback_entry=fallback_entry,
                    allow_entry_fallback=allow_entry_fallback,
                )
                if isinstance(from_node, LDLED_CodeNodeBase):
                    entry_vars.append(_get_output_var(from_node, from_socket))
            if not entry_vars:
                return "_entry_empty()"
            if len(entry_vars) == 1:
                return entry_vars[0]
            merge_var = f"_entry_merge_{len(target_lines)}"
            target_lines.append(f"{merge_var} = _entry_empty()")
            for entry_var in entry_vars:
                target_lines.append(f"{merge_var} = _entry_merge({merge_var}, {entry_var})")
            return merge_var
        if socket.is_linked and socket.links:
            link = socket.links[0]
            if not getattr(link, "is_valid", True):
                return _default_for_input(socket)
            from_node = link.from_node
            from_socket = link.from_socket
            emit_node(
                from_node,
                target_lines,
                emitted_nodes,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            if isinstance(from_node, LDLED_CodeNodeBase):
                return _get_output_var(from_node, from_socket)
            return _default_for_socket(from_socket)
        if is_entry:
            if allow_entry_fallback and fallback_entry is not None:
                return fallback_entry
            return "_entry_empty()"
        return _default_for_input(socket)

    def emit_node_inline(
        dep_node: bpy.types.Node,
        inline_lines: List[str],
        inline_emitted: set[int],
        *,
        fallback_entry: Optional[str] = None,
        allow_entry_fallback: bool = True,
    ) -> None:
        if dep_node.as_pointer() in inline_emitted:
            return
        if not isinstance(dep_node, LDLED_CodeNodeBase):
            return

        inputs: Dict[str, str] = {}
        allowed_inputs = set(dep_node.code_inputs())
        for sock in getattr(dep_node, "inputs", []):
            if allowed_inputs is not None and sock.name not in allowed_inputs:
                continue
            inputs[sock.name] = resolve_input_inline(
                sock,
                inline_lines,
                inline_emitted,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )

        output_vars = {
            sock.name: f"{dep_node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(dep_node, "outputs", [])
        }
        dep_node._set_codegen_output_vars(output_vars)

        snippet = dep_node.build_code(inputs) or ""
        for line in snippet.splitlines():
            inline_lines.append(line)
        inline_emitted.add(dep_node.as_pointer())

    def resolve_input_inline(
        socket: Optional[bpy.types.NodeSocket],
        inline_lines: List[str],
        inline_emitted: set[int],
        *,
        fallback_entry: Optional[str] = None,
        allow_entry_fallback: bool = True,
    ) -> str:
        if socket is None:
            return "0.0"
        is_entry = getattr(socket, "bl_idname", "") == "LDLEDEntrySocket"
        if is_entry and socket.is_linked and socket.links:
            entry_vars: List[str] = []
            for link in socket.links:
                if not getattr(link, "is_valid", True):
                    continue
                from_node = link.from_node
                from_socket = link.from_socket
                emit_node_inline(
                    from_node,
                    inline_lines,
                    inline_emitted,
                    fallback_entry=fallback_entry,
                    allow_entry_fallback=allow_entry_fallback,
                )
                if isinstance(from_node, LDLED_CodeNodeBase):
                    entry_vars.append(_get_output_var(from_node, from_socket))
            if not entry_vars:
                return "_entry_empty()"
            if len(entry_vars) == 1:
                return entry_vars[0]
            merge_var = f"_entry_merge_{len(inline_lines)}"
            inline_lines.append(f"{merge_var} = _entry_empty()")
            for entry_var in entry_vars:
                inline_lines.append(f"{merge_var} = _entry_merge({merge_var}, {entry_var})")
            return merge_var
        if socket.is_linked and socket.links:
            link = socket.links[0]
            if not getattr(link, "is_valid", True):
                return _default_for_input(socket)
            from_node = link.from_node
            from_socket = link.from_socket
            emit_node_inline(
                from_node,
                inline_lines,
                inline_emitted,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            if isinstance(from_node, LDLED_CodeNodeBase):
                return _get_output_var(from_node, from_socket)
            return _default_for_socket(from_socket)
        if is_entry:
            if allow_entry_fallback and fallback_entry is not None:
                return fallback_entry
            return "_entry_empty()"
        return _default_for_input(socket)

    def _emit_value_select(
        index_var: str,
        target_var: str,
        value_sockets: List[Optional[bpy.types.NodeSocket]],
        target_lines: List[str],
        *,
        fallback_entry: Optional[str],
        allow_entry_fallback: bool,
        indent: str = "",
    ) -> None:
        first = True
        for idx, sock in enumerate(value_sockets):
            inline_lines: List[str] = []
            inline_emitted: set[int] = set()
            expr = "0.0"
            if sock is not None:
                expr = resolve_input_inline(
                    sock,
                    inline_lines,
                    inline_emitted,
                    fallback_entry=fallback_entry,
                    allow_entry_fallback=allow_entry_fallback,
                )
            keyword = "if" if first else "elif"
            target_lines.append(f"{indent}{keyword} {index_var} == {idx}:")
            for line in inline_lines:
                target_lines.append(f"{indent}    {line}")
            target_lines.append(f"{indent}    {target_var} = {expr}")
            first = False
        target_lines.append(f"{indent}else:")
        target_lines.append(f"{indent}    {target_var} = 0.0")

    def emit_switch_node(
        node: bpy.types.Node,
        target_lines: List[str],
        emitted_nodes: set[int],
        *,
        fallback_entry: Optional[str],
        allow_entry_fallback: bool,
    ) -> None:
        output_vars = {
            sock.name: f"{node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(node, "outputs", [])
        }
        node._set_codegen_output_vars(output_vars)
        out_var = node.output_var("Value")

        count = max(1, int(getattr(node, "input_count", 2)))
        name_fn = getattr(node, "_value_socket_names", None)
        if name_fn is None:
            return
        names = name_fn(count)
        value_sockets = [node.inputs.get(name) for name in names]
        switch_id = f"{node.codegen_id()}_{int(node.as_pointer())}"

        mode = getattr(node, "switch_mode", "ENTRY")
        if mode == "VALUE":
            switch_socket = node.inputs.get("Switch ID") if hasattr(node, "inputs") else None
            switch_expr = resolve_input(
                switch_socket,
                target_lines,
                emitted_nodes,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            target_lines.append(f"_idx_{switch_id} = int({switch_expr}) % {count}")
            _emit_value_select(
                f"_idx_{switch_id}",
                f"_val_{switch_id}",
                value_sockets,
                target_lines,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            target_lines.append(f"{out_var} = _val_{switch_id}")
            return

        entry_socket = node.inputs.get("Entry") if hasattr(node, "inputs") else None
        entry_expr = resolve_input(
            entry_socket,
            target_lines,
            emitted_nodes,
            fallback_entry=fallback_entry,
            allow_entry_fallback=allow_entry_fallback,
        )
        step_frames = int(getattr(node, "step_frames", 1))
        fade_mode = getattr(node, "fade_mode", "NONE")
        fade_frames = float(getattr(node, "fade_frames", 0.0))
        target_lines.append(
            f"_idx_{switch_id}, _fade_{switch_id} = "
            f"_switch_eval_fade({entry_expr}, frame, {step_frames}, {count}, "
            f"{fade_mode!r}, {fade_frames})"
        )
        _emit_value_select(
            f"_idx_{switch_id}",
            f"_val_{switch_id}",
            value_sockets,
            target_lines,
            fallback_entry=fallback_entry,
            allow_entry_fallback=allow_entry_fallback,
        )
        target_lines.append(f"{out_var} = _val_{switch_id} * _fade_{switch_id}")

    def emit_value_cache_node(
        node: bpy.types.Node,
        target_lines: List[str],
        emitted_nodes: set[int],
        *,
        fallback_entry: Optional[str],
        allow_entry_fallback: bool,
    ) -> None:
        output_vars = {
            sock.name: f"{node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(node, "outputs", [])
        }
        node._set_codegen_output_vars(output_vars)
        out_var = node.output_var("Value")

        cache_key = f"{node.id_data.name}::{node.name}"
        cache_id = int(node.as_pointer())
        cache_mode = getattr(node, "cache_mode", "SINGLE")
        fid_expr = "_formation_id(idx)"

        if cache_mode == "ENTRY":
            entry_socket = node.inputs.get("Entry") if hasattr(node, "inputs") else None
            entry_expr = resolve_input(
                entry_socket,
                target_lines,
                emitted_nodes,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            target_lines.append(f"_active_{cache_id} = _entry_active_count({entry_expr}, frame)")
            target_lines.append(f"if _entry_is_empty({entry_expr}):")
            target_lines.append(f"    _active_{cache_id} = 1")
            target_lines.append(f"if _active_{cache_id} > 0:")
            target_lines.append(f"    if _value_cache_has({cache_key!r}):")
            target_lines.append(f"        _progress_{cache_id} = _entry_progress({entry_expr}, frame)")
            target_lines.append(
                f"        {out_var} = _value_cache_read_entry({cache_key!r}, {fid_expr}, _progress_{cache_id})"
            )
            target_lines.append("    else:")
            inline_lines: List[str] = []
            inline_emitted: set[int] = set()
            value_socket = node.inputs.get("Value") if hasattr(node, "inputs") else None
            value_expr = resolve_input_inline(
                value_socket,
                inline_lines,
                inline_emitted,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            for line in inline_lines:
                target_lines.append(f"        {line}")
            target_lines.append(f"        {out_var} = {value_expr}")
            target_lines.append("else:")
            target_lines.append(f"    {out_var} = 0.0")
            return

        target_lines.append(f"if _value_cache_has({cache_key!r}):")
        target_lines.append(f"    {out_var} = _value_cache_read({cache_key!r}, {fid_expr})")
        target_lines.append("else:")
        inline_lines = []
        inline_emitted = set()
        value_socket = node.inputs.get("Value") if hasattr(node, "inputs") else None
        value_expr = resolve_input_inline(
            value_socket,
            inline_lines,
            inline_emitted,
            fallback_entry=fallback_entry,
            allow_entry_fallback=allow_entry_fallback,
        )
        for line in inline_lines:
            target_lines.append(f"    {line}")
        target_lines.append(f"    {out_var} = {value_expr}")

    output_meta_blocks: Dict[str, List[str]] = {}
    output_color_blocks: Dict[str, List[str]] = {}

    for output in outputs:
        out_key = output.name
        meta_lines: List[str] = []
        meta_emitted: set[int] = set()
        entry_in = resolve_input(
            output.inputs.get("Entry"),
            meta_lines,
            meta_emitted,
            allow_entry_fallback=False,
        )
        intensity_in = resolve_input(
            output.inputs.get("Intensity"),
            meta_lines,
            meta_emitted,
            fallback_entry=entry_in,
        )
        alpha_in = resolve_input(
            output.inputs.get("Alpha"),
            meta_lines,
            meta_emitted,
            fallback_entry=entry_in,
        )
        meta_lines.append(f"_intensity = {intensity_in}")
        meta_lines.append(f"_alpha = {alpha_in}")
        meta_lines.append(f"_entry = {entry_in}")
        output_meta_blocks[out_key] = meta_lines

        color_lines: List[str] = []
        color_emitted: set[int] = set()
        color_in = resolve_input(
            output.inputs.get("Color"),
            color_lines,
            color_emitted,
            fallback_entry="_entry",
        )
        color_lines.append(f"_color = {color_in}")
        output_color_blocks[out_key] = color_lines

    lines.append("_output_items = []")

    for output in outputs:
        out_key = output.name
        priority = int(getattr(output, "priority", 0))
        group_index = output_indices[priority]
        group_size = output_counts[priority]
        output_indices[priority] = group_index + 1
        blend_mode = getattr(output, "blend_mode", "MIX") or "MIX"
        random_weight = float(getattr(output, "random", 0.0))
        random_weight = max(0.0, min(1.0, random_weight))
        seed = _output_seed(output.name)
        lines.append(
            "_output_items.append(({0}, {1}, {2}, {3}, {4}, {5}, {6}))"
            .format(
                priority,
                group_index,
                group_size,
                repr(random_weight),
                repr(blend_mode),
                repr(seed),
                repr(out_key),
            )
        )

    lines.append("_ordered_outputs = []")
    lines.append("for _prio, _group_idx, _group_size, _rand, _blend, _seed, _out_id in _output_items:")
    lines.append("    _order = _group_idx")
    lines.append("    if _rand > 0.0:")
    lines.append("        _roll = _rand01_static(idx, _seed)")
    lines.append("        if _roll < _rand:")
    lines.append("            _order = _rand01_static(idx, _seed + 1.0) * _group_size")
    lines.append("    _ordered_outputs.append((_prio, _order, _group_idx, _blend, _out_id))")
    lines.append("_ordered_outputs.sort(key=lambda item: (item[0], item[1], item[2]))")
    lines.append("_meta = {}")
    lines.append("_max_opaque_prio = None")
    lines.append("for _prio, _order, _group_idx, _blend, _out_id in _ordered_outputs:")
    first = True
    for out_key, meta_lines in output_meta_blocks.items():
        keyword = "if" if first else "elif"
        lines.append(f"    {keyword} _out_id == {out_key!r}:")
        for line in meta_lines:
            lines.append(f"        {line}")
        first = False
    lines.append("    else:")
    lines.append("        _intensity = 0.0")
    lines.append("        _alpha = 0.0")
    lines.append("        _entry = _entry_empty()")
    lines.append("    _entry_count = _entry_active_count(_entry, frame)")
    lines.append("    if _entry_is_empty(_entry):")
    lines.append("        _entry_count = 1")
    lines.append("    _meta[_out_id] = (_intensity, _alpha, _entry, _entry_count)")
    lines.append("    if _blend == \"MIX\" and _entry_count > 0 and _intensity >= 1.0 and _alpha >= 1.0:")
    lines.append("        if _max_opaque_prio is None or _prio > _max_opaque_prio:")
    lines.append("            _max_opaque_prio = _prio")

    lines.append("for _prio, _order, _group_idx, _blend, _out_id in _ordered_outputs:")
    lines.append("    if _max_opaque_prio is not None and _prio < _max_opaque_prio:")
    lines.append("        continue")
    lines.append("    _meta_vals = _meta.get(_out_id)")
    lines.append("    if _meta_vals is None:")
    lines.append("        continue")
    lines.append("    _intensity, _alpha, _entry, _entry_count = _meta_vals")
    lines.append("    if _entry_count <= 0 or _intensity <= 0.0 or _alpha <= 0.0:")
    lines.append("        continue")
    first = True
    for out_key, color_lines in output_color_blocks.items():
        keyword = "if" if first else "elif"
        lines.append(f"    {keyword} _out_id == {out_key!r}:")
        for line in color_lines:
            lines.append(f"        {line}")
        first = False
    lines.append("    else:")
    lines.append("        _color = (0.0, 0.0, 0.0, 1.0)")
    lines.append("    _src_alpha = _clamp01(_alpha * (_color[3] if len(_color) > 3 else 1.0))")
    lines.append("    if _src_alpha <= 0.0:")
    lines.append("        continue")
    lines.append("    _src_color = [_color[0] * _intensity, _color[1] * _intensity, _color[2] * _intensity, 1.0]")
    lines.append("    for _ in range(int(_entry_count)):")
    lines.append("        color = _blend_over(color, _src_color, _src_alpha, _blend)")

    body = ["def _led_effect(idx, pos, frame):", "    color = [0.0, 0.0, 0.0, 1.0]"]
    body.extend([f"    {line}" for line in lines])
    body.append("    return color")

    code = "\n".join(body)
    env = {"bpy": bpy, "math": math, "mathutils": mathutils}
    env.update(runtime_functions())
    exec(code, env)
    le_image._prewarm_tree_images(tree)
    return env["_led_effect"]


def compile_led_socket(
    tree: bpy.types.NodeTree,
    node: bpy.types.Node,
    socket_name: str,
    *,
    force_inputs: bool = False,
) -> Optional[Callable]:
    if tree is None or node is None or not socket_name:
        return None
    le_image._prewarm_tree_images(tree)
    socket = node.inputs.get(socket_name) if hasattr(node, "inputs") else None
    if socket is None:
        return None

    lines: List[str] = []
    emitted: set[int] = set()

    def emit_node(
        dep_node: bpy.types.Node,
        target_lines: List[str],
        emitted_nodes: set[int],
    ) -> None:
        if dep_node.as_pointer() in emitted_nodes:
            return
        if not isinstance(dep_node, LDLED_CodeNodeBase):
            return

        inputs: Dict[str, str] = {}
        allowed_inputs = None
        if not force_inputs:
            allowed_inputs = set(dep_node.code_inputs())
        for sock in getattr(dep_node, "inputs", []):
            if allowed_inputs is not None and sock.name not in allowed_inputs:
                continue
            inputs[sock.name] = resolve_input(sock, target_lines, emitted_nodes)

        output_vars = {
            sock.name: f"{dep_node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(dep_node, "outputs", [])
        }
        dep_node._set_codegen_output_vars(output_vars)

        snippet = dep_node.build_code(inputs) or ""
        for line in snippet.splitlines():
            target_lines.append(line)
        emitted_nodes.add(dep_node.as_pointer())

    def resolve_input(
        dep_socket: Optional[bpy.types.NodeSocket],
        target_lines: List[str],
        emitted_nodes: set[int],
    ) -> str:
        if dep_socket is None:
            return "0.0"
        is_entry = getattr(dep_socket, "bl_idname", "") == "LDLEDEntrySocket"
        if is_entry and dep_socket.is_linked and dep_socket.links:
            entry_vars: List[str] = []
            for link in dep_socket.links:
                if not getattr(link, "is_valid", True):
                    continue
                from_node = link.from_node
                from_socket = link.from_socket
                emit_node(from_node, target_lines, emitted_nodes)
                if isinstance(from_node, LDLED_CodeNodeBase):
                    entry_vars.append(_get_output_var(from_node, from_socket))
            if not entry_vars:
                return "_entry_empty()"
            if len(entry_vars) == 1:
                return entry_vars[0]
            merge_var = f"_entry_merge_{len(target_lines)}"
            target_lines.append(f"{merge_var} = _entry_empty()")
            for entry_var in entry_vars:
                target_lines.append(f"{merge_var} = _entry_merge({merge_var}, {entry_var})")
            return merge_var
        if dep_socket.is_linked and dep_socket.links:
            link = dep_socket.links[0]
            if not getattr(link, "is_valid", True):
                return _default_for_input(dep_socket)
            from_node = link.from_node
            from_socket = link.from_socket
            emit_node(from_node, target_lines, emitted_nodes)
            if isinstance(from_node, LDLED_CodeNodeBase):
                return _get_output_var(from_node, from_socket)
            return _default_for_socket(from_socket)
        if is_entry:
            return "_entry_empty()"
        return _default_for_input(dep_socket)

    value_expr = resolve_input(socket, lines, emitted)
    lines.append(f"_value = {value_expr}")

    body = ["def _led_socket(idx, pos, frame):"]
    body.extend([f"    {line}" for line in lines])
    body.append("    return _value")

    code = "\n".join(body)
    env = {"bpy": bpy, "math": math, "mathutils": mathutils}
    env.update(runtime_functions())
    exec(code, env)
    return env["_led_socket"]


def get_output_activity(tree: bpy.types.NodeTree, frame: float) -> Dict[str, bool]:
    outputs = _collect_outputs(tree)
    if not outputs:
        return {}

    emitted: set[int] = set()
    lines: List[str] = []

    def emit_node(node: bpy.types.Node) -> None:
        if node.as_pointer() in emitted:
            return
        if not isinstance(node, LDLED_CodeNodeBase):
            return

        inputs: Dict[str, str] = {}
        allowed_inputs = set(node.code_inputs())
        for sock in getattr(node, "inputs", []):
            if allowed_inputs is not None and sock.name not in allowed_inputs:
                continue
            inputs[sock.name] = resolve_input(sock)

        output_vars = {
            sock.name: f"{node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(node, "outputs", [])
        }
        le_codegen_base.set_codegen_output_vars_override(node, output_vars)

        snippet = node.build_code(inputs) or ""
        for line in snippet.splitlines():
            lines.append(line)
        emitted.add(node.as_pointer())

    def resolve_input(socket: Optional[bpy.types.NodeSocket]) -> str:
        if socket is None:
            return "0.0"
        is_entry = getattr(socket, "bl_idname", "") == "LDLEDEntrySocket"
        if is_entry and socket.is_linked and socket.links:
            entry_vars: List[str] = []
            for link in socket.links:
                if not getattr(link, "is_valid", True):
                    continue
                from_node = link.from_node
                from_socket = link.from_socket
                emit_node(from_node)
                if isinstance(from_node, LDLED_CodeNodeBase):
                    entry_vars.append(_get_output_var(from_node, from_socket))
            if not entry_vars:
                return "_entry_empty()"
            if len(entry_vars) == 1:
                return entry_vars[0]
            merge_var = f"_entry_merge_{len(lines)}"
            lines.append(f"{merge_var} = _entry_empty()")
            for entry_var in entry_vars:
                lines.append(f"{merge_var} = _entry_merge({merge_var}, {entry_var})")
            return merge_var
        if socket.is_linked and socket.links:
            link = socket.links[0]
            if not getattr(link, "is_valid", True):
                return _default_for_input(socket)
            from_node = link.from_node
            from_socket = link.from_socket
            emit_node(from_node)
            if isinstance(from_node, LDLED_CodeNodeBase):
                return _get_output_var(from_node, from_socket)
            return _default_for_socket(from_socket)
        if is_entry:
            return "_entry_empty()"
        return _default_for_input(socket)

    for output in outputs:
        entry_in = resolve_input(output.inputs.get("Entry"))
        out_id = _sanitize_identifier(output.name)
        lines.append(f"_entry_{out_id} = {entry_in}")
        lines.append(f"_entry_count_{out_id} = _entry_active_count(_entry_{out_id}, frame)")
        lines.append(f"if _entry_is_empty(_entry_{out_id}):")
        lines.append(f"    _entry_count_{out_id} = 1")
        lines.append(f"result[{output.name!r}] = int(_entry_count_{out_id})")

    body = ["def _led_output_activity(frame):", "    result = {}"]
    body.extend([f"    {line}" for line in lines])
    body.append("    return result")

    code = "\n".join(body)
    env = {"bpy": bpy, "math": math, "mathutils": mathutils}
    env.update(runtime_functions())
    exec(code, env)
    counts = env["_led_output_activity"](float(frame))
    return {name: bool(count) for name, count in counts.items()}


_TREE_CACHE: Dict[int, Tuple[Callable, Any]] = {}


def _to_hashable(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bpy.types.ID):
        return value.name
    if isinstance(value, (list, tuple, mathutils.Vector, mathutils.Color)):
        return tuple(_to_hashable(v) for v in value)
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        return tuple(_to_hashable(v) for v in value)
    return repr(value)


def _node_signature(node: bpy.types.Node):
    props = []
    for prop in node.bl_rna.properties:
        ident = prop.identifier
        if ident == "rna_type":
            continue
        val = getattr(node, ident)
        props.append((ident, _to_hashable(val)))
    inputs = []
    for sock in getattr(node, "inputs", []):
        val = sock.default_value if hasattr(sock, "default_value") else None
        inputs.append((sock.name, getattr(sock, "bl_idname", ""), _to_hashable(val)))
    return (node.bl_idname, node.name, node.label, tuple(props), tuple(inputs))


def _tree_signature(tree: bpy.types.NodeTree):
    nodes = sorted(getattr(tree, "nodes", []), key=lambda n: n.name)
    links = []
    for link in getattr(tree, "links", []):
        if not getattr(link, "is_valid", True):
            continue
        from_node = getattr(link, "from_node", None)
        to_node = getattr(link, "to_node", None)
        from_socket = getattr(link, "from_socket", None)
        to_socket = getattr(link, "to_socket", None)
        if not (from_node and to_node and from_socket and to_socket):
            continue
        links.append((from_node.name, from_socket.name, to_node.name, to_socket.name))
    links.sort()
    return (tuple(_node_signature(n) for n in nodes), tuple(links))


def get_compiled_effect(tree: bpy.types.NodeTree) -> Optional[Callable]:
    key = tree.as_pointer()
    sig = _tree_signature(tree)
    cached = _TREE_CACHE.get(key)
    if cached and cached[1] == sig:
        return cached[0]
    compiled = compile_led_effect(tree)
    if compiled is not None:
        _TREE_CACHE[key] = (compiled, sig)
    return compiled


def get_active_tree(scene: bpy.types.Scene) -> Optional[bpy.types.NodeTree]:
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", "") == "LD_LedEffectsTree":
            return tree
    return None

