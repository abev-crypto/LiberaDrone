import bpy

from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.ledeffects import led_codegen_runtime
import json
import os

_LED_OUTPUT_ACTIVITY: dict[str, bool] = {}
_LED_OUTPUT_SYNC_PENDING = False
_UNSUPPORTED = object()
_LED_TEMPLATE_GLOB = ".json"


def _template_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ledeffects", "sample"))


def _list_template_files() -> list[tuple[str, str]]:
    folder = _template_dir()
    if not os.path.isdir(folder):
        return []
    results = []
    try:
        for entry in os.listdir(folder):
            if not entry.lower().endswith(_LED_TEMPLATE_GLOB):
                continue
            path = os.path.join(folder, entry)
            if os.path.isfile(path):
                results.append((os.path.splitext(entry)[0], path))
    except Exception:
        return []
    results.sort(key=lambda item: item[0].lower())
    return results


def _encode_value(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bpy.types.ID):
        return {"__id__": value.__class__.__name__, "name": value.name}
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        try:
            return [float(v) for v in value]
        except Exception:
            return _UNSUPPORTED
    return _UNSUPPORTED


def _resolve_id_ref(data):
    if not isinstance(data, dict):
        return data
    if "__id__" not in data:
        return data
    name = data.get("name", "")
    id_type = data.get("__id__", "")
    pools = {
        "Object": bpy.data.objects,
        "Collection": bpy.data.collections,
        "Image": bpy.data.images,
        "Texture": bpy.data.textures,
        "Material": bpy.data.materials,
        "World": bpy.data.worlds,
        "Text": bpy.data.texts,
        "NodeTree": bpy.data.node_groups,
    }
    pool = pools.get(id_type)
    if pool is None:
        return None
    return pool.get(name)


def _decode_value(value):
    if isinstance(value, dict):
        resolved = _resolve_id_ref(value)
        if resolved is not value:
            return resolved
    if isinstance(value, list):
        return tuple(value)
    return value


def _encode_node_properties(node: bpy.types.Node) -> dict:
    props: dict[str, object] = {}
    for prop in node.bl_rna.properties:
        ident = prop.identifier
        if ident in {"rna_type", "name", "label", "location", "color_ramp_tex"}:
            continue
        if getattr(prop, "is_readonly", False):
            continue
        try:
            value = getattr(node, ident)
        except Exception:
            continue
        encoded = _encode_value(value)
        if encoded is _UNSUPPORTED:
            continue
        props[ident] = encoded
    return props


def _encode_socket_defaults(node: bpy.types.Node) -> list[dict[str, object]]:
    defaults: list[dict[str, object]] = []
    for sock in getattr(node, "inputs", []):
        if not hasattr(sock, "default_value"):
            continue
        try:
            encoded = _encode_value(sock.default_value)
        except Exception:
            continue
        if encoded is _UNSUPPORTED:
            continue
        defaults.append({"name": sock.name, "default": encoded})
    return defaults


def _apply_node_properties(node: bpy.types.Node, props: dict) -> None:
    for ident, raw in (props or {}).items():
        try:
            setattr(node, ident, _decode_value(raw))
        except Exception:
            continue


def _apply_socket_defaults(node: bpy.types.Node, defaults: list[dict]) -> None:
    for entry in defaults or []:
        name = entry.get("name")
        if not name:
            continue
        sock = node.inputs.get(name) if hasattr(node, "inputs") else None
        if sock is None or not hasattr(sock, "default_value"):
            continue
        try:
            sock.default_value = _decode_value(entry.get("default"))
        except Exception:
            continue


def _apply_color_ramp(node: bpy.types.Node, data: dict | None) -> None:
    if not data:
        return
    tex_name = data.get("name") or f"{node.name}_ColorRamp"
    tex = getattr(node, "color_ramp_tex", None)
    if tex is None:
        tex = bpy.data.textures.get(tex_name)
    if tex is None:
        try:
            tex = bpy.data.textures.new(name=tex_name, type='BLEND')
        except Exception:
            return
    tex.use_color_ramp = True
    try:
        node.color_ramp_tex = tex
    except Exception:
        pass
    ramp = getattr(tex, "color_ramp", None)
    if ramp is None:
        return
    elements = data.get("elements") or []
    if elements:
        while len(ramp.elements) < len(elements):
            ramp.elements.new(0.5)
        while len(ramp.elements) > len(elements):
            ramp.elements.remove(ramp.elements[-1])
        for idx, elem_data in enumerate(elements):
            if idx >= len(ramp.elements):
                break
            elem = ramp.elements[idx]
            try:
                elem.position = float(elem_data.get("position", elem.position))
            except Exception:
                pass
            color = elem_data.get("color")
            if isinstance(color, (list, tuple)) and len(color) >= 4:
                try:
                    elem.color = [float(c) for c in color[:4]]
                except Exception:
                    pass
    interp = data.get("interpolation")
    if interp:
        try:
            ramp.interpolation = interp
        except Exception:
            pass
    mode = data.get("color_mode")
    if mode:
        try:
            ramp.color_mode = mode
        except Exception:
            pass


def _collect_subgraph_nodes(output_node: bpy.types.Node) -> list[bpy.types.Node]:
    visited: set[bpy.types.Node] = set()
    stack = [output_node]
    result: list[bpy.types.Node] = []
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        result.append(node)
        for sock in getattr(node, "inputs", []):
            for link in getattr(sock, "links", []):
                if not getattr(link, "is_valid", True):
                    continue
                from_node = getattr(link, "from_node", None)
                if from_node is not None:
                    stack.append(from_node)
    return result


def _serialize_led_graph(output_node: bpy.types.Node) -> dict:
    tree = output_node.id_data
    nodes = _collect_subgraph_nodes(output_node)
    node_set = set(nodes)
    node_data = []
    for node in nodes:
        loc = getattr(node, "location", None)
        loc_val = [float(loc.x), float(loc.y)] if loc is not None else [0.0, 0.0]
        color_ramp = None
        tex = getattr(node, "color_ramp_tex", None)
        if tex is not None and getattr(tex, "color_ramp", None) is not None:
            ramp = tex.color_ramp
            elements = [
                {
                    "position": float(elem.position),
                    "color": [float(c) for c in elem.color],
                }
                for elem in ramp.elements
            ]
            color_ramp = {
                "name": tex.name,
                "interpolation": ramp.interpolation,
                "color_mode": ramp.color_mode,
                "elements": elements,
            }
        node_data.append(
            {
                "name": node.name,
                "label": node.label,
                "bl_idname": node.bl_idname,
                "location": loc_val,
                "properties": _encode_node_properties(node),
                "inputs": _encode_socket_defaults(node),
                "color_ramp": color_ramp,
            }
        )
    links = []
    for link in getattr(tree, "links", []):
        if not getattr(link, "is_valid", True):
            continue
        from_node = link.from_node
        to_node = link.to_node
        if from_node not in node_set or to_node not in node_set:
            continue
        links.append(
            {
                "from_node": from_node.name,
                "from_socket": link.from_socket.name,
                "to_node": to_node.name,
                "to_socket": link.to_socket.name,
            }
        )
    return {
        "version": 1,
        "tree_type": "LD_LedEffectsTree",
        "root": output_node.name,
        "nodes": node_data,
        "links": links,
    }


def _build_led_graph(tree: bpy.types.NodeTree, payload: dict) -> bpy.types.Node | None:
    nodes_data = payload.get("nodes", [])
    if not nodes_data:
        return None
    existing_nodes = list(tree.nodes)
    node_map: dict[str, bpy.types.Node] = {}
    for data in nodes_data:
        bl_idname = data.get("bl_idname", "")
        if not bl_idname:
            continue
        try:
            node = tree.nodes.new(bl_idname)
        except Exception:
            continue
        name = data.get("name", "")
        if name:
            try:
                node.name = name
            except Exception:
                pass
        label = data.get("label", "")
        if label:
            try:
                node.label = label
            except Exception:
                pass
        loc = data.get("location")
        if isinstance(loc, (list, tuple)) and len(loc) >= 2:
            try:
                node.location = (float(loc[0]), float(loc[1]))
            except Exception:
                pass
        _apply_node_properties(node, data.get("properties", {}))
        _apply_socket_defaults(node, data.get("inputs", []))
        _apply_color_ramp(node, data.get("color_ramp"))
        node_map[data.get("name", node.name)] = node

    for link in payload.get("links", []):
        from_name = link.get("from_node")
        to_name = link.get("to_node")
        from_socket_name = link.get("from_socket")
        to_socket_name = link.get("to_socket")
        if not (from_name and to_name and from_socket_name and to_socket_name):
            continue
        from_node = node_map.get(from_name)
        to_node = node_map.get(to_name)
        if from_node is None or to_node is None:
            continue
        from_socket = from_node.outputs.get(from_socket_name) if hasattr(from_node, "outputs") else None
        to_socket = to_node.inputs.get(to_socket_name) if hasattr(to_node, "inputs") else None
        if from_socket is None or to_socket is None:
            continue
        try:
            tree.links.new(from_socket, to_socket)
        except Exception:
            continue

    root_name = payload.get("root", "")
    imported_nodes = list(node_map.values())
    if existing_nodes and imported_nodes:
        existing_x = [float(n.location.x) for n in existing_nodes if hasattr(n, "location")]
        existing_max_x = max(existing_x) if existing_x else 0.0
        new_x = [float(n.location.x) for n in imported_nodes if hasattr(n, "location")]
        new_min_x = min(new_x) if new_x else 0.0
        offset_x = (existing_max_x - new_min_x) + 300.0
        for node in imported_nodes:
            try:
                node.location.x += offset_x
            except Exception:
                pass

    if imported_nodes:
        frame = tree.nodes.new("NodeFrame")
        frame.label = payload.get("root", "Imported")
        frame.shrink = True
        xs = [float(n.location.x) for n in imported_nodes if hasattr(n, "location")]
        ys = [float(n.location.y) for n in imported_nodes if hasattr(n, "location")]
        if xs and ys:
            try:
                frame.location = (min(xs) - 60.0, max(ys) + 60.0)
            except Exception:
                pass
        for node in imported_nodes:
            if node == frame:
                continue
            try:
                node.parent = frame
            except Exception:
                pass

    return node_map.get(root_name)


def _get_led_tree(context) -> bpy.types.NodeTree | None:
    space = getattr(context, "space_data", None)
    if space and getattr(space, "edit_tree", None) and getattr(space, "tree_type", "") == "LD_LedEffectsTree":
        return space.edit_tree
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", "") == "LD_LedEffectsTree":
            return tree
    return None


def _ensure_led_tree(context) -> bpy.types.NodeTree | None:
    tree = _get_led_tree(context)
    if tree is not None:
        return tree
    tree = bpy.data.node_groups.new("LEDEffectsTree", "LD_LedEffectsTree")
    space = getattr(context, "space_data", None)
    if space and getattr(space, "type", "") == "NODE_EDITOR":
        try:
            space.tree_type = "LD_LedEffectsTree"
            space.node_tree = tree
        except Exception:
            pass
    return tree


def _schedule_output_sync(scene: bpy.types.Scene, tree: bpy.types.NodeTree) -> None:
    global _LED_OUTPUT_SYNC_PENDING
    if _LED_OUTPUT_SYNC_PENDING:
        return
    scene_name = scene.name if scene else ""
    tree_name = tree.name if tree else ""

    def _do_sync():
        global _LED_OUTPUT_SYNC_PENDING
        _LED_OUTPUT_SYNC_PENDING = False
        scn = bpy.data.scenes.get(scene_name)
        t = bpy.data.node_groups.get(tree_name)
        if scn is None or t is None:
            return None
        _sync_output_items(scn, t, allow_index_update=True, allow_write=True)
        return None

    _LED_OUTPUT_SYNC_PENDING = True
    bpy.app.timers.register(_do_sync, first_interval=0.0)


def _sync_output_items(
    scene: bpy.types.Scene,
    tree: bpy.types.NodeTree,
    *,
    allow_index_update: bool = True,
    allow_write: bool = True,
) -> None:
    items = scene.ld_led_output_items
    output_nodes = [n for n in tree.nodes if getattr(n, "bl_idname", "") == "LDLEDOutputNode"]
    output_names = {n.name for n in output_nodes}
    item_names = {item.node_name for item in items}

    if not allow_write:
        if item_names != output_names:
            _schedule_output_sync(scene, tree)
        return

    active_name = None
    if 0 <= scene.ld_led_output_index < len(items):
        active_name = items[scene.ld_led_output_index].node_name

    for idx in reversed(range(len(items))):
        if items[idx].node_name not in output_names:
            items.remove(idx)

    existing = {item.node_name for item in items}
    for node in output_nodes:
        if node.name not in existing:
            item = items.add()
            item.node_name = node.name

    if not allow_index_update:
        return

    target_index = scene.ld_led_output_index
    if active_name:
        for idx, item in enumerate(items):
            if item.node_name == active_name:
                target_index = idx
                break
        else:
            target_index = min(scene.ld_led_output_index, max(len(items) - 1, 0))
    else:
        target_index = min(scene.ld_led_output_index, max(len(items) - 1, 0))

    try:
        scene.ld_led_output_index = target_index
    except Exception:
        pass


def _set_active_output(context, node: bpy.types.Node) -> None:
    tree = getattr(node, "id_data", None)
    if tree is None:
        return
    for n in tree.nodes:
        n.select = False
    node.select = True
    tree.nodes.active = node
    if context and getattr(context, "space_data", None):
        try:
            context.space_data.node_tree = tree
        except Exception:
            pass


def _update_output_index(self, context):
    tree = _get_led_tree(context)
    if tree is None:
        return
    idx = int(getattr(self, "ld_led_output_index", 0))
    items = getattr(self, "ld_led_output_items", [])
    if idx < 0 or idx >= len(items):
        return
    node = tree.nodes.get(items[idx].node_name)
    if node is not None:
        _set_active_output(context, node)


def _node_editor_cursor(context) -> tuple[float, float]:
    space = getattr(context, "space_data", None)
    cursor = getattr(space, "cursor_location", None) if space else None
    if cursor is None:
        return (0.0, 0.0)
    try:
        return (float(cursor.x), float(cursor.y))
    except Exception:
        return (0.0, 0.0)


def _get_selected_output_node(context, tree: bpy.types.NodeTree) -> bpy.types.Node | None:
    if tree is None:
        return None
    scene = getattr(context, "scene", None)
    if scene is None:
        return None
    if 0 <= scene.ld_led_output_index < len(scene.ld_led_output_items):
        node_name = scene.ld_led_output_items[scene.ld_led_output_index].node_name
        node = tree.nodes.get(node_name)
        if node is not None:
            return node
    node = tree.nodes.active if tree else None
    if node is not None and getattr(node, "bl_idname", "") == "LDLEDOutputNode":
        return node
    return None


def _socket_display_name(sock: bpy.types.NodeSocket) -> str:
    name = getattr(sock, "name", "")
    return name if name else getattr(sock, "bl_idname", "Socket")


def _draw_socket_status(layout, sock: bpy.types.NodeSocket) -> None:
    icon = "LINKED" if getattr(sock, "is_linked", False) else "UNLINKED"
    row = layout.row(align=True)
    row.label(text="", icon=icon)
    if getattr(sock, "is_output", False):
        row.label(text=_socket_display_name(sock))
        return
    if getattr(sock, "is_linked", False):
        row.label(text=_socket_display_name(sock))
        return
    if hasattr(sock, "default_value"):
        row.prop(sock, "default_value", text=_socket_display_name(sock))
        return
    row.label(text=_socket_display_name(sock))


class LDLEDOutputItem(bpy.types.PropertyGroup):
    node_name: bpy.props.StringProperty(name="Output Node")


class LDLED_UL_OutputList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        tree = _get_led_tree(context)
        node = tree.nodes.get(item.node_name) if tree else None
        row = layout.row(align=True)
        is_active = bool(_LED_OUTPUT_ACTIVITY.get(item.node_name, False))
        row.alert = is_active
        row.label(text="", icon='CHECKMARK' if is_active else 'BLANK1')
        if node is None:
            row.label(text=item.node_name)
        else:
            row.prop(node, "name", text="")


class LDLED_OT_create_output_node(bpy.types.Operator):
    bl_idname = "ldled.create_output_node"
    bl_label = "CreateNode"
    bl_description = "Create LED Effects tree and add an Output node"

    def execute(self, context):
        tree = _ensure_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        node = tree.nodes.new("LDLEDOutputNode")
        node.location = (200.0, 0.0)
        _set_active_output(context, node)
        _sync_output_items(context.scene, tree)
        for idx, item in enumerate(context.scene.ld_led_output_items):
            if item.node_name == node.name:
                context.scene.ld_led_output_index = idx
                break
        return {'FINISHED'}


def _sanitize_filename(name: str) -> str:
    safe = []
    for ch in name or "":
        if ch.isalnum() or ch in {"_", "-"}:
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe).strip("_")
    return result or "led_template"


def _load_template_file(path: str) -> dict | None:
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


class LDLED_OT_export_template(bpy.types.Operator):
    bl_idname = "ldled.export_template"
    bl_label = "Export"
    bl_description = "Export the selected LED output node graph to JSON"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        tree = _get_led_tree(context)
        node = _get_selected_output_node(context, tree)
        if node is None:
            self.report({'ERROR'}, "Select an LED Output node")
            return {'CANCELLED'}
        base = _template_dir()
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        filename = _sanitize_filename(node.name) + ".json"
        self.filepath = os.path.join(base, filename)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = _get_led_tree(context)
        node = _get_selected_output_node(context, tree)
        if node is None:
            self.report({'ERROR'}, "Select an LED Output node")
            return {'CANCELLED'}
        payload = _serialize_led_graph(node)
        if not self.filepath:
            self.report({'ERROR'}, "Missing export path")
            return {'CANCELLED'}
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=True, indent=2)
        except Exception as exc:
            self.report({'ERROR'}, f"Export failed: {exc}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Exported: {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class LDLED_OT_import_template(bpy.types.Operator):
    bl_idname = "ldled.import_template"
    bl_label = "Import"
    bl_description = "Import an LED template JSON and build the node graph"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        base = _template_dir()
        if os.path.isdir(base):
            self.filepath = base
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = _ensure_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        payload = _load_template_file(self.filepath)
        if not payload:
            self.report({'ERROR'}, "Template load failed")
            return {'CANCELLED'}
        if payload.get("tree_type") != "LD_LedEffectsTree":
            self.report({'ERROR'}, "Invalid template type")
            return {'CANCELLED'}
        root = _build_led_graph(tree, payload)
        if root is not None:
            _set_active_output(context, root)
        _sync_output_items(context.scene, tree)
        return {'FINISHED'}


class LDLED_OT_build_template(bpy.types.Operator):
    bl_idname = "ldled.build_template"
    bl_label = "Build Template"
    bl_description = "Build an LED node template from the sample directory"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        tree = _ensure_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        payload = _load_template_file(self.filepath)
        if not payload:
            self.report({'ERROR'}, "Template load failed")
            return {'CANCELLED'}
        if payload.get("tree_type") != "LD_LedEffectsTree":
            self.report({'ERROR'}, "Invalid template type")
            return {'CANCELLED'}
        root = _build_led_graph(tree, payload)
        if root is not None:
            _set_active_output(context, root)
        _sync_output_items(context.scene, tree)
        return {'FINISHED'}


class LDLED_OT_add_frame(bpy.types.Operator):
    bl_idname = "ldled.add_frame"
    bl_label = "Frame"
    bl_description = "Wrap selected LED nodes in a frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        tree = _get_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        selected = [n for n in tree.nodes if n.select]
        frame = tree.nodes.new("NodeFrame")
        frame.label = "Frame"
        frame.shrink = True
        if selected:
            xs = [float(n.location.x) for n in selected if hasattr(n, "location")]
            ys = [float(n.location.y) for n in selected if hasattr(n, "location")]
            if xs and ys:
                frame.location = (min(xs) - 60.0, max(ys) + 60.0)
            for node in selected:
                if node == frame:
                    continue
                node.parent = frame
        else:
            frame.location = _node_editor_cursor(context)
        for node in tree.nodes:
            node.select = False
        frame.select = True
        tree.nodes.active = frame
        return {'FINISHED'}


class LDLED_OT_add_reroute(bpy.types.Operator):
    bl_idname = "ldled.add_reroute"
    bl_label = "Reroute"
    bl_description = "Add a reroute node at the cursor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        tree = _get_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        node = tree.nodes.new("NodeReroute")
        node.location = _node_editor_cursor(context)
        for n in tree.nodes:
            n.select = False
        node.select = True
        tree.nodes.active = node
        return {'FINISHED'}


class LDLED_OT_group_selected(bpy.types.Operator):
    bl_idname = "ldled.group_selected"
    bl_label = "Group"
    bl_description = "Group selected LED nodes (Output nodes are not allowed)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        tree = _get_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        selected = [n for n in tree.nodes if n.select]
        if not selected:
            self.report({'ERROR'}, "Select nodes to group")
            return {'CANCELLED'}
        if any(getattr(n, "bl_idname", "") == "LDLEDOutputNode" for n in selected):
            self.report({'ERROR'}, "Output nodes cannot be grouped")
            return {'CANCELLED'}
        if not bpy.ops.node.group_make.poll():
            self.report({'ERROR'}, "Grouping is not available in this editor")
            return {'CANCELLED'}
        for node in selected:
            tree.nodes.active = node
            break
        result = bpy.ops.node.group_make()
        if result != {'FINISHED'}:
            self.report({'ERROR'}, "Group creation failed")
            return {'CANCELLED'}
        return {'FINISHED'}


class LDLED_PT_panel(bpy.types.Panel):
    bl_label = "LED Effects"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "LED"

    @classmethod
    def poll(cls, context):
        space = getattr(context, "space_data", None)
        return bool(space and getattr(space, "tree_type", "") == "LD_LedEffectsTree")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        tree = _get_led_tree(context)

        layout.operator("ldled.create_output_node", text="CreateNode")
        row = layout.row(align=True)
        row.operator("ldled.add_frame", text="Frame")
        row.operator("ldled.add_reroute", text="Reroute")
        row.operator("ldled.group_selected", text="Group")
        templates = _list_template_files()
        if templates:
            col = layout.column(align=True)
            for label, path in templates:
                op = col.operator("ldled.build_template", text=label)
                op.filepath = path

        if tree is None:
            layout.label(text="No LED node tree", icon='ERROR')
            return

        _sync_output_items(scene, tree, allow_index_update=False, allow_write=False)
        global _LED_OUTPUT_ACTIVITY
        try:
            _LED_OUTPUT_ACTIVITY = led_codegen_runtime.get_output_activity(tree, scene.frame_current)
        except Exception:
            _LED_OUTPUT_ACTIVITY = {}

        layout.template_list(
            "LDLED_UL_OutputList",
            "",
            scene,
            "ld_led_output_items",
            scene,
            "ld_led_output_index",
            rows=4,
        )

        row = layout.row(align=True)
        row.operator("ldled.export_template", text="Export")
        row.operator("ldled.import_template", text="Import")

        node = _get_selected_output_node(context, tree)
        if node is not None and getattr(node, "bl_idname", "") == "LDLEDOutputNode":
            box = layout.box()
            box.label(text="Active Output")
            box.prop(node, "name", text="Name")
            if hasattr(node, "draw_buttons"):
                node.draw_buttons(context, box)

            socket_box = layout.box()
            socket_box.label(text="Sockets")
            if getattr(node, "inputs", None):
                socket_box.label(text="Inputs")
                for sock in node.inputs:
                    _draw_socket_status(socket_box, sock)
            if getattr(node, "outputs", None):
                socket_box.label(text="Outputs")
                for sock in node.outputs:
                    _draw_socket_status(socket_box, sock)


class LDLED_UI(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LDLEDOutputItem)
        bpy.utils.register_class(LDLED_UL_OutputList)
        bpy.utils.register_class(LDLED_OT_create_output_node)
        bpy.utils.register_class(LDLED_OT_export_template)
        bpy.utils.register_class(LDLED_OT_import_template)
        bpy.utils.register_class(LDLED_OT_build_template)
        bpy.utils.register_class(LDLED_OT_add_frame)
        bpy.utils.register_class(LDLED_OT_add_reroute)
        bpy.utils.register_class(LDLED_OT_group_selected)
        bpy.utils.register_class(LDLED_PT_panel)
        if not hasattr(bpy.types.Scene, "ld_led_output_items"):
            bpy.types.Scene.ld_led_output_items = bpy.props.CollectionProperty(type=LDLEDOutputItem)
        if not hasattr(bpy.types.Scene, "ld_led_output_index"):
            bpy.types.Scene.ld_led_output_index = bpy.props.IntProperty(
                name="Output Index",
                default=0,
                update=_update_output_index,
            )

    @classmethod
    def unregister(cls) -> None:
        if hasattr(bpy.types.Scene, "ld_led_output_index"):
            del bpy.types.Scene.ld_led_output_index
        if hasattr(bpy.types.Scene, "ld_led_output_items"):
            del bpy.types.Scene.ld_led_output_items
        bpy.utils.unregister_class(LDLED_PT_panel)
        bpy.utils.unregister_class(LDLED_OT_group_selected)
        bpy.utils.unregister_class(LDLED_OT_add_reroute)
        bpy.utils.unregister_class(LDLED_OT_add_frame)
        bpy.utils.unregister_class(LDLED_OT_build_template)
        bpy.utils.unregister_class(LDLED_OT_import_template)
        bpy.utils.unregister_class(LDLED_OT_export_template)
        bpy.utils.unregister_class(LDLED_OT_create_output_node)
        bpy.utils.unregister_class(LDLED_UL_OutputList)
        bpy.utils.unregister_class(LDLEDOutputItem)
