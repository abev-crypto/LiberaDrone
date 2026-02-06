import json
import os

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

from liberadronecore.ledeffects.nodes.mask import le_collectionmask
from liberadronecore.ledeffects.nodes.mask import le_idmask
from liberadronecore.ledeffects.nodes.mask import le_insidemesh
from liberadronecore.ledeffects.nodes.mask import le_trail
from liberadronecore.ledeffects.nodes.position import le_projectionuv
from liberadronecore.ledeffects.nodes.sampler import le_image
from liberadronecore.ledeffects.nodes.entry import le_frameentry
from liberadronecore.ledeffects.nodes.util import le_catcache
from liberadronecore.ledeffects.nodes.util import le_paintcache
from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.formation import fn_parse
from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.ui import ledeffects_panel as led_panel
from liberadronecore.ledeffects.util import collectionmask as collectionmask_util
from liberadronecore.ledeffects.util import formation_ids as formation_ids_util
from liberadronecore.ledeffects.util import idmask as idmask_util
from liberadronecore.ledeffects.util import insidemesh as insidemesh_util
from liberadronecore.ledeffects.util import paint as paint_util
from liberadronecore.ledeffects.util import projectionuv as projectionuv_util
from liberadronecore.ledeffects.util import trail as trail_util
from liberadronecore.ui.paint import paint_window
from liberadronecore.util import led_eval
from liberadronecore.util.modeling import delaunay
from liberadronecore.tasks import ledeffects_task


class LDLED_OT_create_output_node(bpy.types.Operator):
    bl_idname = "ldled.create_output_node"
    bl_label = "CreateNode"
    bl_description = "Create LED Effects tree and add an Output node"

    def execute(self, context):
        tree = led_panel._ensure_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        node = tree.nodes.new("LDLEDOutputNode")
        node.location = (200.0, 0.0)
        led_panel._set_active_output(context, node)
        led_panel._sync_output_items(context.scene, tree)
        for idx, item in enumerate(context.scene.ld_led_output_items):
            if item.node_name == node.name:
                context.scene.ld_led_output_index = idx
                break
        return {'FINISHED'}


class LDLED_OT_export_template(bpy.types.Operator):
    bl_idname = "ldled.export_template"
    bl_label = "Export"
    bl_description = "Export the selected LED output node graph to JSON"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        tree = led_panel._get_led_tree(context)
        node = led_panel._get_selected_output_node(context, tree)
        if node is None:
            self.report({'ERROR'}, "Select an LED Output node")
            return {'CANCELLED'}
        base = led_panel._template_dir()
        os.makedirs(base, exist_ok=True)
        filename = led_panel._sanitize_filename(node.name) + ".json"
        self.filepath = os.path.join(base, filename)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = led_panel._get_led_tree(context)
        node = led_panel._get_selected_output_node(context, tree)
        if node is None:
            self.report({'ERROR'}, "Select an LED Output node")
            return {'CANCELLED'}
        payload = led_panel._serialize_led_graph(node)
        if not self.filepath:
            self.report({'ERROR'}, "Missing export path")
            return {'CANCELLED'}
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)
        self.report({'INFO'}, f"Exported: {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class LDLED_OT_import_template(bpy.types.Operator):
    bl_idname = "ldled.import_template"
    bl_label = "Import"
    bl_description = "Import an LED template JSON and build the node graph"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        base = led_panel._template_dir()
        if os.path.isdir(base):
            self.filepath = base
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = led_panel._ensure_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        payload = led_panel._load_template_file(self.filepath)
        if not payload:
            self.report({'ERROR'}, "Template load failed")
            return {'CANCELLED'}
        if payload.get("tree_type") != "LD_LedEffectsTree":
            self.report({'ERROR'}, "Invalid template type")
            return {'CANCELLED'}
        root = led_panel._build_led_graph(tree, payload)
        if root is not None:
            led_panel._set_active_output(context, root)
        led_panel._sync_output_items(context.scene, tree)
        return {'FINISHED'}


class LDLED_OT_build_template(bpy.types.Operator):
    bl_idname = "ldled.build_template"
    bl_label = "Build Template"
    bl_description = "Build an LED node template from the sample directory"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        tree = led_panel._ensure_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        payload = led_panel._load_template_file(self.filepath)
        if not payload:
            self.report({'ERROR'}, "Template load failed")
            return {'CANCELLED'}
        if payload.get("tree_type") != "LD_LedEffectsTree":
            self.report({'ERROR'}, "Invalid template type")
            return {'CANCELLED'}
        root = led_panel._build_led_graph(tree, payload)
        if root is not None:
            led_panel._set_active_output(context, root)
        led_panel._sync_output_items(context.scene, tree)
        return {'FINISHED'}


class LDLED_OT_add_frame(bpy.types.Operator):
    bl_idname = "ldled.add_frame"
    bl_label = "Frame"
    bl_description = "Wrap selected LED nodes in a frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        tree = led_panel._get_led_tree(context)
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
            frame.location = led_panel._node_editor_cursor(context)
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
        tree = led_panel._get_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        node = tree.nodes.new("NodeReroute")
        node.location = led_panel._node_editor_cursor(context)
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
        tree = led_panel._get_led_tree(context)
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
        for node in selected:
            tree.nodes.active = node
            break
        override = led_panel._node_editor_override(context)
        if override:
            with context.temp_override(**override):
                if not bpy.ops.node.group_make.poll():
                    self.report({'ERROR'}, "Grouping is not supported in this editor")
                    return {'CANCELLED'}
                result = bpy.ops.node.group_make()
        else:
            if not bpy.ops.node.group_make.poll():
                self.report({'ERROR'}, "Grouping is not supported in this editor")
                return {'CANCELLED'}
            result = bpy.ops.node.group_make()
        if result != {'FINISHED'}:
            self.report({'ERROR'}, "Group creation failed")
            return {'CANCELLED'}
        return {'FINISHED'}


class LDLED_OT_cat_cache_bake(bpy.types.Operator):
    bl_idname = "ldled.cat_cache_bake"
    bl_label = "Bake CAT Cache"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_catcache.LDLEDCatCacheNode):
            self.report({'ERROR'}, "CAT Cache node not found")
            return {'CANCELLED'}

        scene = context.scene
        if scene is None:
            self.report({'ERROR'}, "No active scene")
            return {'CANCELLED'}

        color_fn = le_catcache.led_codegen_runtime.compile_led_socket(tree, node, "Color", force_inputs=True)
        entry_fn = le_catcache.led_codegen_runtime.compile_led_socket(tree, node, "Entry", force_inputs=True)
        if color_fn is None or entry_fn is None:
            self.report({'ERROR'}, "Failed to compile CAT inputs")
            return {'CANCELLED'}

        entry = entry_fn(0, (0.0, 0.0, 0.0), scene.frame_current)
        span = le_catcache._first_entry_span(entry)
        if span is None:
            self.report({'ERROR'}, "Entry span not found")
            return {'CANCELLED'}

        start, end = span
        start_frame = int(start)
        end_frame = int(end)
        if end_frame <= start_frame:
            self.report({'ERROR'}, "Entry duration is 0")
            return {'CANCELLED'}

        width = max(1, end_frame - start_frame)
        original_frame = scene.frame_current
        span_items: list[tuple[float, float, str]] = []
        if entry:
            for key, items in entry.items():
                for s, e in items:
                    span_items.append((float(s), float(e), str(key)))
        span_items.sort(key=lambda item: (item[0], item[1], item[2]))
        span_preview = span_items[:3]
        view_layer = context.view_layer

        def _set_frame(frame: int) -> None:
            scene.frame_set(int(frame))
            view_layer.update()

        _set_frame(start_frame)
        start_positions, _start_pairs, _start_formations = ledeffects_task._collect_formation_positions(scene)
        print(
            f"[CATCache] Bake node={node.name} start={start_frame} end={end_frame} "
            f"size={width}x{max(0, len(start_positions))} "
            f"spans={len(span_items)} preview={span_preview}"
        )

        ledeffects_task.suspend_led_effects(True)

        _set_frame(start_frame)
        positions, pair_ids, formation_ids = ledeffects_task._collect_formation_positions(scene)
        height = len(positions)
        if height <= 0:
            self.report({'ERROR'}, "No formation vertices")
            return {'CANCELLED'}

        pixels = np.zeros((height, width, 4), dtype=np.float32)

        for col_idx, frame in enumerate(range(start_frame, end_frame)):
            _set_frame(frame)
            positions, pair_ids, formation_ids = ledeffects_task._collect_formation_positions(scene)
            positions_cache, _inv_map = led_eval.order_positions_cache_by_pair_ids(
                positions,
                pair_ids,
            )
            le_meshinfo.begin_led_frame_cache(
                frame,
                positions_cache,
                formation_ids=formation_ids,
                pair_ids=pair_ids,
            )
            colors = led_eval.eval_effect_colors_by_map(
                positions,
                pair_ids,
                formation_ids,
                color_fn,
                frame,
            )
            pixels[:, col_idx] = colors
            le_meshinfo.end_led_frame_cache()
        min_val = float(pixels.min())
        max_val = float(pixels.max())
        nonzero = int(np.count_nonzero(pixels))
        print(f"[CATCache] pixels stats min={min_val} max={max_val} nonzero={nonzero}")
        img = None
        png_path = le_catcache.image_util.scene_cache_path(
            f"{node.label}_CAT",
            "PNG",
            scene=scene,
            create=True,
        )
        if png_path and le_catcache.image_util.write_png_rgba(
            png_path,
            pixels,
            colorspace="Non-Color",
        ):
            abs_path = bpy.path.abspath(png_path)
            img = node.image
            if img is not None:
                img_path = bpy.path.abspath(img.filepath)
                if img_path and os.path.normpath(img_path) == os.path.normpath(abs_path):
                    img.reload()
                else:
                    img = None
            if img is None:
                img = bpy.data.images.load(abs_path, check_existing=True)

        if img is not None:
            img.reload()
            le_image._IMAGE_CACHE.pop(int(img.as_pointer()), None)
        img.colorspace_settings.name = "Non-Color"
        img.use_fake_user = True
        le_catcache._pack_cat_image(img)
        node.image = img
        scene.frame_set(original_frame)
        ledeffects_task.suspend_led_effects(False)

        return {'FINISHED'}


class LDLED_OT_paint_cache_bake(bpy.types.Operator):
    bl_idname = "ldled.paint_cache_bake"
    bl_label = "Bake Paint Cache"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_paintcache.LDLEDPaintCacheNode):
            self.report({'ERROR'}, "Paint Cache node not found")
            return {'CANCELLED'}

        scene = context.scene
        if scene is None:
            self.report({'ERROR'}, "No active scene")
            return {'CANCELLED'}

        color_fn = le_catcache.led_codegen_runtime.compile_led_socket(
            tree,
            node,
            "Color",
            force_inputs=True,
        )
        if color_fn is None:
            self.report({'ERROR'}, "Failed to compile Color input")
            return {'CANCELLED'}

        allow_fn = le_catcache.led_codegen_runtime.compile_led_socket(
            tree,
            node,
            "AllowIDs",
            force_inputs=True,
        )
        frame = int(scene.frame_current)
        allow_ids = allow_fn(0, (0.0, 0.0, 0.0), frame) if allow_fn else None

        allow_set = None
        if allow_ids is None:
            allow_set = None
        elif isinstance(allow_ids, (list, tuple, set)):
            allow_set = {int(v) for v in allow_ids if int(v) >= 0}
        else:
            allow_set = {int(allow_ids)}

        positions, pair_ids, formation_ids = ledeffects_task._collect_formation_positions(scene)
        if positions is None or len(positions) == 0:
            self.report({'ERROR'}, "No formation vertices")
            return {'CANCELLED'}
        if formation_ids is None or len(formation_ids) != len(positions):
            self.report({'ERROR'}, "formation_id attribute not found")
            return {'CANCELLED'}

        positions_list = [tuple(float(v) for v in pos) for pos in positions]
        min_x = min(p[0] for p in positions_list)
        max_x = max(p[0] for p in positions_list)
        min_z = min(p[2] for p in positions_list)
        max_z = max(p[2] for p in positions_list)
        span_x = max(0.0001, max_x - min_x)
        span_z = max(0.0001, max_z - min_z)

        mapping = {}
        for src_idx, fid in enumerate(formation_ids):
            fid_val = int(fid)
            if allow_set is not None and fid_val not in allow_set:
                continue
            if fid_val in mapping:
                continue
            pos = positions_list[src_idx]
            runtime_idx = int(pair_ids[src_idx]) if pair_ids is not None else int(src_idx)
            u = (pos[0] - min_x) / span_x
            v = (pos[2] - min_z) / span_z
            mapping[fid_val] = (u, v, runtime_idx, pos)

        if not mapping:
            self.report({'ERROR'}, "No valid formation IDs to cache")
            return {'CANCELLED'}

        positions_cache, _inv_map = led_eval.order_positions_cache_by_pair_ids(positions_list, pair_ids)
        le_meshinfo.begin_led_frame_cache(
            frame,
            positions_cache,
            formation_ids=formation_ids,
            pair_ids=pair_ids,
        )
        colors_by_fid = {}
        try:
            for fid_val, (u, v, runtime_idx, pos) in mapping.items():
                color = color_fn(runtime_idx, pos, frame)
                if not color:
                    color = (0.0, 0.0, 0.0, 1.0)
                if len(color) < 4:
                    color = (float(color[0]), float(color[1]), float(color[2]), 1.0)
                else:
                    color = (
                        float(color[0]),
                        float(color[1]),
                        float(color[2]),
                        float(color[3]),
                    )
                colors_by_fid[fid_val] = (u, v, color)
        finally:
            le_meshinfo.end_led_frame_cache()

        uv_points = []
        uv_colors = []
        for u, v, color in colors_by_fid.values():
            uv_points.append((float(u), float(v)))
            uv_colors.append(color)

        if not uv_points:
            self.report({'ERROR'}, "No colors generated")
            return {'CANCELLED'}

        if node.image:
            width, height = node.image.size
        else:
            width = 512
            height = 512

        width = max(1, int(width))
        height = max(1, int(height))

        kd = KDTree(len(uv_points))
        for i, (u, v) in enumerate(uv_points):
            kd.insert(Vector((u, v, 0.0)), i)
        kd.balance()

        pixels = np.zeros((height, width, 4), dtype=np.float32)
        x_div = max(1, width - 1)
        y_div = max(1, height - 1)
        for y in range(height):
            v = y / y_div
            for x in range(width):
                u = x / x_div
                _co, idx, _dist = kd.find(Vector((u, v, 0.0)))
                pixels[y, x] = uv_colors[int(idx)]

        png_path = le_catcache.image_util.scene_cache_path(
            f"{node.label}_PaintCache",
            "PNG",
            scene=scene,
            create=True,
        )
        if not png_path:
            self.report({'ERROR'}, "Cache path not available (save the blend file)")
            return {'CANCELLED'}

        if not le_catcache.image_util.write_png_rgba(png_path, pixels, colorspace="Non-Color"):
            self.report({'ERROR'}, "Failed to write Paint Cache image")
            return {'CANCELLED'}

        abs_path = bpy.path.abspath(png_path)
        img = node.image
        if img is not None:
            img_path = bpy.path.abspath(img.filepath)
            if img_path and os.path.normpath(img_path) == os.path.normpath(abs_path):
                img.reload()
            else:
                img = None
        if img is None:
            img = bpy.data.images.load(abs_path, check_existing=True)

        img.colorspace_settings.name = "Non-Color"
        img.use_fake_user = True
        node.image = img
        le_image._IMAGE_CACHE.pop(int(img.as_pointer()), None)

        return {'FINISHED'}


class LDLED_OT_frameentry_fill_current(bpy.types.Operator):
    bl_idname = "ldled.frameentry_fill_current"
    bl_label = "Fill from Current"
    bl_description = "Fill Start/Duration from the current frame formation"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_frameentry.LDLEDFrameEntryNode):
            self.report({'ERROR'}, "Frame Entry node not found")
            return {'CANCELLED'}

        scene = context.scene
        if scene is None:
            self.report({'ERROR'}, "No active scene")
            return {'CANCELLED'}

        schedule = fn_parse.get_cached_schedule(scene)
        if not schedule:
            self.report({'ERROR'}, "No formation schedule. Run Calculate first.")
            return {'CANCELLED'}

        frame = int(scene.frame_current)
        active = None
        for entry in schedule:
            if entry.start <= frame < entry.end:
                if active is None or entry.start > active.start:
                    active = entry
        if active is None:
            self.report({'ERROR'}, "No active formation at current frame")
            return {'CANCELLED'}

        start_sock = node.inputs.get("Start")
        if start_sock is not None and hasattr(start_sock, "default_value"):
            start_sock.default_value = int(active.start)
        duration_sock = node.inputs.get("Duration")
        if duration_sock is not None and hasattr(duration_sock, "default_value"):
            duration_sock.default_value = max(0, int(active.end - active.start))
        node.end_frame = int(active.end)

        return {'FINISHED'}


class LDLED_OT_remapframe_fill_current(bpy.types.Operator):
    bl_idname = "ldled.remapframe_fill_current"
    bl_label = "Set Remap Frame"
    bl_description = "Set Remap Frame to the end of the current formation"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not hasattr(node, "remap_frame"):
            self.report({'ERROR'}, "Remap Frame node not found")
            return {'CANCELLED'}

        scene = context.scene
        if scene is None:
            self.report({'ERROR'}, "No active scene")
            return {'CANCELLED'}

        schedule = fn_parse.get_cached_schedule(scene)
        if not schedule:
            self.report({'ERROR'}, "No formation schedule. Run Calculate first.")
            return {'CANCELLED'}

        frame = int(scene.frame_current)
        active = None
        for entry in schedule:
            if entry.start <= frame < entry.end:
                if active is None or entry.start > active.start:
                    active = entry
        if active is None:
            self.report({'ERROR'}, "No active formation at current frame")
            return {'CANCELLED'}

        node.remap_frame = max(int(active.start), int(active.end) - 1)

        return {'FINISHED'}


class LDLED_OT_insidemesh_create_mesh(bpy.types.Operator):
    bl_idname = "ldled.insidemesh_create_mesh"
    bl_label = "Create Inside Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_insidemesh.LDLEDInsideMeshNode):
            self.report({'ERROR'}, "Inside Mesh node not found")
            return {'CANCELLED'}

        points = insidemesh_util._collect_points(context)
        if len(points) < 3:
            self.report({'ERROR'}, "Select at least 3 vertices or a mesh")
            return {'CANCELLED'}

        mesh = delaunay.build_planar_mesh_from_points(points)
        name = insidemesh_util._unique_name(f"{node.name}_Inside")
        obj = bpy.data.objects.new(name, mesh)
        insidemesh_util._ensure_collection(context).objects.link(obj)
        obj.display_type = 'BOUNDS'
        insidemesh_util._apply_solidify(obj)
        insidemesh_util._freeze_object_transform(obj)
        mesh_socket = node.inputs.get("Mesh")
        if mesh_socket is not None and hasattr(mesh_socket, "default_value"):
            mesh_socket.default_value = obj
        return {'FINISHED'}


class LDLED_OT_projectionuv_create_mesh(bpy.types.Operator):
    bl_idname = "ldled.projectionuv_create_mesh"
    bl_label = "Create Projection Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()
    mode: bpy.props.EnumProperty(
        items=[
            ("AREA", "Area", ""),
            ("FORMATION", "Formation", ""),
            ("SELECT", "Select", ""),
        ],
        default="AREA",
    )

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_projectionuv.LDLEDProjectionUVNode):
            self.report({'ERROR'}, "Projection UV node not found")
            return {'CANCELLED'}

        bounds = None
        if self.mode == "AREA":
            obj = bpy.data.objects.get("AreaObject")
            bounds = projectionuv_util._world_bbox_from_object(obj) if obj else None
            if bounds is None:
                self.report({'ERROR'}, "AreaObject not found")
                return {'CANCELLED'}
        elif self.mode == "FORMATION":
            col = bpy.data.collections.get("Formation")
            bounds = projectionuv_util._world_bbox_from_collection(col)
            if bounds is None:
                self.report({'ERROR'}, "Formation collection not found")
                return {'CANCELLED'}
        else:
            verts = projectionuv_util._selected_world_vertices(context)
            if verts:
                bounds = projectionuv_util._world_bbox_from_points(verts)
            else:
                bounds = None
                for obj in projectionuv_util._selected_mesh_objects(context):
                    obj_bounds = projectionuv_util._world_bbox_from_object(obj)
                    if obj_bounds is None:
                        continue
                    if bounds is None:
                        bounds = (obj_bounds[0].copy(), obj_bounds[1].copy())
                    else:
                        bounds[0].x = min(bounds[0].x, obj_bounds[0].x)
                        bounds[0].y = min(bounds[0].y, obj_bounds[0].y)
                        bounds[0].z = min(bounds[0].z, obj_bounds[0].z)
                        bounds[1].x = max(bounds[1].x, obj_bounds[1].x)
                        bounds[1].y = max(bounds[1].y, obj_bounds[1].y)
                        bounds[1].z = max(bounds[1].z, obj_bounds[1].z)
            if bounds is None:
                self.report({'ERROR'}, "No selection mesh or vertices")
                return {'CANCELLED'}

        name = projectionuv_util._unique_name(f"{node.name}_Projection")
        obj = projectionuv_util._create_xz_plane(name, bounds, context)
        obj.display_type = 'BOUNDS'
        mesh_socket = node.inputs.get("Mesh")
        if mesh_socket is not None and hasattr(mesh_socket, "default_value"):
            mesh_socket.default_value = obj
        return {'FINISHED'}


class LDLED_OT_projectionuv_toggle_preview_material(bpy.types.Operator):
    bl_idname = "ldled.projectionuv_toggle_preview_material"
    bl_label = "Toggle Preview Material"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_projectionuv.LDLEDProjectionUVNode):
            self.report({'ERROR'}, "Projection UV node not found")
            return {'CANCELLED'}

        mesh_socket = node.inputs.get("Mesh")
        if mesh_socket is None or mesh_socket.is_linked:
            self.report({'ERROR'}, "Projection mesh input is not set")
            return {'CANCELLED'}

        obj = mesh_socket.default_value
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Projection mesh object not found")
            return {'CANCELLED'}

        image = getattr(node, "preview_image", None)
        if image is None:
            self.report({'ERROR'}, "Preview image not set")
            return {'CANCELLED'}

        mat_name = projectionuv_util._preview_material_name(image)
        mats = obj.data.materials
        if mats and mats[0] and mats[0].name == mat_name:
            mats.clear()
            obj.display_type = 'BOUNDS'
        else:
            mat = projectionuv_util._get_or_create_preview_material(image)
            if mats:
                mats[0] = mat
            else:
                mats.append(mat)
            obj.display_type = 'SOLID'
        return {'FINISHED'}


class LDLED_OT_paint_start(bpy.types.Operator):
    bl_idname = "ldled.paint_start"
    bl_label = "Start Paint"
    bl_options = {'REGISTER'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        window = context.window
        if window is None or window.screen is None:
            self.report({'ERROR'}, "No active window")
            return {'CANCELLED'}

        area = next((a for a in window.screen.areas if a.type == 'VIEW_3D'), None)
        if area is None:
            self.report({'ERROR'}, "3D View not found")
            return {'CANCELLED'}
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if region is None:
            self.report({'ERROR'}, "3D View region not found")
            return {'CANCELLED'}

        override = {
            "window": window,
            "screen": window.screen,
            "area": area,
            "region": region,
            "scene": context.scene,
        }
        with context.temp_override(**override):
            result = bpy.ops.ldled.paint_modal(
                'INVOKE_DEFAULT',
                node_tree_name=self.node_tree_name,
                node_name=self.node_name,
            )
        if 'RUNNING_MODAL' in result:
            paint_window.show_window()
        return {'FINISHED'}


class LDLED_OT_paint_modal(bpy.types.Operator):
    bl_idname = "ldled.paint_modal"
    bl_label = "Paint"
    bl_options = {'REGISTER'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    _draw_handle = None
    _brush_center_2d = None
    _brush_radius_px = None
    _kd = None
    _vidx_list = None
    _proj_count = 0
    _view_sig = None
    _obj_name = None
    _obj_mw_sig = None
    _sel_sig = None
    _only_selected = False
    _painting = False
    _last_primary = None
    _cursor_eyedropper = False
    _formation_map = None
    _formation_error = None

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, "Run in a 3D View")
            return {'CANCELLED'}

        tree = bpy.data.node_groups[self.node_tree_name]
        node = tree.nodes[self.node_name]
        paint_util.set_active_node(node)
        paint_util.set_paint_modal_active(True)
        paint_util.set_eyedrop_mode(None)

        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            paint_util.clear_active_node()
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        if not self._update_formation_map(bm):
            paint_util.set_paint_modal_active(False)
            paint_util.set_eyedrop_mode(None)
            paint_util.clear_active_node()
            self.report({'ERROR'}, self._formation_error or "formation_id attribute not found")
            return {'CANCELLED'}

        self._brush_radius_px = node.paint_radius
        self._brush_center_2d = (event.mouse_region_x, event.mouse_region_y)
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            paint_util.draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL'
        )
        self._rebuild_cache(context)

        context.window_manager.modal_handler_add(self)
        self._set_header_text(context)
        return {'RUNNING_MODAL'}

    def finish(self, context):
        if self._draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
        if self._cursor_eyedropper:
            context.window.cursor_modal_restore()
            self._cursor_eyedropper = False
        if context.area:
            context.area.header_text_set(None)
        self._kd = None
        self._vidx_list = None
        paint_util.set_eyedrop_mode(None)
        paint_util.set_paint_modal_active(False)
        paint_util.clear_active_node()

    def _update_brush_draw(self, context, event):
        self._brush_center_2d = (event.mouse_region_x, event.mouse_region_y)
        node = paint_util.active_node()
        self._brush_radius_px = node.paint_radius
        if context.area:
            context.area.tag_redraw()
        self._set_header_text(context)

    def _set_header_text(self, context) -> None:
        if context.area is None:
            return
        node = paint_util.active_node()
        if node is None:
            return
        mode = paint_util.eyedrop_mode()
        if mode == "VERTEX":
            context.area.header_text_set("Paint: LMB=sample vertex | RMB/ESC=exit | [ ] radius")
        elif mode == "SCREEN":
            context.area.header_text_set("Paint: LMB=sample screen | RMB/ESC=exit | [ ] radius")
        else:
            context.area.header_text_set("Paint: LMB drag=apply | RMB/ESC=exit | [ ] radius")

    def _view_signature(self, region, rv3d):
        vm = rv3d.view_matrix
        pm = rv3d.perspective_matrix
        return (
            region.width,
            region.height,
            rv3d.is_perspective,
            round(vm[0][0], 6), round(vm[0][1], 6), round(vm[0][2], 6), round(vm[0][3], 6),
            round(vm[1][0], 6), round(vm[1][1], 6), round(vm[1][2], 6), round(vm[1][3], 6),
            round(vm[2][0], 6), round(vm[2][1], 6), round(vm[2][2], 6), round(vm[2][3], 6),
            round(pm[0][0], 6), round(pm[1][1], 6), round(pm[2][2], 6), round(pm[3][2], 6),
        )

    def _obj_matrix_sig(self, obj):
        mw = obj.matrix_world
        return tuple(round(mw[i][j], 6) for i in range(3) for j in range(4))

    def _selection_sig(self, bm):
        sel = [v.index for v in bm.verts if v.select]
        sel_count = len(sel)
        head = tuple(sel[:16])
        return (sel_count, head)

    def _rebuild_cache(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        selected = [v for v in bm.verts if v.select]
        self._only_selected = bool(selected)
        self._kd, self._vidx_list, self._proj_count = paint_util.build_screen_kdtree(
            context,
            obj,
            self._only_selected,
        )
        self._update_formation_map(bm)
        self._view_sig = self._view_signature(context.region, context.region_data)
        self._obj_name = obj.name
        self._obj_mw_sig = self._obj_matrix_sig(obj)
        self._sel_sig = self._selection_sig(bm)
        self._last_primary = None

    def _ensure_cache_valid(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        need = False
        if self._kd is None:
            need = True
        if obj.name != self._obj_name:
            need = True
        if self._obj_matrix_sig(obj) != self._obj_mw_sig:
            need = True
        if self._view_signature(context.region, context.region_data) != self._view_sig:
            need = True
        if self._selection_sig(bm) != self._sel_sig:
            need = True

        if need:
            self._rebuild_cache(context)

    def _compute_hits(self, context, event):
        if self._kd is None or self._proj_count <= 0:
            return []
        node = paint_util.active_node()
        hard = bool(node.paint_hard_brush) if node is not None else False
        return paint_util.find_hits(
            self._kd,
            self._vidx_list,
            (event.mouse_region_x, event.mouse_region_y),
            self._brush_radius_px,
            paint_util.DEFAULT_FALLOFF_POWER,
            hard=hard,
        )

    def _update_formation_map(self, bm) -> bool:
        ids, error = formation_ids_util.read_bmesh_formation_ids(bm, bm.verts)
        if error:
            self._formation_map = None
            self._formation_error = error
            return False
        self._formation_map = {int(v.index): int(fid) for v, fid in zip(bm.verts, ids)}
        self._formation_error = None
        return True

    def _map_hits_to_formation(self, hits):
        if not self._formation_map:
            return []
        mapped = []
        for vidx, weight in hits:
            fid = self._formation_map.get(int(vidx))
            if fid is None or int(fid) < 0:
                continue
            mapped.append((int(fid), float(weight)))
        return mapped

    def _sync_cursor(self, context) -> None:
        mode = paint_util.eyedrop_mode()
        if mode and not self._cursor_eyedropper:
            context.window.cursor_modal_set('EYEDROPPER')
            self._cursor_eyedropper = True
        if mode is None and self._cursor_eyedropper:
            context.window.cursor_modal_restore()
            self._cursor_eyedropper = False

    def _apply_eyedrop(self, context, event) -> None:
        node = paint_util.active_node()
        if node is None:
            return
        mode = paint_util.eyedrop_mode()
        if mode == "SCREEN":
            color = paint_util.sample_screen_color(
                context,
                (event.mouse_region_x, event.mouse_region_y),
            )
            if color is None:
                print("[Paint] eyedrop: no screen color")
                return
            node.paint_color = (color[0], color[1], color[2])
            node.paint_alpha = float(color[3])
            return

        self._ensure_cache_valid(context)
        hits = self._compute_hits(context, event)
        hits = self._map_hits_to_formation(hits)
        if not hits:
            print("[Paint] eyedrop: no hit")
            return
        if mode == "VERTEX":
            hits = [max(hits, key=lambda item: item[1])]
        color = paint_util.average_color(node, hits)
        if color is None:
            print("[Paint] eyedrop: no painted color")
            return
        node.paint_color = (color[0], color[1], color[2])
        node.paint_alpha = float(color[3])

    def modal(self, context, event):
        if event.type in {
            'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE'
        } or event.alt:
            return {'PASS_THROUGH'}

        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            self.finish(context)
            return {'CANCELLED'}
        if event.type == 'ESC':
            self.finish(context)
            return {'CANCELLED'}

        if event.type == 'LEFT_BRACKET' and event.value == 'PRESS':
            node = paint_util.active_node()
            radius = max(1.0, float(node.paint_radius) / 1.1)
            node.paint_radius = radius
            self._brush_radius_px = radius
            if context.area:
                context.area.tag_redraw()
            print(f"[Paint] radius={radius:.1f}px")
            self._set_header_text(context)
            return {'RUNNING_MODAL'}
        if event.type == 'RIGHT_BRACKET' and event.value == 'PRESS':
            node = paint_util.active_node()
            radius = min(5000.0, float(node.paint_radius) * 1.1)
            node.paint_radius = radius
            self._brush_radius_px = radius
            if context.area:
                context.area.tag_redraw()
            print(f"[Paint] radius={radius:.1f}px")
            self._set_header_text(context)
            return {'RUNNING_MODAL'}

        self._sync_cursor(context)
        if event.type in {'MOUSEMOVE', 'LEFTMOUSE'}:
            paint_util.set_last_mouse(event.mouse_region_x, event.mouse_region_y)
            self._update_brush_draw(context, event)

        if paint_util.eyedrop_mode() is not None:
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                self._apply_eyedrop(context, event)
                paint_util.set_eyedrop_mode(None)
                self._sync_cursor(context)
                self._set_header_text(context)
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._ensure_cache_valid(context)
            self._painting = True
            hits = self._compute_hits(context, event)
            hits = self._map_hits_to_formation(hits)
            if hits:
                node = paint_util.active_node()
                color = node.paint_color
                paint_util.apply_paint(node, hits, color, node.paint_alpha, node.blend_mode)
                node.id_data.update_tag()
                primary = hits[0][0]
                if primary != self._last_primary:
                    self._last_primary = primary
                    print(f"[Paint] primary_vert={primary} hits={len(hits)}")
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._painting = False
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE' and self._painting:
            self._ensure_cache_valid(context)
            hits = self._compute_hits(context, event)
            hits = self._map_hits_to_formation(hits)
            if hits:
                node = paint_util.active_node()
                color = node.paint_color
                paint_util.apply_paint(node, hits, color, node.paint_alpha, node.blend_mode)
                node.id_data.update_tag()
                primary = hits[0][0]
                if primary != self._last_primary:
                    self._last_primary = primary
                    print(f"[Paint] primary_vert={primary} hits={len(hits)}")
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}


class LDLED_OT_paint_apply_selection(bpy.types.Operator):
    bl_idname = "ldled.paint_apply_selection"
    bl_label = "Apply Paint"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = paint_util.active_node()
        if node is None:
            self.report({'ERROR'}, "Paint node not active")
            return {'CANCELLED'}
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')

        indices = paint_util.selected_vertex_indices(obj)
        if not indices:
            self.report({'ERROR'}, "No selected vertices")
            return {'CANCELLED'}
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        verts = [bm.verts[idx] for idx in indices if idx < len(bm.verts)]
        ids, error = formation_ids_util.read_bmesh_formation_ids(bm, verts)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}
        hits = [(int(fid), 1.0) for fid in ids if int(fid) >= 0]
        if not hits:
            self.report({'ERROR'}, "No valid formation_id")
            return {'CANCELLED'}
        paint_util.apply_paint(node, hits, node.paint_color, node.paint_alpha, node.blend_mode)
        node.id_data.update_tag()
        return {'FINISHED'}


class LDLED_OT_paint_eyedrop_vertex(bpy.types.Operator):
    bl_idname = "ldled.paint_eyedrop_vertex"
    bl_label = "Eyedrop Vertex"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = paint_util.active_node()
        if node is None:
            self.report({'ERROR'}, "Paint node not active")
            return {'CANCELLED'}
        if paint_util.is_paint_modal_active():
            paint_util.set_eyedrop_mode("VERTEX")
            return {'FINISHED'}
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')

        indices = paint_util.selected_vertex_indices(obj)
        if not indices:
            self.report({'ERROR'}, "No selected vertices")
            return {'CANCELLED'}
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        verts = [bm.verts[idx] for idx in indices if idx < len(bm.verts)]
        ids, error = formation_ids_util.read_bmesh_formation_ids(bm, verts)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}
        hits = [(int(fid), 1.0) for fid in ids if int(fid) >= 0]
        if not hits:
            self.report({'ERROR'}, "No valid formation_id")
            return {'CANCELLED'}
        color = paint_util.average_color(node, hits)
        if color is None:
            self.report({'ERROR'}, "No painted color to sample")
            return {'CANCELLED'}
        node.paint_color = (color[0], color[1], color[2])
        node.paint_alpha = float(color[3])
        return {'FINISHED'}


class LDLED_OT_paint_eyedrop_screen(bpy.types.Operator):
    bl_idname = "ldled.paint_eyedrop_screen"
    bl_label = "Eyedrop Screen"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = paint_util.active_node()
        if node is None:
            self.report({'ERROR'}, "Paint node not active")
            return {'CANCELLED'}
        if paint_util.is_paint_modal_active():
            paint_util.set_eyedrop_mode("SCREEN")
            return {'FINISHED'}
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')

        mouse = paint_util.last_mouse()
        if mouse is None:
            self.report({'ERROR'}, "Cursor position not available")
            return {'CANCELLED'}
        color = paint_util.sample_screen_color(context, mouse)
        if color is None:
            self.report({'ERROR'}, "Screen color not available")
            return {'CANCELLED'}
        node.paint_color = (color[0], color[1], color[2])
        node.paint_alpha = float(color[3])
        return {'FINISHED'}


class LDLED_OT_collectionmask_create_collection(bpy.types.Operator):
    bl_idname = "ldled.collectionmask_create_collection"
    bl_label = "Create Mask Collection"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_collectionmask.LDLEDCollectionMaskNode):
            self.report({'ERROR'}, "Collection Mask node not found")
            return {'CANCELLED'}

        selected = getattr(context, "selected_objects", None) or []
        meshes = [obj for obj in selected if obj.type == 'MESH']
        if not meshes:
            self.report({'ERROR'}, "Select mesh objects")
            return {'CANCELLED'}

        scene = context.scene or bpy.context.scene
        if scene is None:
            self.report({'ERROR'}, "No active scene")
            return {'CANCELLED'}

        name = collectionmask_util._unique_collection_name(f"{node.name}_Mask")
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)

        for obj in meshes:
            if obj.name not in col.objects:
                col.objects.link(obj)

        node.collection = col
        node.inputs["Collection"].default_value = col

        return {'FINISHED'}


class LDLED_OT_idmask_add_selection(bpy.types.Operator):
    bl_idname = "ldled.idmask_add_selection"
    bl_label = "Add Formation IDs"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_idmask.LDLEDIDMaskNode):
            self.report({'ERROR'}, "ID Mask node not found")
            return {'CANCELLED'}

        selected_ids, error = idmask_util._read_selected_ids(context)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        existing = set(idmask_util._node_effective_ids(node, include_legacy=True))
        merged = existing | set(selected_ids or [])
        idmask_util._set_node_ids(node, idmask_util._sorted_ids(merged))
        node.use_custom_ids = True
        return {'FINISHED'}


class LDLED_OT_idmask_remove_selection(bpy.types.Operator):
    bl_idname = "ldled.idmask_remove_selection"
    bl_label = "Remove Formation IDs"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_idmask.LDLEDIDMaskNode):
            self.report({'ERROR'}, "ID Mask node not found")
            return {'CANCELLED'}

        selected_ids, error = idmask_util._read_selected_ids(context)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        existing = set(idmask_util._node_effective_ids(node, include_legacy=True))
        remaining = existing - set(selected_ids or [])
        idmask_util._set_node_ids(node, idmask_util._sorted_ids(remaining))
        node.use_custom_ids = True
        return {'FINISHED'}


class LDLED_OT_trail_set_start(bpy.types.Operator):
    bl_idname = "ldled.trail_set_start"
    bl_label = "Set Trail Start"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_trail.LDLEDTrailNode):
            self.report({'ERROR'}, "Trail node not found")
            return {'CANCELLED'}

        selected_ids, error = trail_util._read_selected_ids_ordered(context, None)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}
        if not selected_ids:
            self.report({'ERROR'}, "No selected vertices")
            return {'CANCELLED'}
        node.start_id = int(selected_ids[0])
        return {'FINISHED'}


class LDLED_OT_trail_set_transit(bpy.types.Operator):
    bl_idname = "ldled.trail_set_transit"
    bl_label = "Set Trail Transit"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, le_trail.LDLEDTrailNode):
            self.report({'ERROR'}, "Trail node not found")
            return {'CANCELLED'}

        selected_ids, error = trail_util._read_selected_ids_ordered(context, None)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}
        if not selected_ids:
            self.report({'ERROR'}, "No selected vertices")
            return {'CANCELLED'}

        node.transit_ids = " ".join(str(i) for i in selected_ids)
        return {'FINISHED'}


class LDLEDEffectsOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LDLED_OT_create_output_node)
        bpy.utils.register_class(LDLED_OT_export_template)
        bpy.utils.register_class(LDLED_OT_import_template)
        bpy.utils.register_class(LDLED_OT_build_template)
        bpy.utils.register_class(LDLED_OT_add_frame)
        bpy.utils.register_class(LDLED_OT_add_reroute)
        bpy.utils.register_class(LDLED_OT_group_selected)
        bpy.utils.register_class(LDLED_OT_cat_cache_bake)
        bpy.utils.register_class(LDLED_OT_paint_cache_bake)
        bpy.utils.register_class(LDLED_OT_frameentry_fill_current)
        bpy.utils.register_class(LDLED_OT_remapframe_fill_current)
        bpy.utils.register_class(LDLED_OT_insidemesh_create_mesh)
        bpy.utils.register_class(LDLED_OT_projectionuv_create_mesh)
        bpy.utils.register_class(LDLED_OT_projectionuv_toggle_preview_material)
        bpy.utils.register_class(LDLED_OT_paint_start)
        bpy.utils.register_class(LDLED_OT_paint_modal)
        bpy.utils.register_class(LDLED_OT_paint_apply_selection)
        bpy.utils.register_class(LDLED_OT_paint_eyedrop_vertex)
        bpy.utils.register_class(LDLED_OT_paint_eyedrop_screen)
        bpy.utils.register_class(LDLED_OT_collectionmask_create_collection)
        bpy.utils.register_class(LDLED_OT_idmask_add_selection)
        bpy.utils.register_class(LDLED_OT_idmask_remove_selection)
        bpy.utils.register_class(LDLED_OT_trail_set_start)
        bpy.utils.register_class(LDLED_OT_trail_set_transit)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LDLED_OT_trail_set_transit)
        bpy.utils.unregister_class(LDLED_OT_trail_set_start)
        bpy.utils.unregister_class(LDLED_OT_idmask_remove_selection)
        bpy.utils.unregister_class(LDLED_OT_idmask_add_selection)
        bpy.utils.unregister_class(LDLED_OT_collectionmask_create_collection)
        bpy.utils.unregister_class(LDLED_OT_paint_eyedrop_screen)
        bpy.utils.unregister_class(LDLED_OT_paint_eyedrop_vertex)
        bpy.utils.unregister_class(LDLED_OT_paint_apply_selection)
        bpy.utils.unregister_class(LDLED_OT_paint_modal)
        bpy.utils.unregister_class(LDLED_OT_paint_start)
        bpy.utils.unregister_class(LDLED_OT_projectionuv_create_mesh)
        bpy.utils.unregister_class(LDLED_OT_projectionuv_toggle_preview_material)
        bpy.utils.unregister_class(LDLED_OT_insidemesh_create_mesh)
        bpy.utils.unregister_class(LDLED_OT_remapframe_fill_current)
        bpy.utils.unregister_class(LDLED_OT_frameentry_fill_current)
        bpy.utils.unregister_class(LDLED_OT_paint_cache_bake)
        bpy.utils.unregister_class(LDLED_OT_cat_cache_bake)
        bpy.utils.unregister_class(LDLED_OT_group_selected)
        bpy.utils.unregister_class(LDLED_OT_add_reroute)
        bpy.utils.unregister_class(LDLED_OT_add_frame)
        bpy.utils.unregister_class(LDLED_OT_build_template)
        bpy.utils.unregister_class(LDLED_OT_import_template)
        bpy.utils.unregister_class(LDLED_OT_export_template)
        bpy.utils.unregister_class(LDLED_OT_create_output_node)
