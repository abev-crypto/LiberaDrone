from __future__ import annotations

import bpy
from bpy.props import PointerProperty

from liberadronecore.formation.fn_nodecategory import FN_Node
from liberadronecore.system.transition import vat_gn, transition_apply
from liberadronecore.util import image_util


def _ensure_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
    elif col.name not in scene.collection.children:
        scene.collection.children.link(col)
    return col


def _link_object_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)


def _ensure_point_object(
    name: str,
    positions: list[tuple[float, float, float]],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != 'MESH':
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        obj = bpy.data.objects.new(name, mesh)
    else:
        mesh = obj.data
        if mesh is None or mesh.users > 1:
            mesh = bpy.data.meshes.new(f"{name}_Mesh")
            obj.data = mesh
    mesh.clear_geometry()
    mesh.from_pydata(positions, [], [])
    mesh.update()
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    return obj


def _order_by_pair_id(items, pair_ids):
    if pair_ids is None or len(items) != len(pair_ids):
        return items
    count = len(items)
    ordered = [None] * count
    for idx, pid in enumerate(pair_ids):
        if pid is None or pid < 0 or pid >= count:
            return items
        if ordered[pid] is not None:
            return items
        ordered[pid] = items[idx]
    if any(entry is None for entry in ordered):
        return items
    return ordered


def _ensure_image(name: str, width: int, height: int) -> bpy.types.Image:
    img = bpy.data.images.get(name)
    if img is not None:
        try:
            bpy.data.images.remove(img, do_unlink=True)
        except TypeError:
            try:
                bpy.data.images.remove(img)
            except Exception:
                pass
    img = bpy.data.images.new(name=name, width=width, height=height, alpha=True, float_buffer=True)
    try:
        img.colorspace_settings.name = "Non-Color"
    except Exception:
        pass
    return img


def _resolve_socket_value(node: bpy.types.Node, name: str, default):
    try:
        from liberadronecore.formation import fn_parse
    except Exception:
        return default
    return fn_parse._resolve_input_value(node, name, default)


def _iter_connected_nodes(sock: bpy.types.NodeSocket | None) -> list[bpy.types.Node]:
    if sock is None:
        return []
    nodes: list[bpy.types.Node] = []
    seen_nodes: set[int] = set()
    seen_reroutes: set[int] = set()
    stack = [sock]
    while stack:
        cur = stack.pop()
        for link in getattr(cur, "links", []):
            if hasattr(link, "is_valid") and not link.is_valid:
                continue
            target = getattr(link, "to_node", None)
            if target is None:
                continue
            if getattr(target, "bl_idname", "") == "NodeReroute":
                node_id = int(target.as_pointer()) if hasattr(target, "as_pointer") else id(target)
                if node_id in seen_reroutes:
                    continue
                seen_reroutes.add(node_id)
                for out_sock in getattr(target, "outputs", []):
                    stack.append(out_sock)
                continue
            node_id = int(target.as_pointer()) if hasattr(target, "as_pointer") else id(target)
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            nodes.append(target)
    return nodes


def _resolve_connected_range(node: bpy.types.Node, context) -> tuple[int, int] | None:
    out_sock = node.outputs.get("Collection") if hasattr(node, "outputs") else None
    targets = _iter_connected_nodes(out_sock)
    formation_ids = {
        "FN_ShowNode",
        "FN_TransitionNode",
        "FN_SplitTransitionNode",
        "FN_MergeTransitionNode",
    }
    targets = [t for t in targets if getattr(t, "bl_idname", "") in formation_ids]
    if not targets:
        return None
    try:
        from liberadronecore.formation import fn_parse
    except Exception:
        return None
    schedule = fn_parse.compute_schedule(context, assign_pairs=False)
    range_start = None
    range_end = None
    for target in targets:
        entry = None
        tree_name = getattr(getattr(target, "id_data", None), "name", "")
        for item in schedule:
            if item.node_name == target.name and item.tree_name == tree_name:
                entry = item
                break
        if entry is not None:
            start = int(entry.start)
            end = int(entry.end)
        else:
            start = getattr(target, "computed_start_frame", None)
            try:
                start = int(start)
            except Exception:
                start = None
            if start is None or start < 0:
                continue
            duration_value = fn_parse._resolve_input_value(target, "Duration", 0.0, "duration")
            try:
                duration = fn_parse._duration_frames(duration_value)
            except Exception:
                try:
                    duration = int(float(duration_value))
                except Exception:
                    duration = 0
            end = start + max(0, int(duration))
        if range_start is None or start < range_start:
            range_start = start
        if range_end is None or end > range_end:
            range_end = end
    if range_start is None or range_end is None or range_end <= range_start:
        return None
    return range_start, range_end - range_start


class FN_VATCacheNode(bpy.types.Node, FN_Node):
    bl_idname = "FN_VATCacheNode"
    bl_label = "VAT Cache"
    bl_icon = "FILE_CACHE"

    cache_collection: PointerProperty(type=bpy.types.Collection)

    def init(self, context):
        self.inputs.new("FN_SocketCollection", "Collection")
        self.outputs.new("FN_SocketCollection", "Collection")

    def draw_buttons(self, context, layout):
        op = layout.operator("fn.build_vat_cache", text="Build")
        op.node_name = self.name
        if self.cache_collection is not None:
            layout.prop(self, "cache_collection", text="Cached")

    def build_cache(self, context):
        scene = context.scene
        if scene is None:
            raise RuntimeError("No active scene.")
        source = _resolve_socket_value(self, "Collection", None)
        if not isinstance(source, bpy.types.Collection):
            raise RuntimeError("Collection input is required.")

        range_data = _resolve_connected_range(self, context)
        if range_data is None:
            start_frame = int(scene.frame_start)
            duration = max(1, int(scene.frame_end - scene.frame_start + 1))
        else:
            start_frame, duration = range_data
            duration = max(1, int(duration))
        end_frame = start_frame + duration

        try:
            import numpy as np
        except Exception as exc:
            raise RuntimeError(f"Numpy not available: {exc}") from exc

        view_layer = context.view_layer
        depsgraph = context.evaluated_depsgraph_get()
        original_frame = scene.frame_current

        positions_frames: list[list[tuple[float, float, float]]] = []
        drone_count = None
        for frame in range(start_frame, end_frame):
            scene.frame_set(frame)
            if view_layer is not None:
                view_layer.update()
            positions, pair_ids = transition_apply._collect_positions_for_collection(
                source,
                frame,
                depsgraph,
            )
            if not positions:
                scene.frame_set(original_frame)
                if view_layer is not None:
                    view_layer.update()
                raise RuntimeError(f"No positions at frame {frame}.")
            ordered_positions = _order_by_pair_id(positions, pair_ids)
            if drone_count is None:
                drone_count = len(ordered_positions)
            elif len(ordered_positions) != drone_count:
                scene.frame_set(original_frame)
                if view_layer is not None:
                    view_layer.update()
                raise RuntimeError("Drone count mismatch during bake.")
            positions_frames.append(
                [(float(p.x), float(p.y), float(p.z)) for p in ordered_positions]
            )

        scene.frame_set(original_frame)
        if view_layer is not None:
            view_layer.update()

        if not positions_frames or drone_count is None:
            raise RuntimeError("No cached positions.")

        positions_arr = np.asarray(positions_frames, dtype=np.float32)
        pos_min = positions_arr.min(axis=(0, 1))
        pos_max = positions_arr.max(axis=(0, 1))
        rx = float(pos_max[0] - pos_min[0]) or 1.0
        ry = float(pos_max[1] - pos_min[1]) or 1.0
        rz = float(pos_max[2] - pos_min[2]) or 1.0

        frame_count = positions_arr.shape[0]
        pos_pixels = np.empty((drone_count, frame_count, 4), dtype=np.float32)
        pos_pixels[:, :, 3] = 1.0
        pos_pixels[:, :, 0] = (positions_arr[:, :, 0].T - pos_min[0]) / rx
        pos_pixels[:, :, 1] = (positions_arr[:, :, 1].T - pos_min[1]) / ry
        pos_pixels[:, :, 2] = (positions_arr[:, :, 2].T - pos_min[2]) / rz

        prefix = f"VATCache_{self.name}"
        img = _ensure_image(f"{prefix}_VAT", frame_count, drone_count)
        img.pixels[:] = pos_pixels.ravel()
        cache_path = image_util.scene_cache_path(f"{prefix}_VAT", "OPEN_EXR", scene=scene, create=True)
        if cache_path and image_util.write_exr_rgba(cache_path, pos_pixels):
            image_util.link_image_to_existing_file(
                img,
                cache_path,
                "OPEN_EXR",
                use_float=True,
                colorspace="Non-Color",
                reload=True,
            )

        cache_col = _ensure_collection(scene, prefix)
        obj = _ensure_point_object(
            f"{prefix}_Obj",
            positions_frames[0],
            cache_col,
        )
        _link_object_to_collection(obj, cache_col)

        group = vat_gn._create_gn_vat_group(
            img,
            (float(pos_min[0]), float(pos_min[1]), float(pos_min[2])),
            (float(pos_max[0]), float(pos_max[1]), float(pos_max[2])),
            frame_count,
            drone_count,
            start_frame=start_frame,
            base_name=prefix,
        )
        vat_gn._apply_gn_to_object(obj, group)

        self.cache_collection = cache_col
        out_sock = self.outputs.get("Collection") if hasattr(self, "outputs") else None
        if out_sock and hasattr(out_sock, "collection"):
            out_sock.collection = cache_col
