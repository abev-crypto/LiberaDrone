import bpy
import mathutils
import os
import typing


def gn_drone_errorcheck_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize GN_Drone_ErrorCheck node group"""
    gn_drone_errorcheck_1 = bpy.data.node_groups.new(type='GeometryNodeTree', name="GN_Drone_ErrorCheck")

    gn_drone_errorcheck_1.color_tag = 'NONE'
    gn_drone_errorcheck_1.description = ""
    gn_drone_errorcheck_1.default_group_node_width = 140

    # gn_drone_errorcheck_1 interface

    # Socket Geometry
    geometry_socket = gn_drone_errorcheck_1.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    # Socket Geometry
    geometry_socket_1 = gn_drone_errorcheck_1.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'

    # Socket Prev Pos
    prev_pos_socket = gn_drone_errorcheck_1.interface.new_socket(name="Prev Pos", in_out='INPUT', socket_type='NodeSocketVector')
    prev_pos_socket.default_value = (0.0, 0.0, 0.0)
    prev_pos_socket.min_value = -3.4028234663852886e+38
    prev_pos_socket.max_value = 3.4028234663852886e+38
    prev_pos_socket.subtype = 'NONE'
    prev_pos_socket.attribute_domain = 'POINT'

    # Socket Prev Vel
    prev_vel_socket = gn_drone_errorcheck_1.interface.new_socket(name="Prev Vel", in_out='INPUT', socket_type='NodeSocketVector')
    prev_vel_socket.default_value = (0.0, 0.0, 0.0)
    prev_vel_socket.min_value = -3.4028234663852886e+38
    prev_vel_socket.max_value = 3.4028234663852886e+38
    prev_vel_socket.subtype = 'NONE'
    prev_vel_socket.attribute_domain = 'POINT'

    # Socket Delta Time
    delta_time_socket = gn_drone_errorcheck_1.interface.new_socket(name="Delta Time", in_out='INPUT', socket_type='NodeSocketFloat')
    delta_time_socket.default_value = 0.0
    delta_time_socket.min_value = -3.4028234663852886e+38
    delta_time_socket.max_value = 3.4028234663852886e+38
    delta_time_socket.subtype = 'NONE'
    delta_time_socket.attribute_domain = 'POINT'

    # Socket Max Speed Vert
    max_speed_vert_socket = gn_drone_errorcheck_1.interface.new_socket(name="Max Speed Vert", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_vert_socket.default_value = 0.0
    max_speed_vert_socket.min_value = -3.4028234663852886e+38
    max_speed_vert_socket.max_value = 3.4028234663852886e+38
    max_speed_vert_socket.subtype = 'NONE'
    max_speed_vert_socket.attribute_domain = 'POINT'

    # Socket Max Speed Horiz
    max_speed_horiz_socket = gn_drone_errorcheck_1.interface.new_socket(name="Max Speed Horiz", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_horiz_socket.default_value = 0.0
    max_speed_horiz_socket.min_value = -3.4028234663852886e+38
    max_speed_horiz_socket.max_value = 3.4028234663852886e+38
    max_speed_horiz_socket.subtype = 'NONE'
    max_speed_horiz_socket.attribute_domain = 'POINT'

    # Socket Max Acc Vert
    max_acc_vert_socket = gn_drone_errorcheck_1.interface.new_socket(name="Max Acc Vert", in_out='INPUT', socket_type='NodeSocketFloat')
    max_acc_vert_socket.default_value = 0.0
    max_acc_vert_socket.min_value = -3.4028234663852886e+38
    max_acc_vert_socket.max_value = 3.4028234663852886e+38
    max_acc_vert_socket.subtype = 'NONE'
    max_acc_vert_socket.attribute_domain = 'POINT'

    # Socket Max Acc Horiz
    max_acc_horiz_socket = gn_drone_errorcheck_1.interface.new_socket(name="Max Acc Horiz", in_out='INPUT', socket_type='NodeSocketFloat')
    max_acc_horiz_socket.default_value = 0.0
    max_acc_horiz_socket.min_value = -3.4028234663852886e+38
    max_acc_horiz_socket.max_value = 3.4028234663852886e+38
    max_acc_horiz_socket.subtype = 'NONE'
    max_acc_horiz_socket.attribute_domain = 'POINT'

    # Socket Min Distance
    min_distance_socket = gn_drone_errorcheck_1.interface.new_socket(name="Min Distance", in_out='INPUT', socket_type='NodeSocketFloat')
    min_distance_socket.default_value = 0.0
    min_distance_socket.min_value = -3.4028234663852886e+38
    min_distance_socket.max_value = 3.4028234663852886e+38
    min_distance_socket.subtype = 'NONE'
    min_distance_socket.attribute_domain = 'POINT'

    # Initialize gn_drone_errorcheck_1 nodes

    # Node Group Input
    group_input = gn_drone_errorcheck_1.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Group Output
    group_output = gn_drone_errorcheck_1.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Position
    position = gn_drone_errorcheck_1.nodes.new("GeometryNodeInputPosition")
    position.name = "Position"

    # Node Vector Math
    vector_math = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math.name = "Vector Math"
    vector_math.operation = 'SUBTRACT'

    # Node Combine XYZ
    combine_xyz = gn_drone_errorcheck_1.nodes.new("ShaderNodeCombineXYZ")
    combine_xyz.name = "Combine XYZ"

    # Node Vector Math.001
    vector_math_001 = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math_001.name = "Vector Math.001"
    vector_math_001.operation = 'DIVIDE'

    # Node Store Named Attribute
    store_named_attribute = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute.name = "Store Named Attribute"
    store_named_attribute.data_type = 'FLOAT_VECTOR'
    store_named_attribute.domain = 'POINT'
    # Selection
    store_named_attribute.inputs[1].default_value = True
    # Name
    store_named_attribute.inputs[2].default_value = "vel"

    # Node Vector Math.002
    vector_math_002 = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math_002.name = "Vector Math.002"
    vector_math_002.operation = 'SUBTRACT'

    # Node Vector Math.003
    vector_math_003 = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math_003.name = "Vector Math.003"
    vector_math_003.operation = 'DIVIDE'

    # Node Store Named Attribute.001
    store_named_attribute_001 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_001.name = "Store Named Attribute.001"
    store_named_attribute_001.data_type = 'FLOAT_VECTOR'
    store_named_attribute_001.domain = 'POINT'
    # Selection
    store_named_attribute_001.inputs[1].default_value = True
    # Name
    store_named_attribute_001.inputs[2].default_value = "acc"

    # Node Separate XYZ
    separate_xyz = gn_drone_errorcheck_1.nodes.new("ShaderNodeSeparateXYZ")
    separate_xyz.name = "Separate XYZ"

    # Node Math
    math = gn_drone_errorcheck_1.nodes.new("ShaderNodeMath")
    math.name = "Math"
    math.operation = 'ABSOLUTE'
    math.use_clamp = False

    # Node Combine XYZ.001
    combine_xyz_001 = gn_drone_errorcheck_1.nodes.new("ShaderNodeCombineXYZ")
    combine_xyz_001.name = "Combine XYZ.001"
    # Z
    combine_xyz_001.inputs[2].default_value = 0.0

    # Node Vector Math.004
    vector_math_004 = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math_004.name = "Vector Math.004"
    vector_math_004.operation = 'LENGTH'

    # Node Store Named Attribute.002
    store_named_attribute_002 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_002.name = "Store Named Attribute.002"
    store_named_attribute_002.data_type = 'FLOAT'
    store_named_attribute_002.domain = 'POINT'
    # Selection
    store_named_attribute_002.inputs[1].default_value = True
    # Name
    store_named_attribute_002.inputs[2].default_value = "speed_vert"

    # Node Store Named Attribute.003
    store_named_attribute_003 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_003.name = "Store Named Attribute.003"
    store_named_attribute_003.data_type = 'FLOAT'
    store_named_attribute_003.domain = 'POINT'
    # Selection
    store_named_attribute_003.inputs[1].default_value = True
    # Name
    store_named_attribute_003.inputs[2].default_value = "speed_horiz"

    # Node Separate XYZ.001
    separate_xyz_001 = gn_drone_errorcheck_1.nodes.new("ShaderNodeSeparateXYZ")
    separate_xyz_001.name = "Separate XYZ.001"

    # Node Math.001
    math_001 = gn_drone_errorcheck_1.nodes.new("ShaderNodeMath")
    math_001.name = "Math.001"
    math_001.operation = 'ABSOLUTE'
    math_001.use_clamp = False

    # Node Combine XYZ.002
    combine_xyz_002 = gn_drone_errorcheck_1.nodes.new("ShaderNodeCombineXYZ")
    combine_xyz_002.name = "Combine XYZ.002"
    # Z
    combine_xyz_002.inputs[2].default_value = 0.0

    # Node Vector Math.005
    vector_math_005 = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math_005.name = "Vector Math.005"
    vector_math_005.operation = 'LENGTH'

    # Node Store Named Attribute.004
    store_named_attribute_004 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_004.name = "Store Named Attribute.004"
    store_named_attribute_004.data_type = 'FLOAT'
    store_named_attribute_004.domain = 'POINT'
    # Selection
    store_named_attribute_004.inputs[1].default_value = True
    # Name
    store_named_attribute_004.inputs[2].default_value = "acc_vert"

    # Node Store Named Attribute.005
    store_named_attribute_005 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_005.name = "Store Named Attribute.005"
    store_named_attribute_005.data_type = 'FLOAT'
    store_named_attribute_005.domain = 'POINT'
    # Selection
    store_named_attribute_005.inputs[1].default_value = True
    # Name
    store_named_attribute_005.inputs[2].default_value = "acc_horiz"

    # Node Compare
    compare = gn_drone_errorcheck_1.nodes.new("FunctionNodeCompare")
    compare.name = "Compare"
    compare.data_type = 'FLOAT'
    compare.mode = 'ELEMENT'
    compare.operation = 'GREATER_THAN'

    # Node Store Named Attribute.006
    store_named_attribute_006 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_006.name = "Store Named Attribute.006"
    store_named_attribute_006.data_type = 'BOOLEAN'
    store_named_attribute_006.domain = 'POINT'
    # Selection
    store_named_attribute_006.inputs[1].default_value = True
    # Name
    store_named_attribute_006.inputs[2].default_value = "err_speed_vert"

    # Node Compare.001
    compare_001 = gn_drone_errorcheck_1.nodes.new("FunctionNodeCompare")
    compare_001.name = "Compare.001"
    compare_001.data_type = 'FLOAT'
    compare_001.mode = 'ELEMENT'
    compare_001.operation = 'GREATER_THAN'

    # Node Store Named Attribute.007
    store_named_attribute_007 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_007.name = "Store Named Attribute.007"
    store_named_attribute_007.data_type = 'BOOLEAN'
    store_named_attribute_007.domain = 'POINT'
    # Selection
    store_named_attribute_007.inputs[1].default_value = True
    # Name
    store_named_attribute_007.inputs[2].default_value = "err_speed_horiz"

    # Node Compare.002
    compare_002 = gn_drone_errorcheck_1.nodes.new("FunctionNodeCompare")
    compare_002.name = "Compare.002"
    compare_002.data_type = 'FLOAT'
    compare_002.mode = 'ELEMENT'
    compare_002.operation = 'GREATER_THAN'

    # Node Store Named Attribute.008
    store_named_attribute_008 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_008.name = "Store Named Attribute.008"
    store_named_attribute_008.data_type = 'BOOLEAN'
    store_named_attribute_008.domain = 'POINT'
    # Selection
    store_named_attribute_008.inputs[1].default_value = True
    # Name
    store_named_attribute_008.inputs[2].default_value = "err_acc_vert"

    # Node Compare.003
    compare_003 = gn_drone_errorcheck_1.nodes.new("FunctionNodeCompare")
    compare_003.name = "Compare.003"
    compare_003.data_type = 'FLOAT'
    compare_003.mode = 'ELEMENT'
    compare_003.operation = 'GREATER_THAN'

    # Node Store Named Attribute.009
    store_named_attribute_009 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_009.name = "Store Named Attribute.009"
    store_named_attribute_009.data_type = 'BOOLEAN'
    store_named_attribute_009.domain = 'POINT'
    # Selection
    store_named_attribute_009.inputs[1].default_value = True
    # Name
    store_named_attribute_009.inputs[2].default_value = "err_acc_horiz"

    # Node Index of Nearest
    index_of_nearest = gn_drone_errorcheck_1.nodes.new("GeometryNodeIndexOfNearest")
    index_of_nearest.name = "Index of Nearest"
    # Group ID
    index_of_nearest.inputs[1].default_value = 0

    # Node Sample Index
    sample_index = gn_drone_errorcheck_1.nodes.new("GeometryNodeSampleIndex")
    sample_index.name = "Sample Index"
    sample_index.clamp = False
    sample_index.data_type = 'FLOAT_VECTOR'
    sample_index.domain = 'POINT'

    # Node Vector Math.006
    vector_math_006 = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math_006.name = "Vector Math.006"
    vector_math_006.operation = 'DISTANCE'

    # Node Compare.004
    compare_004 = gn_drone_errorcheck_1.nodes.new("FunctionNodeCompare")
    compare_004.name = "Compare.004"
    compare_004.data_type = 'FLOAT'
    compare_004.mode = 'ELEMENT'
    compare_004.operation = 'LESS_THAN'

    # Node Store Named Attribute.010
    store_named_attribute_010 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_010.name = "Store Named Attribute.010"
    store_named_attribute_010.data_type = 'BOOLEAN'
    store_named_attribute_010.domain = 'POINT'
    # Selection
    store_named_attribute_010.inputs[1].default_value = True
    # Name
    store_named_attribute_010.inputs[2].default_value = "err_close"

    # Set locations
    gn_drone_errorcheck_1.nodes["Group Input"].location = (-1000.0, 0.0)
    gn_drone_errorcheck_1.nodes["Group Output"].location = (1200.0, 0.0)
    gn_drone_errorcheck_1.nodes["Position"].location = (-879.0662841796875, 217.7041778564453)
    gn_drone_errorcheck_1.nodes["Vector Math"].location = (-600.0, 250.0)
    gn_drone_errorcheck_1.nodes["Combine XYZ"].location = (-600.0, 50.0)
    gn_drone_errorcheck_1.nodes["Vector Math.001"].location = (-400.0, 250.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute"].location = (-200.0, 250.0)
    gn_drone_errorcheck_1.nodes["Vector Math.002"].location = (0.0, 250.0)
    gn_drone_errorcheck_1.nodes["Vector Math.003"].location = (200.0, 250.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.001"].location = (400.0, 250.0)
    gn_drone_errorcheck_1.nodes["Separate XYZ"].location = (-200.0, -50.0)
    gn_drone_errorcheck_1.nodes["Math"].location = (0.0, 0.0)
    gn_drone_errorcheck_1.nodes["Combine XYZ.001"].location = (0.0, -180.0)
    gn_drone_errorcheck_1.nodes["Vector Math.004"].location = (200.0, -180.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].location = (400.0, 0.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].location = (400.0, -180.0)
    gn_drone_errorcheck_1.nodes["Separate XYZ.001"].location = (0.0, -400.0)
    gn_drone_errorcheck_1.nodes["Math.001"].location = (200.0, -350.0)
    gn_drone_errorcheck_1.nodes["Combine XYZ.002"].location = (200.0, -520.0)
    gn_drone_errorcheck_1.nodes["Vector Math.005"].location = (400.0, -520.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].location = (600.0, -350.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].location = (600.0, -520.0)
    gn_drone_errorcheck_1.nodes["Compare"].location = (800.0, 0.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].location = (1000.0, 0.0)
    gn_drone_errorcheck_1.nodes["Compare.001"].location = (800.0, -180.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.007"].location = (1000.0, -180.0)
    gn_drone_errorcheck_1.nodes["Compare.002"].location = (800.0, -350.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].location = (1000.0, -350.0)
    gn_drone_errorcheck_1.nodes["Compare.003"].location = (800.0, -520.0)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.009"].location = (1011.045166015625, -558.6865234375)
    gn_drone_errorcheck_1.nodes["Index of Nearest"].location = (-693.9655151367188, -282.2750244140625)
    gn_drone_errorcheck_1.nodes["Sample Index"].location = (-405.58514404296875, -327.78173828125)
    gn_drone_errorcheck_1.nodes["Vector Math.006"].location = (-272.7162170410156, -384.2509460449219)
    gn_drone_errorcheck_1.nodes["Compare.004"].location = (-280.6695861816406, -531.4411010742188)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.010"].location = (1005.8572998046875, -773.9570922851562)

    # Set dimensions
    gn_drone_errorcheck_1.nodes["Group Input"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Group Input"].height = 100.0

    gn_drone_errorcheck_1.nodes["Group Output"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Group Output"].height = 100.0

    gn_drone_errorcheck_1.nodes["Position"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Position"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math"].height = 100.0

    gn_drone_errorcheck_1.nodes["Combine XYZ"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Combine XYZ"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.002"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.002"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.003"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.003"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Separate XYZ"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Separate XYZ"].height = 100.0

    gn_drone_errorcheck_1.nodes["Math"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Math"].height = 100.0

    gn_drone_errorcheck_1.nodes["Combine XYZ.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Combine XYZ.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.004"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.004"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].height = 100.0

    gn_drone_errorcheck_1.nodes["Separate XYZ.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Separate XYZ.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Math.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Math.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Combine XYZ.002"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Combine XYZ.002"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.005"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.005"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.007"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.007"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare.002"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare.002"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare.003"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare.003"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.009"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.009"].height = 100.0

    gn_drone_errorcheck_1.nodes["Index of Nearest"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Index of Nearest"].height = 100.0

    gn_drone_errorcheck_1.nodes["Sample Index"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Sample Index"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.006"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.006"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare.004"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare.004"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.010"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.010"].height = 100.0


    # Initialize gn_drone_errorcheck_1 links

    # group_input.Geometry -> store_named_attribute.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute"].inputs[0]
    )
    # store_named_attribute.Geometry -> store_named_attribute_001.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.001"].inputs[0]
    )
    # store_named_attribute_001.Geometry -> store_named_attribute_002.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].inputs[0]
    )
    # store_named_attribute_002.Geometry -> store_named_attribute_003.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].inputs[0]
    )
    # store_named_attribute_003.Geometry -> store_named_attribute_004.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].inputs[0]
    )
    # store_named_attribute_004.Geometry -> store_named_attribute_005.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].inputs[0]
    )
    # store_named_attribute_005.Geometry -> store_named_attribute_006.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].inputs[0]
    )
    # store_named_attribute_006.Geometry -> store_named_attribute_007.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.007"].inputs[0]
    )
    # store_named_attribute_007.Geometry -> store_named_attribute_008.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.007"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].inputs[0]
    )
    # store_named_attribute_008.Geometry -> store_named_attribute_009.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.009"].inputs[0]
    )
    # position.Position -> vector_math.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Position"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math"].inputs[0]
    )
    # group_input.Prev Pos -> vector_math.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[1],
        gn_drone_errorcheck_1.nodes["Vector Math"].inputs[1]
    )
    # group_input.Delta Time -> combine_xyz.X
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[3],
        gn_drone_errorcheck_1.nodes["Combine XYZ"].inputs[0]
    )
    # group_input.Delta Time -> combine_xyz.Y
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[3],
        gn_drone_errorcheck_1.nodes["Combine XYZ"].inputs[1]
    )
    # group_input.Delta Time -> combine_xyz.Z
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[3],
        gn_drone_errorcheck_1.nodes["Combine XYZ"].inputs[2]
    )
    # vector_math.Vector -> vector_math_001.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.001"].inputs[0]
    )
    # combine_xyz.Vector -> vector_math_001.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Combine XYZ"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.001"].inputs[1]
    )
    # vector_math_001.Vector -> store_named_attribute.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute"].inputs[3]
    )
    # vector_math_001.Vector -> vector_math_002.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.002"].inputs[0]
    )
    # group_input.Prev Vel -> vector_math_002.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[2],
        gn_drone_errorcheck_1.nodes["Vector Math.002"].inputs[1]
    )
    # vector_math_002.Vector -> vector_math_003.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.002"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.003"].inputs[0]
    )
    # combine_xyz.Vector -> vector_math_003.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Combine XYZ"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.003"].inputs[1]
    )
    # vector_math_003.Vector -> store_named_attribute_001.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.003"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.001"].inputs[3]
    )
    # vector_math_001.Vector -> separate_xyz.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Separate XYZ"].inputs[0]
    )
    # separate_xyz.Z -> math.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ"].outputs[2],
        gn_drone_errorcheck_1.nodes["Math"].inputs[0]
    )
    # math.Value -> store_named_attribute_002.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Math"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].inputs[3]
    )
    # math.Value -> compare.A
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Math"].outputs[0],
        gn_drone_errorcheck_1.nodes["Compare"].inputs[0]
    )
    # separate_xyz.X -> combine_xyz_001.X
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ"].outputs[0],
        gn_drone_errorcheck_1.nodes["Combine XYZ.001"].inputs[0]
    )
    # separate_xyz.Y -> combine_xyz_001.Y
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ"].outputs[1],
        gn_drone_errorcheck_1.nodes["Combine XYZ.001"].inputs[1]
    )
    # combine_xyz_001.Vector -> vector_math_004.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Combine XYZ.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.004"].inputs[0]
    )
    # vector_math_004.Value -> store_named_attribute_003.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.004"].outputs[1],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].inputs[3]
    )
    # vector_math_004.Value -> compare_001.A
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.004"].outputs[1],
        gn_drone_errorcheck_1.nodes["Compare.001"].inputs[0]
    )
    # vector_math_003.Vector -> separate_xyz_001.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.003"].outputs[0],
        gn_drone_errorcheck_1.nodes["Separate XYZ.001"].inputs[0]
    )
    # separate_xyz_001.Z -> math_001.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ.001"].outputs[2],
        gn_drone_errorcheck_1.nodes["Math.001"].inputs[0]
    )
    # math_001.Value -> store_named_attribute_004.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Math.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].inputs[3]
    )
    # math_001.Value -> compare_002.A
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Math.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Compare.002"].inputs[0]
    )
    # separate_xyz_001.X -> combine_xyz_002.X
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Combine XYZ.002"].inputs[0]
    )
    # separate_xyz_001.Y -> combine_xyz_002.Y
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ.001"].outputs[1],
        gn_drone_errorcheck_1.nodes["Combine XYZ.002"].inputs[1]
    )
    # combine_xyz_002.Vector -> vector_math_005.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Combine XYZ.002"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.005"].inputs[0]
    )
    # vector_math_005.Value -> store_named_attribute_005.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.005"].outputs[1],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].inputs[3]
    )
    # vector_math_005.Value -> compare_003.A
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.005"].outputs[1],
        gn_drone_errorcheck_1.nodes["Compare.003"].inputs[0]
    )
    # group_input.Max Speed Vert -> compare.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[4],
        gn_drone_errorcheck_1.nodes["Compare"].inputs[1]
    )
    # group_input.Max Speed Horiz -> compare_001.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[5],
        gn_drone_errorcheck_1.nodes["Compare.001"].inputs[1]
    )
    # group_input.Max Acc Vert -> compare_002.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[6],
        gn_drone_errorcheck_1.nodes["Compare.002"].inputs[1]
    )
    # group_input.Max Acc Horiz -> compare_003.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[7],
        gn_drone_errorcheck_1.nodes["Compare.003"].inputs[1]
    )
    # compare.Result -> store_named_attribute_006.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].inputs[3]
    )
    # compare_001.Result -> store_named_attribute_007.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.007"].inputs[3]
    )
    # compare_002.Result -> store_named_attribute_008.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare.002"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].inputs[3]
    )
    # compare_003.Result -> store_named_attribute_009.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare.003"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.009"].inputs[3]
    )
    # position.Position -> index_of_nearest.Position
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Position"].outputs[0],
        gn_drone_errorcheck_1.nodes["Index of Nearest"].inputs[0]
    )
    # index_of_nearest.Index -> sample_index.Index
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Index of Nearest"].outputs[0],
        gn_drone_errorcheck_1.nodes["Sample Index"].inputs[2]
    )
    # position.Position -> sample_index.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Position"].outputs[0],
        gn_drone_errorcheck_1.nodes["Sample Index"].inputs[1]
    )
    # group_input.Geometry -> sample_index.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[0],
        gn_drone_errorcheck_1.nodes["Sample Index"].inputs[0]
    )
    # sample_index.Value -> vector_math_006.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Sample Index"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.006"].inputs[0]
    )
    # position.Position -> vector_math_006.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Position"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.006"].inputs[1]
    )
    # vector_math_006.Value -> compare_004.A
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.006"].outputs[1],
        gn_drone_errorcheck_1.nodes["Compare.004"].inputs[0]
    )
    # store_named_attribute_009.Geometry -> store_named_attribute_010.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.009"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.010"].inputs[0]
    )
    # compare_004.Result -> store_named_attribute_010.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare.004"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.010"].inputs[3]
    )
    # store_named_attribute_010.Geometry -> group_output.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.010"].outputs[0],
        gn_drone_errorcheck_1.nodes["Group Output"].inputs[0]
    )
    # group_input.Min Distance -> compare_004.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[8],
        gn_drone_errorcheck_1.nodes["Compare.004"].inputs[1]
    )

    return gn_drone_errorcheck_1


def geometry_nodes_001_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize Geometry Nodes.001 node group"""
    geometry_nodes_001_1 = bpy.data.node_groups.new(type='GeometryNodeTree', name="Geometry Nodes.001")

    geometry_nodes_001_1.color_tag = 'NONE'
    geometry_nodes_001_1.description = ""
    geometry_nodes_001_1.default_group_node_width = 140
    geometry_nodes_001_1.is_modifier = True

    # geometry_nodes_001_1 interface

    # Socket Geometry
    geometry_socket = geometry_nodes_001_1.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    # Socket Geometry
    geometry_socket_1 = geometry_nodes_001_1.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'

    # Socket Formation
    formation_socket = geometry_nodes_001_1.interface.new_socket(name="Formation", in_out='INPUT', socket_type='NodeSocketCollection')
    formation_socket.attribute_domain = 'POINT'

    # Socket Max Speed Vert
    max_speed_vert_socket = geometry_nodes_001_1.interface.new_socket(name="Max Speed Vert", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_vert_socket.default_value = 0.0
    max_speed_vert_socket.min_value = -3.4028234663852886e+38
    max_speed_vert_socket.max_value = 3.4028234663852886e+38
    max_speed_vert_socket.subtype = 'NONE'
    max_speed_vert_socket.attribute_domain = 'POINT'

    # Socket Max Speed Horiz
    max_speed_horiz_socket = geometry_nodes_001_1.interface.new_socket(name="Max Speed Horiz", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_horiz_socket.default_value = 0.0
    max_speed_horiz_socket.min_value = -3.4028234663852886e+38
    max_speed_horiz_socket.max_value = 3.4028234663852886e+38
    max_speed_horiz_socket.subtype = 'NONE'
    max_speed_horiz_socket.attribute_domain = 'POINT'

    # Socket Max Acc Vert
    max_acc_vert_socket = geometry_nodes_001_1.interface.new_socket(name="Max Acc Vert", in_out='INPUT', socket_type='NodeSocketFloat')
    max_acc_vert_socket.default_value = 0.0
    max_acc_vert_socket.min_value = -3.4028234663852886e+38
    max_acc_vert_socket.max_value = 3.4028234663852886e+38
    max_acc_vert_socket.subtype = 'NONE'
    max_acc_vert_socket.attribute_domain = 'POINT'

    # Socket Max Acc Horiz
    max_acc_horiz_socket = geometry_nodes_001_1.interface.new_socket(name="Max Acc Horiz", in_out='INPUT', socket_type='NodeSocketFloat')
    max_acc_horiz_socket.default_value = 0.0
    max_acc_horiz_socket.min_value = -3.4028234663852886e+38
    max_acc_horiz_socket.max_value = 3.4028234663852886e+38
    max_acc_horiz_socket.subtype = 'NONE'
    max_acc_horiz_socket.attribute_domain = 'POINT'

    # Socket Min Distance
    min_distance_socket = geometry_nodes_001_1.interface.new_socket(name="Min Distance", in_out='INPUT', socket_type='NodeSocketFloat')
    min_distance_socket.default_value = 0.0
    min_distance_socket.min_value = -3.4028234663852886e+38
    min_distance_socket.max_value = 3.4028234663852886e+38
    min_distance_socket.subtype = 'NONE'
    min_distance_socket.attribute_domain = 'POINT'

    # Socket SkipCheck
    skipcheck_socket = geometry_nodes_001_1.interface.new_socket(name="SkipCheck", in_out='INPUT', socket_type='NodeSocketBool')
    skipcheck_socket.default_value = False
    skipcheck_socket.attribute_domain = 'POINT'
    skipcheck_socket.hide_value = True

    # Initialize geometry_nodes_001_1 nodes

    # Node Group Input
    group_input = geometry_nodes_001_1.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Group Output
    group_output = geometry_nodes_001_1.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Simulation Input
    simulation_input = geometry_nodes_001_1.nodes.new("GeometryNodeSimulationInput")
    simulation_input.name = "Simulation Input"
    # Node Simulation Output
    simulation_output = geometry_nodes_001_1.nodes.new("GeometryNodeSimulationOutput")
    simulation_output.name = "Simulation Output"
    simulation_output.active_index = 0
    simulation_output.state_items.clear()
    # Create item "Geometry"
    simulation_output.state_items.new('GEOMETRY', "Geometry")
    simulation_output.state_items[0].attribute_domain = 'POINT'

    # Node Capture Attribute
    capture_attribute = geometry_nodes_001_1.nodes.new("GeometryNodeCaptureAttribute")
    capture_attribute.name = "Capture Attribute"
    capture_attribute.active_index = 0
    capture_attribute.capture_items.clear()
    capture_attribute.capture_items.new('FLOAT', "Position")
    capture_attribute.capture_items["Position"].data_type = 'FLOAT_VECTOR'
    capture_attribute.domain = 'POINT'

    # Node Position
    position = geometry_nodes_001_1.nodes.new("GeometryNodeInputPosition")
    position.name = "Position"

    # Node Named Attribute
    named_attribute = geometry_nodes_001_1.nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute.name = "Named Attribute"
    named_attribute.data_type = 'FLOAT_VECTOR'
    # Name
    named_attribute.inputs[0].default_value = "vel"

    # Node Group
    group = geometry_nodes_001_1.nodes.new("GeometryNodeGroup")
    group.name = "Group"
    group.node_tree = bpy.data.node_groups[node_tree_names[gn_drone_errorcheck_1_node_group]]

    # Node Collection Info
    collection_info = geometry_nodes_001_1.nodes.new("GeometryNodeCollectionInfo")
    collection_info.name = "Collection Info"
    collection_info.transform_space = 'ORIGINAL'
    # Separate Children
    collection_info.inputs[1].default_value = False
    # Reset Children
    collection_info.inputs[2].default_value = False

    # Node Mesh to Points
    mesh_to_points = geometry_nodes_001_1.nodes.new("GeometryNodeMeshToPoints")
    mesh_to_points.name = "Mesh to Points"
    mesh_to_points.mode = 'VERTICES'
    # Selection
    mesh_to_points.inputs[1].default_value = True
    # Position
    mesh_to_points.inputs[2].default_value = (0.0, 0.0, 0.0)
    # Radius
    mesh_to_points.inputs[3].default_value = 0.0

    # Node Sample Index
    sample_index = geometry_nodes_001_1.nodes.new("GeometryNodeSampleIndex")
    sample_index.name = "Sample Index"
    sample_index.clamp = False
    sample_index.data_type = 'FLOAT_VECTOR'
    sample_index.domain = 'POINT'

    # Node Position.001
    position_001 = geometry_nodes_001_1.nodes.new("GeometryNodeInputPosition")
    position_001.name = "Position.001"

    # Node Index
    index = geometry_nodes_001_1.nodes.new("GeometryNodeInputIndex")
    index.name = "Index"

    # Node Realize Instances
    realize_instances = geometry_nodes_001_1.nodes.new("GeometryNodeRealizeInstances")
    realize_instances.name = "Realize Instances"
    # Selection
    realize_instances.inputs[1].default_value = True
    # Realize All
    realize_instances.inputs[2].default_value = True
    # Depth
    realize_instances.inputs[3].default_value = 0

    # Node Set Position.001
    set_position_001 = geometry_nodes_001_1.nodes.new("GeometryNodeSetPosition")
    set_position_001.name = "Set Position.001"
    # Selection
    set_position_001.inputs[1].default_value = True
    # Offset
    set_position_001.inputs[3].default_value = (0.0, 0.0, 0.0)

    # Node Set Position
    set_position = geometry_nodes_001_1.nodes.new("GeometryNodeSetPosition")
    set_position.name = "Set Position"
    # Selection
    set_position.inputs[1].default_value = True
    # Offset
    set_position.inputs[3].default_value = (0.0, 0.0, 0.0)

    # Process zone input Simulation Input
    simulation_input.pair_with_output(simulation_output)



    # Set locations
    geometry_nodes_001_1.nodes["Group Input"].location = (-1224.3953857421875, -179.26084899902344)
    geometry_nodes_001_1.nodes["Group Output"].location = (921.4347534179688, -246.2064971923828)
    geometry_nodes_001_1.nodes["Simulation Input"].location = (-74.16285705566406, -143.55059814453125)
    geometry_nodes_001_1.nodes["Simulation Output"].location = (611.5438842773438, -200.75521850585938)
    geometry_nodes_001_1.nodes["Capture Attribute"].location = (154.31085205078125, -126.03953552246094)
    geometry_nodes_001_1.nodes["Position"].location = (-111.36146545410156, -386.9756774902344)
    geometry_nodes_001_1.nodes["Named Attribute"].location = (-102.1490478515625, -470.6581726074219)
    geometry_nodes_001_1.nodes["Group"].location = (309.4452819824219, -292.27996826171875)
    geometry_nodes_001_1.nodes["Collection Info"].location = (-1009.32177734375, 86.92550659179688)
    geometry_nodes_001_1.nodes["Mesh to Points"].location = (-582.4127807617188, 96.82801818847656)
    geometry_nodes_001_1.nodes["Sample Index"].location = (-410.7318115234375, 87.01919555664062)
    geometry_nodes_001_1.nodes["Position.001"].location = (-641.5189208984375, -193.10543823242188)
    geometry_nodes_001_1.nodes["Index"].location = (-634.4633178710938, -242.64747619628906)
    geometry_nodes_001_1.nodes["Realize Instances"].location = (-765.2047119140625, 114.92731475830078)
    geometry_nodes_001_1.nodes["Set Position.001"].location = (318.02685546875, -47.46184539794922)
    geometry_nodes_001_1.nodes["Set Position"].location = (-204.0633544921875, -70.75257873535156)

    # Set dimensions
    geometry_nodes_001_1.nodes["Group Input"].width  = 140.0
    geometry_nodes_001_1.nodes["Group Input"].height = 100.0

    geometry_nodes_001_1.nodes["Group Output"].width  = 140.0
    geometry_nodes_001_1.nodes["Group Output"].height = 100.0

    geometry_nodes_001_1.nodes["Simulation Input"].width  = 140.0
    geometry_nodes_001_1.nodes["Simulation Input"].height = 100.0

    geometry_nodes_001_1.nodes["Simulation Output"].width  = 140.0
    geometry_nodes_001_1.nodes["Simulation Output"].height = 100.0

    geometry_nodes_001_1.nodes["Capture Attribute"].width  = 140.0
    geometry_nodes_001_1.nodes["Capture Attribute"].height = 100.0

    geometry_nodes_001_1.nodes["Position"].width  = 140.0
    geometry_nodes_001_1.nodes["Position"].height = 100.0

    geometry_nodes_001_1.nodes["Named Attribute"].width  = 140.0
    geometry_nodes_001_1.nodes["Named Attribute"].height = 100.0

    geometry_nodes_001_1.nodes["Group"].width  = 242.075439453125
    geometry_nodes_001_1.nodes["Group"].height = 100.0

    geometry_nodes_001_1.nodes["Collection Info"].width  = 140.0
    geometry_nodes_001_1.nodes["Collection Info"].height = 100.0

    geometry_nodes_001_1.nodes["Mesh to Points"].width  = 140.0
    geometry_nodes_001_1.nodes["Mesh to Points"].height = 100.0

    geometry_nodes_001_1.nodes["Sample Index"].width  = 140.0
    geometry_nodes_001_1.nodes["Sample Index"].height = 100.0

    geometry_nodes_001_1.nodes["Position.001"].width  = 140.0
    geometry_nodes_001_1.nodes["Position.001"].height = 100.0

    geometry_nodes_001_1.nodes["Index"].width  = 140.0
    geometry_nodes_001_1.nodes["Index"].height = 100.0

    geometry_nodes_001_1.nodes["Realize Instances"].width  = 140.0
    geometry_nodes_001_1.nodes["Realize Instances"].height = 100.0

    geometry_nodes_001_1.nodes["Set Position.001"].width  = 140.0
    geometry_nodes_001_1.nodes["Set Position.001"].height = 100.0

    geometry_nodes_001_1.nodes["Set Position"].width  = 140.0
    geometry_nodes_001_1.nodes["Set Position"].height = 100.0


    # Initialize geometry_nodes_001_1 links

    # simulation_input.Geometry -> capture_attribute.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Simulation Input"].outputs[1],
        geometry_nodes_001_1.nodes["Capture Attribute"].inputs[0]
    )
    # position.Position -> capture_attribute.Position
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Position"].outputs[0],
        geometry_nodes_001_1.nodes["Capture Attribute"].inputs[1]
    )
    # capture_attribute.Position -> group.Prev Pos
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Capture Attribute"].outputs[1],
        geometry_nodes_001_1.nodes["Group"].inputs[1]
    )
    # named_attribute.Attribute -> group.Prev Vel
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Named Attribute"].outputs[0],
        geometry_nodes_001_1.nodes["Group"].inputs[2]
    )
    # simulation_input.Delta Time -> group.Delta Time
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Simulation Input"].outputs[0],
        geometry_nodes_001_1.nodes["Group"].inputs[3]
    )
    # group.Geometry -> simulation_output.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group"].outputs[0],
        geometry_nodes_001_1.nodes["Simulation Output"].inputs[1]
    )
    # group_input.Max Speed Vert -> group.Max Speed Vert
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group Input"].outputs[2],
        geometry_nodes_001_1.nodes["Group"].inputs[4]
    )
    # group_input.Max Speed Horiz -> group.Max Speed Horiz
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group Input"].outputs[3],
        geometry_nodes_001_1.nodes["Group"].inputs[5]
    )
    # group_input.Max Acc Vert -> group.Max Acc Vert
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group Input"].outputs[4],
        geometry_nodes_001_1.nodes["Group"].inputs[6]
    )
    # group_input.Max Acc Horiz -> group.Max Acc Horiz
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group Input"].outputs[5],
        geometry_nodes_001_1.nodes["Group"].inputs[7]
    )
    # group_input.Formation -> collection_info.Collection
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group Input"].outputs[1],
        geometry_nodes_001_1.nodes["Collection Info"].inputs[0]
    )
    # mesh_to_points.Points -> sample_index.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Mesh to Points"].outputs[0],
        geometry_nodes_001_1.nodes["Sample Index"].inputs[0]
    )
    # position_001.Position -> sample_index.Value
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Position.001"].outputs[0],
        geometry_nodes_001_1.nodes["Sample Index"].inputs[1]
    )
    # index.Index -> sample_index.Index
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Index"].outputs[0],
        geometry_nodes_001_1.nodes["Sample Index"].inputs[2]
    )
    # collection_info.Instances -> realize_instances.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Collection Info"].outputs[0],
        geometry_nodes_001_1.nodes["Realize Instances"].inputs[0]
    )
    # realize_instances.Geometry -> mesh_to_points.Mesh
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Realize Instances"].outputs[0],
        geometry_nodes_001_1.nodes["Mesh to Points"].inputs[0]
    )
    # group_input.Min Distance -> group.Min Distance
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group Input"].outputs[6],
        geometry_nodes_001_1.nodes["Group"].inputs[8]
    )
    # group_input.SkipCheck -> simulation_output.Skip
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group Input"].outputs[7],
        geometry_nodes_001_1.nodes["Simulation Output"].inputs[0]
    )
    # capture_attribute.Geometry -> set_position_001.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Capture Attribute"].outputs[0],
        geometry_nodes_001_1.nodes["Set Position.001"].inputs[0]
    )
    # sample_index.Value -> set_position_001.Position
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Sample Index"].outputs[0],
        geometry_nodes_001_1.nodes["Set Position.001"].inputs[2]
    )
    # set_position_001.Geometry -> group.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Set Position.001"].outputs[0],
        geometry_nodes_001_1.nodes["Group"].inputs[0]
    )
    # simulation_output.Geometry -> group_output.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Simulation Output"].outputs[0],
        geometry_nodes_001_1.nodes["Group Output"].inputs[0]
    )
    # group_input.Geometry -> set_position.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Group Input"].outputs[0],
        geometry_nodes_001_1.nodes["Set Position"].inputs[0]
    )
    # set_position.Geometry -> simulation_input.Geometry
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Set Position"].outputs[0],
        geometry_nodes_001_1.nodes["Simulation Input"].inputs[0]
    )
    # sample_index.Value -> set_position.Position
    geometry_nodes_001_1.links.new(
        geometry_nodes_001_1.nodes["Sample Index"].outputs[0],
        geometry_nodes_001_1.nodes["Set Position"].inputs[2]
    )

    return geometry_nodes_001_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    gn_drone_errorcheck = gn_drone_errorcheck_1_node_group(node_tree_names)
    node_tree_names[gn_drone_errorcheck_1_node_group] = gn_drone_errorcheck.name

    geometry_nodes_001 = geometry_nodes_001_1_node_group(node_tree_names)
    node_tree_names[geometry_nodes_001_1_node_group] = geometry_nodes_001.name

