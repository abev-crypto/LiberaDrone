import json
import os

import bpy

from liberadronecore.ledeffects.nodes.mask import le_collectionmask
from liberadronecore.ledeffects.nodes.mask import le_idmask
from liberadronecore.ledeffects.nodes.mask import le_insidemesh
from liberadronecore.ledeffects.nodes.position import le_projectionuv
from liberadronecore.ledeffects.nodes.util import le_catcache
from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.ui import ledeffects_panel as led_panel


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
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
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
        print(
            f"[CATCache] Bake node={node.name} start={start_frame} end={end_frame} "
            f"size={width}x{max(0, len(le_catcache._resolve_positions(scene, start_frame)[0]))} "
            f"spans={len(span_items)} preview={span_preview}"
        )

        suspend = None
        try:
            from liberadronecore.tasks import ledeffects_task

            suspend = getattr(ledeffects_task, "suspend_led_effects", None)
        except Exception:
            suspend = None

        if suspend is not None:
            suspend(True)

        positions, pair_ids = le_catcache._resolve_positions(scene, start_frame)
        height = len(positions)
        if height <= 0:
            self.report({'ERROR'}, "No formation vertices")
            return {'CANCELLED'}

        pixels = le_catcache.np.zeros((height, width, 4), dtype=le_catcache.np.float32)

        for col_idx, frame in enumerate(range(start_frame, end_frame)):
            positions, pair_ids = le_catcache._resolve_positions(scene, frame)
            if not positions:
                continue
            if len(positions) != height:
                continue
            frame_logs: list[str] = []
            for idx, pos in enumerate(positions):
                runtime_idx = idx
                if pair_ids is not None:
                    pid = pair_ids[idx]
                    if pid is not None:
                        try:
                            runtime_idx = int(pid)
                        except (TypeError, ValueError):
                            runtime_idx = idx
                if runtime_idx < 0 or runtime_idx >= height:
                    continue
                color = color_fn(runtime_idx, pos, frame)
                if not color:
                    continue
                rgba = [0.0, 0.0, 0.0, 1.0]
                for chan in range(min(4, len(color))):
                    rgba[chan] = float(color[chan])
                pixels[runtime_idx, col_idx] = rgba
                frame_logs.append(
                    f"[CATCache] frame={frame} idx={idx} runtime_idx={runtime_idx} color={rgba}"
                )
            if frame_logs:
                print("\n".join(frame_logs))
        try:
            min_val = float(pixels.min())
            max_val = float(pixels.max())
            nonzero = int(le_catcache.np.count_nonzero(pixels))
            print(f"[CATCache] pixels stats min={min_val} max={max_val} nonzero={nonzero}")
        except Exception:
            pass
        img = None
        png_path = le_catcache.image_util.scene_cache_path(
            f"{node.label}_CAT",
            "PNG",
            scene=scene,
            create=True,
        )
        if png_path and le_catcache.image_util.write_png_rgba(png_path, pixels):
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
            try:
                le_catcache.led_codegen_runtime._IMAGE_CACHE.pop(int(img.as_pointer()), None)
            except Exception:
                pass
        try:
            img.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
        try:
            img.use_fake_user = True
        except Exception:
            pass
        le_catcache._pack_cat_image(img)
        node.image = img
        scene.frame_set(original_frame)
        if suspend is not None:
            suspend(False)

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

        points = le_insidemesh._collect_points(context)
        if len(points) < 3:
            self.report({'ERROR'}, "Select at least 3 vertices or a mesh")
            return {'CANCELLED'}

        mesh = le_insidemesh.delaunay.build_planar_mesh_from_points(points)
        name = le_insidemesh._unique_name(f"{node.name}_Inside")
        obj = bpy.data.objects.new(name, mesh)
        le_insidemesh._ensure_collection(context).objects.link(obj)
        obj.display_type = 'BOUNDS'
        le_insidemesh._apply_solidify(obj)
        le_insidemesh._freeze_object_transform(obj)
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
            bounds = le_projectionuv._world_bbox_from_object(obj) if obj else None
            if bounds is None:
                self.report({'ERROR'}, "AreaObject not found")
                return {'CANCELLED'}
        elif self.mode == "FORMATION":
            col = bpy.data.collections.get("Formation")
            bounds = le_projectionuv._world_bbox_from_collection(col)
            if bounds is None:
                self.report({'ERROR'}, "Formation collection not found")
                return {'CANCELLED'}
        else:
            verts = le_projectionuv._selected_world_vertices(context)
            if verts:
                bounds = le_projectionuv._world_bbox_from_points(verts)
            else:
                bounds = None
                for obj in le_projectionuv._selected_mesh_objects(context):
                    obj_bounds = le_projectionuv._world_bbox_from_object(obj)
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

        name = le_projectionuv._unique_name(f"{node.name}_Projection")
        obj = le_projectionuv._create_xz_plane(name, bounds, context)
        obj.display_type = 'BOUNDS'
        mesh_socket = node.inputs.get("Mesh")
        if mesh_socket is not None and hasattr(mesh_socket, "default_value"):
            mesh_socket.default_value = obj
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

        name = le_collectionmask._unique_collection_name(f"{node.name}_Mask")
        col = bpy.data.collections.new(name)
        try:
            scene.collection.children.link(col)
        except Exception:
            pass

        for obj in meshes:
            if obj.name not in col.objects:
                col.objects.link(obj)

        if hasattr(node, "collection"):
            try:
                node.collection = col
            except Exception:
                pass

        col_socket = node.inputs.get("Collection") if hasattr(node, "inputs") else None
        if col_socket is not None and hasattr(col_socket, "default_value"):
            try:
                col_socket.default_value = col
            except Exception:
                pass

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

        selected_ids, error = le_idmask._read_selected_ids(context)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        existing = set(le_idmask._node_effective_ids(node, include_legacy=True))
        merged = existing | set(selected_ids or [])
        le_idmask._set_node_ids(node, le_idmask._sorted_ids(merged))
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

        selected_ids, error = le_idmask._read_selected_ids(context)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        existing = set(le_idmask._node_effective_ids(node, include_legacy=True))
        remaining = existing - set(selected_ids or [])
        le_idmask._set_node_ids(node, le_idmask._sorted_ids(remaining))
        node.use_custom_ids = True
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
        bpy.utils.register_class(LDLED_OT_insidemesh_create_mesh)
        bpy.utils.register_class(LDLED_OT_projectionuv_create_mesh)
        bpy.utils.register_class(LDLED_OT_collectionmask_create_collection)
        bpy.utils.register_class(LDLED_OT_idmask_add_selection)
        bpy.utils.register_class(LDLED_OT_idmask_remove_selection)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LDLED_OT_idmask_remove_selection)
        bpy.utils.unregister_class(LDLED_OT_idmask_add_selection)
        bpy.utils.unregister_class(LDLED_OT_collectionmask_create_collection)
        bpy.utils.unregister_class(LDLED_OT_projectionuv_create_mesh)
        bpy.utils.unregister_class(LDLED_OT_insidemesh_create_mesh)
        bpy.utils.unregister_class(LDLED_OT_cat_cache_bake)
        bpy.utils.unregister_class(LDLED_OT_group_selected)
        bpy.utils.unregister_class(LDLED_OT_add_reroute)
        bpy.utils.unregister_class(LDLED_OT_add_frame)
        bpy.utils.unregister_class(LDLED_OT_build_template)
        bpy.utils.unregister_class(LDLED_OT_import_template)
        bpy.utils.unregister_class(LDLED_OT_export_template)
        bpy.utils.unregister_class(LDLED_OT_create_output_node)
