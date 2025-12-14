import bpy

def _create_gn_vat_group(
    pos_img,
    pos_min,
    pos_max,
    frame_count,
    drone_count,
    *,
    start_frame: int | None,
    base_name: str,
):
    group_name = f"GN_DroneVAT_{base_name}"
    existing = bpy.data.node_groups.get(group_name)
    if existing is not None:
        bpy.data.node_groups.remove(existing)

    ng = bpy.data.node_groups.new(group_name, "GeometryNodeTree")
    iface = ng.interface

    geo_in = iface.new_socket(
        name="Geometry",
        in_out="INPUT",
        socket_type="NodeSocketGeometry",
        description="Input geometry to be displaced by VAT textures",
    )
    posmin_in = iface.new_socket(
        name="Pos Min",
        in_out="INPUT",
        socket_type="NodeSocketVector",
        description="Minimum XYZ values encoded in the VAT position texture",
    )
    posmax_in = iface.new_socket(
        name="Pos Max",
        in_out="INPUT",
        socket_type="NodeSocketVector",
        description="Maximum XYZ values encoded in the VAT position texture",
    )
    startframe_in = iface.new_socket(
        name="Start Frame",
        in_out="INPUT",
        socket_type="NodeSocketFloat",
        description="Scene frame at which the VAT animation starts",
    )
    framecount_in = iface.new_socket(
        name="Frame Count",
        in_out="INPUT",
        socket_type="NodeSocketFloat",
        description="Number of frames contained in the VAT textures",
    )
    dronecount_in = iface.new_socket(
        name="Drone Count",
        in_out="INPUT",
        socket_type="NodeSocketInt",
        description="Total number of drones encoded along the V axis",
    )
    geo_out = iface.new_socket(
        name="Geometry",
        in_out="OUTPUT",
        socket_type="NodeSocketGeometry",
        description="Geometry with VAT-driven positions and colors applied",
    )

    posmin_in.default_value = pos_min
    posmax_in.default_value = pos_max
    startframe_in.default_value = float(start_frame) if start_frame is not None else 0.0
    framecount_in.default_value = float(frame_count)
    dronecount_in.default_value = int(drone_count)

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    n_input = nodes.new("NodeGroupInput")
    n_input.location = (-900, 0)
    n_output = nodes.new("NodeGroupOutput")
    n_output.location = (500, 0)

    n_time = nodes.new("GeometryNodeInputSceneTime")
    n_time.location = (-700, 200)
    n_index = nodes.new("GeometryNodeInputIndex")
    n_index.location = (-700, -50)

    n_sub = nodes.new("ShaderNodeMath")
    n_sub.operation = "SUBTRACT"
    n_sub.location = (-500, 200)

    n_div = nodes.new("ShaderNodeMath")
    n_div.operation = "DIVIDE"
    n_div.use_clamp = True
    n_div.location = (-300, 200)

    n_fc_minus1 = nodes.new("ShaderNodeMath")
    n_fc_minus1.operation = "SUBTRACT"
    n_fc_minus1.location = (-500, 50)

    n_dc_minus1 = nodes.new("ShaderNodeMath")
    n_dc_minus1.operation = "SUBTRACT"
    n_dc_minus1.location = (-500, -250)

    n_div_index = nodes.new("ShaderNodeMath")
    n_div_index.operation = "DIVIDE"
    n_div_index.use_clamp = True
    n_div_index.location = (-300, -250)

    n_combine_uv = nodes.new("ShaderNodeCombineXYZ")
    n_combine_uv.location = (-100, 0)

    n_tex_pos = nodes.new("GeometryNodeImageTexture")
    n_tex_pos.location = (100, 150)
    n_tex_pos.interpolation = "Closest"
    n_tex_pos.extension = "EXTEND"
    n_tex_pos.inputs["Image"].default_value = pos_img

    n_vsub = nodes.new("ShaderNodeVectorMath")
    n_vsub.operation = "SUBTRACT"
    n_vsub.location = (300, 250)

    n_vmul = nodes.new("ShaderNodeVectorMath")
    n_vmul.operation = "MULTIPLY"
    n_vmul.location = (500, 150)

    n_vadd = nodes.new("ShaderNodeVectorMath")
    n_vadd.operation = "ADD"
    n_vadd.location = (700, 150)

    n_setpos = nodes.new("GeometryNodeSetPosition")
    n_setpos.location = (900, 100)

    links.new(n_input.outputs["Geometry"], n_setpos.inputs["Geometry"])
    links.new(n_setpos.outputs["Geometry"], n_output.inputs["Geometry"])

    links.new(n_time.outputs["Frame"], n_sub.inputs[0])
    links.new(n_input.outputs["Start Frame"], n_sub.inputs[1])

    links.new(n_input.outputs["Frame Count"], n_fc_minus1.inputs[0])
    n_fc_minus1.inputs[1].default_value = 1.0

    links.new(n_sub.outputs[0], n_div.inputs[0])
    links.new(n_fc_minus1.outputs[0], n_div.inputs[1])

    links.new(n_div.outputs[0], n_combine_uv.inputs[0])

    links.new(n_input.outputs["Drone Count"], n_dc_minus1.inputs[0])
    n_dc_minus1.inputs[1].default_value = 1.0

    links.new(n_index.outputs["Index"], n_div_index.inputs[0])
    links.new(n_dc_minus1.outputs[0], n_div_index.inputs[1])

    links.new(n_div_index.outputs[0], n_combine_uv.inputs[1])

    links.new(n_combine_uv.outputs["Vector"], n_tex_pos.inputs["Vector"])

    links.new(n_input.outputs["Pos Max"], n_vsub.inputs[0])
    links.new(n_input.outputs["Pos Min"], n_vsub.inputs[1])

    links.new(n_tex_pos.outputs["Color"], n_vmul.inputs[0])
    links.new(n_vsub.outputs["Vector"], n_vmul.inputs[1])

    links.new(n_input.outputs["Pos Min"], n_vadd.inputs[0])
    links.new(n_vmul.outputs["Vector"], n_vadd.inputs[1])

    links.new(n_vadd.outputs["Vector"], n_setpos.inputs["Position"])

    return ng


def _apply_gn_to_object(obj, node_group):
    for m in list(obj.modifiers):
        if m.type == "NODES":
            obj.modifiers.remove(m)
    mod = obj.modifiers.new(name="Drone VAT", type="NODES")
    mod.node_group = node_group
    return mod