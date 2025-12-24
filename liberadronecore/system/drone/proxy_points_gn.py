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

    # Socket Max Speed Up
    max_speed_up_socket = gn_drone_errorcheck_1.interface.new_socket(name="Max Speed Up", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_up_socket.default_value = 0.0
    max_speed_up_socket.min_value = -3.4028234663852886e+38
    max_speed_up_socket.max_value = 3.4028234663852886e+38
    max_speed_up_socket.subtype = 'NONE'
    max_speed_up_socket.attribute_domain = 'POINT'

    # Socket Max Speed Down
    max_speed_down_socket = gn_drone_errorcheck_1.interface.new_socket(name="Max Speed Down", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_down_socket.default_value = 0.0
    max_speed_down_socket.min_value = -3.4028234663852886e+38
    max_speed_down_socket.max_value = 3.4028234663852886e+38
    max_speed_down_socket.subtype = 'NONE'
    max_speed_down_socket.attribute_domain = 'POINT'

    # Socket Max Speed Horiz
    max_speed_horiz_socket = gn_drone_errorcheck_1.interface.new_socket(name="Max Speed Horiz", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_horiz_socket.default_value = 0.0
    max_speed_horiz_socket.min_value = -3.4028234663852886e+38
    max_speed_horiz_socket.max_value = 3.4028234663852886e+38
    max_speed_horiz_socket.subtype = 'NONE'
    max_speed_horiz_socket.attribute_domain = 'POINT'

    # Socket Max Acc
    max_acc_socket = gn_drone_errorcheck_1.interface.new_socket(name="Max Acc", in_out='INPUT', socket_type='NodeSocketFloat')
    max_acc_socket.default_value = 0.0
    max_acc_socket.min_value = -3.4028234663852886e+38
    max_acc_socket.max_value = 3.4028234663852886e+38
    max_acc_socket.subtype = 'NONE'
    max_acc_socket.attribute_domain = 'POINT'

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

    # Node Vector Math.002
    vector_math_002 = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math_002.name = "Vector Math.002"
    vector_math_002.operation = 'SUBTRACT'

    # Node Vector Math.003
    vector_math_003 = gn_drone_errorcheck_1.nodes.new("ShaderNodeVectorMath")
    vector_math_003.name = "Vector Math.003"
    vector_math_003.operation = 'DIVIDE'

    # Node Separate XYZ
    separate_xyz = gn_drone_errorcheck_1.nodes.new("ShaderNodeSeparateXYZ")
    separate_xyz.name = "Separate XYZ"

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
    store_named_attribute_004.inputs[2].default_value = "acc"

    # Node Compare
    compare = gn_drone_errorcheck_1.nodes.new("FunctionNodeCompare")
    compare.name = "Compare"
    compare.data_type = 'FLOAT'
    compare.mode = 'ELEMENT'
    compare.operation = 'GREATER_THAN'

    # Node Compare.005
    compare_005 = gn_drone_errorcheck_1.nodes.new("FunctionNodeCompare")
    compare_005.name = "Compare.005"
    compare_005.data_type = 'FLOAT'
    compare_005.mode = 'ELEMENT'
    compare_005.operation = 'LESS_THAN'

    # Node Math.002
    math_002 = gn_drone_errorcheck_1.nodes.new("ShaderNodeMath")
    math_002.name = "Math.002"
    math_002.operation = 'MULTIPLY'
    math_002.use_clamp = False
    # Value_001
    math_002.inputs[1].default_value = -1.0

    # Node Boolean Math
    boolean_math = gn_drone_errorcheck_1.nodes.new("FunctionNodeBooleanMath")
    boolean_math.name = "Boolean Math"
    boolean_math.operation = 'OR'

    # Node Store Named Attribute.006
    store_named_attribute_006 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_006.name = "Store Named Attribute.006"
    store_named_attribute_006.data_type = 'BOOLEAN'
    store_named_attribute_006.domain = 'POINT'
    # Selection
    store_named_attribute_006.inputs[1].default_value = True
    # Name
    store_named_attribute_006.inputs[2].default_value = "err_speed"

    # Node Compare.001
    compare_001 = gn_drone_errorcheck_1.nodes.new("FunctionNodeCompare")
    compare_001.name = "Compare.001"
    compare_001.data_type = 'FLOAT'
    compare_001.mode = 'ELEMENT'
    compare_001.operation = 'GREATER_THAN'

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
    store_named_attribute_008.inputs[2].default_value = "err_acc"

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

    # Node Boolean Math.001
    boolean_math_001 = gn_drone_errorcheck_1.nodes.new("FunctionNodeBooleanMath")
    boolean_math_001.name = "Boolean Math.001"
    boolean_math_001.operation = 'OR'

    # Node Store Named Attribute.005
    store_named_attribute_005 = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_005.name = "Store Named Attribute.005"
    store_named_attribute_005.data_type = 'FLOAT_VECTOR'
    store_named_attribute_005.domain = 'POINT'
    # Selection
    store_named_attribute_005.inputs[1].default_value = True
    # Name
    store_named_attribute_005.inputs[2].default_value = "vel"

    # Node Store Named Attribute
    store_named_attribute = gn_drone_errorcheck_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute.name = "Store Named Attribute"
    store_named_attribute.data_type = 'FLOAT_VECTOR'
    store_named_attribute.domain = 'POINT'
    # Selection
    store_named_attribute.inputs[1].default_value = True
    # Name
    store_named_attribute.inputs[2].default_value = "prev_pos"

    # Set locations
    gn_drone_errorcheck_1.nodes["Group Input"].location = (-710.4562377929688, -36.167781829833984)
    gn_drone_errorcheck_1.nodes["Group Output"].location = (1414.5443115234375, -324.6570129394531)
    gn_drone_errorcheck_1.nodes["Position"].location = (-775.8805541992188, -798.4730224609375)
    gn_drone_errorcheck_1.nodes["Vector Math"].location = (-423.8331298828125, -370.361083984375)
    gn_drone_errorcheck_1.nodes["Combine XYZ"].location = (-426.0843200683594, -785.4727172851562)
    gn_drone_errorcheck_1.nodes["Vector Math.001"].location = (-218.97227478027344, -461.51947021484375)
    gn_drone_errorcheck_1.nodes["Vector Math.002"].location = (31.8991756439209, -521.2974853515625)
    gn_drone_errorcheck_1.nodes["Vector Math.003"].location = (220.80526733398438, -451.8393249511719)
    gn_drone_errorcheck_1.nodes["Separate XYZ"].location = (-39.46705627441406, 30.304824829101562)
    gn_drone_errorcheck_1.nodes["Combine XYZ.001"].location = (171.32273864746094, 138.37579345703125)
    gn_drone_errorcheck_1.nodes["Vector Math.004"].location = (223.94143676757812, -128.6003875732422)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].location = (403.80999755859375, 264.58099365234375)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].location = (413.74462890625, 39.436771392822266)
    gn_drone_errorcheck_1.nodes["Vector Math.005"].location = (440.35882568359375, -446.8684387207031)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].location = (601.6134643554688, -183.7008056640625)
    gn_drone_errorcheck_1.nodes["Compare"].location = (800.0, 0.0)
    gn_drone_errorcheck_1.nodes["Compare.005"].location = (786.1950073242188, 142.165283203125)
    gn_drone_errorcheck_1.nodes["Math.002"].location = (600.0, 80.0)
    gn_drone_errorcheck_1.nodes["Boolean Math"].location = (955.5160522460938, 164.11087036132812)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].location = (1006.0552368164062, -143.1318359375)
    gn_drone_errorcheck_1.nodes["Compare.001"].location = (800.0, -180.0)
    gn_drone_errorcheck_1.nodes["Compare.002"].location = (783.6096801757812, -469.1745910644531)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].location = (1000.0, -350.0)
    gn_drone_errorcheck_1.nodes["Index of Nearest"].location = (81.34873962402344, -911.8710327148438)
    gn_drone_errorcheck_1.nodes["Sample Index"].location = (306.8037109375, -761.0812377929688)
    gn_drone_errorcheck_1.nodes["Vector Math.006"].location = (513.4815673828125, -743.3855590820312)
    gn_drone_errorcheck_1.nodes["Compare.004"].location = (762.1175537109375, -678.6265869140625)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.010"].location = (1001.7158203125, -562.5946044921875)
    gn_drone_errorcheck_1.nodes["Boolean Math.001"].location = (966.8374633789062, 14.716817855834961)
    gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].location = (407.29071044921875, -170.5794219970703)
    gn_drone_errorcheck_1.nodes["Store Named Attribute"].location = (234.66925048828125, -250.11599731445312)

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

    gn_drone_errorcheck_1.nodes["Vector Math.002"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.002"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.003"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.003"].height = 100.0

    gn_drone_errorcheck_1.nodes["Separate XYZ"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Separate XYZ"].height = 100.0

    gn_drone_errorcheck_1.nodes["Combine XYZ.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Combine XYZ.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.004"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.004"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].height = 100.0

    gn_drone_errorcheck_1.nodes["Vector Math.005"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Vector Math.005"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare.005"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare.005"].height = 100.0

    gn_drone_errorcheck_1.nodes["Math.002"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Math.002"].height = 100.0

    gn_drone_errorcheck_1.nodes["Boolean Math"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Boolean Math"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Compare.002"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Compare.002"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].height = 100.0

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

    gn_drone_errorcheck_1.nodes["Boolean Math.001"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Boolean Math.001"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].height = 100.0

    gn_drone_errorcheck_1.nodes["Store Named Attribute"].width  = 140.0
    gn_drone_errorcheck_1.nodes["Store Named Attribute"].height = 100.0


    # Initialize gn_drone_errorcheck_1 links

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
    # vector_math_001.Vector -> separate_xyz.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Separate XYZ"].inputs[0]
    )
    # separate_xyz.Z -> store_named_attribute_002.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ"].outputs[2],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].inputs[3]
    )
    # separate_xyz.Z -> compare.A
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ"].outputs[2],
        gn_drone_errorcheck_1.nodes["Compare"].inputs[0]
    )
    # separate_xyz.Z -> compare_005.A
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Separate XYZ"].outputs[2],
        gn_drone_errorcheck_1.nodes["Compare.005"].inputs[0]
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
    # group_input.Max Speed Up -> compare.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[4],
        gn_drone_errorcheck_1.nodes["Compare"].inputs[1]
    )
    # group_input.Max Speed Down -> math_002.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[5],
        gn_drone_errorcheck_1.nodes["Math.002"].inputs[0]
    )
    # math_002.Value -> compare_005.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Math.002"].outputs[0],
        gn_drone_errorcheck_1.nodes["Compare.005"].inputs[1]
    )
    # group_input.Max Speed Horiz -> compare_001.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[6],
        gn_drone_errorcheck_1.nodes["Compare.001"].inputs[1]
    )
    # group_input.Max Acc -> compare_002.B
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[7],
        gn_drone_errorcheck_1.nodes["Compare.002"].inputs[1]
    )
    # compare.Result -> boolean_math.Boolean
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare"].outputs[0],
        gn_drone_errorcheck_1.nodes["Boolean Math"].inputs[0]
    )
    # compare_005.Result -> boolean_math.Boolean
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare.005"].outputs[0],
        gn_drone_errorcheck_1.nodes["Boolean Math"].inputs[1]
    )
    # compare_002.Result -> store_named_attribute_008.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare.002"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].inputs[3]
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
    # vector_math_003.Vector -> vector_math_005.Vector
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.003"].outputs[0],
        gn_drone_errorcheck_1.nodes["Vector Math.005"].inputs[0]
    )
    # vector_math_005.Value -> store_named_attribute_004.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.005"].outputs[1],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].inputs[3]
    )
    # store_named_attribute_004.Geometry -> store_named_attribute_006.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].inputs[0]
    )
    # vector_math_005.Value -> compare_002.A
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.005"].outputs[1],
        gn_drone_errorcheck_1.nodes["Compare.002"].inputs[0]
    )
    # store_named_attribute_008.Geometry -> store_named_attribute_010.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.010"].inputs[0]
    )
    # boolean_math.Boolean -> boolean_math_001.Boolean
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Boolean Math"].outputs[0],
        gn_drone_errorcheck_1.nodes["Boolean Math.001"].inputs[0]
    )
    # compare_001.Result -> boolean_math_001.Boolean
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Compare.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Boolean Math.001"].inputs[1]
    )
    # boolean_math_001.Boolean -> store_named_attribute_006.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Boolean Math.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].inputs[3]
    )
    # store_named_attribute_006.Geometry -> store_named_attribute_008.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.006"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.008"].inputs[0]
    )
    # store_named_attribute_003.Geometry -> store_named_attribute_002.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].inputs[0]
    )
    # store_named_attribute_002.Geometry -> store_named_attribute_004.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.002"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.004"].inputs[0]
    )
    # store_named_attribute_005.Geometry -> store_named_attribute_003.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.003"].inputs[0]
    )
    # position.Position -> store_named_attribute.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Position"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute"].inputs[3]
    )
    # group_input.Geometry -> store_named_attribute.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Group Input"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute"].inputs[0]
    )
    # store_named_attribute.Geometry -> store_named_attribute_005.Geometry
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Store Named Attribute"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].inputs[0]
    )
    # vector_math_001.Vector -> store_named_attribute_005.Value
    gn_drone_errorcheck_1.links.new(
        gn_drone_errorcheck_1.nodes["Vector Math.001"].outputs[0],
        gn_drone_errorcheck_1.nodes["Store Named Attribute.005"].inputs[3]
    )

    return gn_drone_errorcheck_1


def gn_proxypoints_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize GN_ProxyPoints node group"""
    gn_proxypoints_1 = bpy.data.node_groups.new(type='GeometryNodeTree', name="GN_ProxyPoints")

    gn_proxypoints_1.color_tag = 'NONE'
    gn_proxypoints_1.description = ""
    gn_proxypoints_1.default_group_node_width = 140
    gn_proxypoints_1.is_modifier = True

    # gn_proxypoints_1 interface

    # Socket Geometry
    geometry_socket = gn_proxypoints_1.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    # Socket Geometry
    geometry_socket_1 = gn_proxypoints_1.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'

    # Socket Formation
    formation_socket = gn_proxypoints_1.interface.new_socket(name="Formation", in_out='INPUT', socket_type='NodeSocketCollection')
    formation_socket.attribute_domain = 'POINT'

    # Socket Max Speed Up
    max_speed_up_socket = gn_proxypoints_1.interface.new_socket(name="Max Speed Up", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_up_socket.default_value = 0.0
    max_speed_up_socket.min_value = -3.4028234663852886e+38
    max_speed_up_socket.max_value = 3.4028234663852886e+38
    max_speed_up_socket.subtype = 'NONE'
    max_speed_up_socket.attribute_domain = 'POINT'

    # Socket Max Speed Down
    max_speed_down_socket = gn_proxypoints_1.interface.new_socket(name="Max Speed Down", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_down_socket.default_value = 0.0
    max_speed_down_socket.min_value = -3.4028234663852886e+38
    max_speed_down_socket.max_value = 3.4028234663852886e+38
    max_speed_down_socket.subtype = 'NONE'
    max_speed_down_socket.attribute_domain = 'POINT'

    # Socket Max Speed Horiz
    max_speed_horiz_socket = gn_proxypoints_1.interface.new_socket(name="Max Speed Horiz", in_out='INPUT', socket_type='NodeSocketFloat')
    max_speed_horiz_socket.default_value = 0.0
    max_speed_horiz_socket.min_value = -3.4028234663852886e+38
    max_speed_horiz_socket.max_value = 3.4028234663852886e+38
    max_speed_horiz_socket.subtype = 'NONE'
    max_speed_horiz_socket.attribute_domain = 'POINT'

    # Socket Max Acc
    max_acc_socket = gn_proxypoints_1.interface.new_socket(name="Max Acc", in_out='INPUT', socket_type='NodeSocketFloat')
    max_acc_socket.default_value = 0.0
    max_acc_socket.min_value = -3.4028234663852886e+38
    max_acc_socket.max_value = 3.4028234663852886e+38
    max_acc_socket.subtype = 'NONE'
    max_acc_socket.attribute_domain = 'POINT'

    # Socket Min Distance
    min_distance_socket = gn_proxypoints_1.interface.new_socket(name="Min Distance", in_out='INPUT', socket_type='NodeSocketFloat')
    min_distance_socket.default_value = 0.0
    min_distance_socket.min_value = -3.4028234663852886e+38
    min_distance_socket.max_value = 3.4028234663852886e+38
    min_distance_socket.subtype = 'NONE'
    min_distance_socket.attribute_domain = 'POINT'

    # Socket SkipCheck
    skipcheck_socket = gn_proxypoints_1.interface.new_socket(name="SkipCheck", in_out='INPUT', socket_type='NodeSocketBool')
    skipcheck_socket.default_value = False
    skipcheck_socket.attribute_domain = 'POINT'
    skipcheck_socket.hide_value = True

    # Initialize gn_proxypoints_1 nodes

    # Node Group Input
    group_input = gn_proxypoints_1.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Group Output
    group_output = gn_proxypoints_1.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Simulation Input
    simulation_input = gn_proxypoints_1.nodes.new("GeometryNodeSimulationInput")
    simulation_input.name = "Simulation Input"
    # Node Simulation Output
    simulation_output = gn_proxypoints_1.nodes.new("GeometryNodeSimulationOutput")
    simulation_output.name = "Simulation Output"
    simulation_output.active_index = 0
    simulation_output.state_items.clear()
    # Create item "Geometry"
    simulation_output.state_items.new('GEOMETRY', "Geometry")
    simulation_output.state_items[0].attribute_domain = 'POINT'

    # Node Named Attribute
    named_attribute = gn_proxypoints_1.nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute.name = "Named Attribute"
    named_attribute.data_type = 'FLOAT_VECTOR'
    # Name
    named_attribute.inputs[0].default_value = "vel"

    # Node Group
    group = gn_proxypoints_1.nodes.new("GeometryNodeGroup")
    group.name = "Group"
    group.node_tree = bpy.data.node_groups[node_tree_names[gn_drone_errorcheck_1_node_group]]

    # Node Collection Info
    collection_info = gn_proxypoints_1.nodes.new("GeometryNodeCollectionInfo")
    collection_info.name = "Collection Info"
    collection_info.transform_space = 'ORIGINAL'
    # Separate Children
    collection_info.inputs[1].default_value = False
    # Reset Children
    collection_info.inputs[2].default_value = False

    # Node Mesh to Points
    mesh_to_points = gn_proxypoints_1.nodes.new("GeometryNodeMeshToPoints")
    mesh_to_points.name = "Mesh to Points"
    mesh_to_points.mode = 'VERTICES'
    # Selection
    mesh_to_points.inputs[1].default_value = True
    # Position
    mesh_to_points.inputs[2].default_value = (0.0, 0.0, 0.0)
    # Radius
    mesh_to_points.inputs[3].default_value = 0.0

    # Node Sample Index
    sample_index = gn_proxypoints_1.nodes.new("GeometryNodeSampleIndex")
    sample_index.name = "Sample Index"
    sample_index.clamp = False
    sample_index.data_type = 'FLOAT_VECTOR'
    sample_index.domain = 'POINT'

    # Node Position.001
    position_001 = gn_proxypoints_1.nodes.new("GeometryNodeInputPosition")
    position_001.name = "Position.001"

    # Node Index
    index = gn_proxypoints_1.nodes.new("GeometryNodeInputIndex")
    index.name = "Index"

    # Node Realize Instances
    realize_instances = gn_proxypoints_1.nodes.new("GeometryNodeRealizeInstances")
    realize_instances.name = "Realize Instances"
    # Selection
    realize_instances.inputs[1].default_value = True
    # Realize All
    realize_instances.inputs[2].default_value = True
    # Depth
    realize_instances.inputs[3].default_value = 0

    # Node Set Position.001
    set_position_001 = gn_proxypoints_1.nodes.new("GeometryNodeSetPosition")
    set_position_001.name = "Set Position.001"
    # Selection
    set_position_001.inputs[1].default_value = True
    # Offset
    set_position_001.inputs[3].default_value = (0.0, 0.0, 0.0)

    # Node Set Position
    set_position = gn_proxypoints_1.nodes.new("GeometryNodeSetPosition")
    set_position.name = "Set Position"
    # Selection
    set_position.inputs[1].default_value = True
    # Offset
    set_position.inputs[3].default_value = (0.0, 0.0, 0.0)

    # Node Named Attribute.001
    named_attribute_001 = gn_proxypoints_1.nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute_001.name = "Named Attribute.001"
    named_attribute_001.data_type = 'FLOAT_VECTOR'
    # Name
    named_attribute_001.inputs[0].default_value = "prev_pos"

    # Node Capture Attribute
    capture_attribute = gn_proxypoints_1.nodes.new("GeometryNodeCaptureAttribute")
    capture_attribute.name = "Capture Attribute"
    capture_attribute.active_index = 1
    capture_attribute.capture_items.clear()
    capture_attribute.capture_items.new('FLOAT', "Attribute")
    capture_attribute.capture_items["Attribute"].data_type = 'FLOAT_VECTOR'
    capture_attribute.capture_items.new('FLOAT', "Attribute.001")
    capture_attribute.capture_items["Attribute.001"].data_type = 'FLOAT_VECTOR'
    capture_attribute.domain = 'POINT'

    # Process zone input Simulation Input
    simulation_input.pair_with_output(simulation_output)



    # Set locations
    gn_proxypoints_1.nodes["Group Input"].location = (-1224.3953857421875, -179.26084899902344)
    gn_proxypoints_1.nodes["Group Output"].location = (1036.3668212890625, -200.17587280273438)
    gn_proxypoints_1.nodes["Simulation Input"].location = (-74.16285705566406, -143.55059814453125)
    gn_proxypoints_1.nodes["Simulation Output"].location = (794.2518920898438, -47.84729766845703)
    gn_proxypoints_1.nodes["Named Attribute"].location = (-102.1490478515625, -470.6581726074219)
    gn_proxypoints_1.nodes["Group"].location = (520.9176025390625, -142.02915954589844)
    gn_proxypoints_1.nodes["Collection Info"].location = (-1009.32177734375, 86.92550659179688)
    gn_proxypoints_1.nodes["Mesh to Points"].location = (-582.4127807617188, 96.82801818847656)
    gn_proxypoints_1.nodes["Sample Index"].location = (-410.7318115234375, 87.01919555664062)
    gn_proxypoints_1.nodes["Position.001"].location = (-641.5189208984375, -193.10543823242188)
    gn_proxypoints_1.nodes["Index"].location = (-634.4633178710938, -242.64747619628906)
    gn_proxypoints_1.nodes["Realize Instances"].location = (-765.2047119140625, 114.92731475830078)
    gn_proxypoints_1.nodes["Set Position.001"].location = (124.7191162109375, 30.70676612854004)
    gn_proxypoints_1.nodes["Set Position"].location = (-277.8728332519531, -153.45828247070312)
    gn_proxypoints_1.nodes["Named Attribute.001"].location = (-98.857666015625, -332.0057678222656)
    gn_proxypoints_1.nodes["Capture Attribute"].location = (314.76611328125, -118.56640625)

    # Set dimensions
    gn_proxypoints_1.nodes["Group Input"].width  = 140.0
    gn_proxypoints_1.nodes["Group Input"].height = 100.0

    gn_proxypoints_1.nodes["Group Output"].width  = 140.0
    gn_proxypoints_1.nodes["Group Output"].height = 100.0

    gn_proxypoints_1.nodes["Simulation Input"].width  = 140.0
    gn_proxypoints_1.nodes["Simulation Input"].height = 100.0

    gn_proxypoints_1.nodes["Simulation Output"].width  = 140.0
    gn_proxypoints_1.nodes["Simulation Output"].height = 100.0

    gn_proxypoints_1.nodes["Named Attribute"].width  = 140.0
    gn_proxypoints_1.nodes["Named Attribute"].height = 100.0

    gn_proxypoints_1.nodes["Group"].width  = 242.075439453125
    gn_proxypoints_1.nodes["Group"].height = 100.0

    gn_proxypoints_1.nodes["Collection Info"].width  = 140.0
    gn_proxypoints_1.nodes["Collection Info"].height = 100.0

    gn_proxypoints_1.nodes["Mesh to Points"].width  = 140.0
    gn_proxypoints_1.nodes["Mesh to Points"].height = 100.0

    gn_proxypoints_1.nodes["Sample Index"].width  = 140.0
    gn_proxypoints_1.nodes["Sample Index"].height = 100.0

    gn_proxypoints_1.nodes["Position.001"].width  = 140.0
    gn_proxypoints_1.nodes["Position.001"].height = 100.0

    gn_proxypoints_1.nodes["Index"].width  = 140.0
    gn_proxypoints_1.nodes["Index"].height = 100.0

    gn_proxypoints_1.nodes["Realize Instances"].width  = 140.0
    gn_proxypoints_1.nodes["Realize Instances"].height = 100.0

    gn_proxypoints_1.nodes["Set Position.001"].width  = 140.0
    gn_proxypoints_1.nodes["Set Position.001"].height = 100.0

    gn_proxypoints_1.nodes["Set Position"].width  = 140.0
    gn_proxypoints_1.nodes["Set Position"].height = 100.0

    gn_proxypoints_1.nodes["Named Attribute.001"].width  = 140.0
    gn_proxypoints_1.nodes["Named Attribute.001"].height = 100.0

    gn_proxypoints_1.nodes["Capture Attribute"].width  = 140.0
    gn_proxypoints_1.nodes["Capture Attribute"].height = 100.0


    # Initialize gn_proxypoints_1 links

    # simulation_input.Delta Time -> group.Delta Time
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Simulation Input"].outputs[0],
        gn_proxypoints_1.nodes["Group"].inputs[3]
    )
    # group.Geometry -> simulation_output.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group"].outputs[0],
        gn_proxypoints_1.nodes["Simulation Output"].inputs[1]
    )
    # group_input.Max Speed Up -> group.Max Speed Up
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group Input"].outputs[2],
        gn_proxypoints_1.nodes["Group"].inputs[4]
    )
    # group_input.Max Speed Down -> group.Max Speed Down
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group Input"].outputs[3],
        gn_proxypoints_1.nodes["Group"].inputs[5]
    )
    # group_input.Max Speed Horiz -> group.Max Speed Horiz
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group Input"].outputs[4],
        gn_proxypoints_1.nodes["Group"].inputs[6]
    )
    # group_input.Max Acc -> group.Max Acc
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group Input"].outputs[5],
        gn_proxypoints_1.nodes["Group"].inputs[7]
    )
    # group_input.Formation -> collection_info.Collection
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group Input"].outputs[1],
        gn_proxypoints_1.nodes["Collection Info"].inputs[0]
    )
    # mesh_to_points.Points -> sample_index.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Mesh to Points"].outputs[0],
        gn_proxypoints_1.nodes["Sample Index"].inputs[0]
    )
    # position_001.Position -> sample_index.Value
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Position.001"].outputs[0],
        gn_proxypoints_1.nodes["Sample Index"].inputs[1]
    )
    # index.Index -> sample_index.Index
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Index"].outputs[0],
        gn_proxypoints_1.nodes["Sample Index"].inputs[2]
    )
    # collection_info.Instances -> realize_instances.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Collection Info"].outputs[0],
        gn_proxypoints_1.nodes["Realize Instances"].inputs[0]
    )
    # realize_instances.Geometry -> mesh_to_points.Mesh
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Realize Instances"].outputs[0],
        gn_proxypoints_1.nodes["Mesh to Points"].inputs[0]
    )
    # group_input.Min Distance -> group.Min Distance
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group Input"].outputs[6],
        gn_proxypoints_1.nodes["Group"].inputs[8]
    )
    # group_input.SkipCheck -> simulation_output.Skip
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group Input"].outputs[7],
        gn_proxypoints_1.nodes["Simulation Output"].inputs[0]
    )
    # sample_index.Value -> set_position_001.Position
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Sample Index"].outputs[0],
        gn_proxypoints_1.nodes["Set Position.001"].inputs[2]
    )
    # group_input.Geometry -> set_position.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Group Input"].outputs[0],
        gn_proxypoints_1.nodes["Set Position"].inputs[0]
    )
    # set_position.Geometry -> simulation_input.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Set Position"].outputs[0],
        gn_proxypoints_1.nodes["Simulation Input"].inputs[0]
    )
    # sample_index.Value -> set_position.Position
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Sample Index"].outputs[0],
        gn_proxypoints_1.nodes["Set Position"].inputs[2]
    )
    # simulation_input.Geometry -> set_position_001.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Simulation Input"].outputs[1],
        gn_proxypoints_1.nodes["Set Position.001"].inputs[0]
    )
    # set_position_001.Geometry -> capture_attribute.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Set Position.001"].outputs[0],
        gn_proxypoints_1.nodes["Capture Attribute"].inputs[0]
    )
    # simulation_output.Geometry -> group_output.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Simulation Output"].outputs[0],
        gn_proxypoints_1.nodes["Group Output"].inputs[0]
    )
    # named_attribute_001.Attribute -> capture_attribute.Attribute
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Named Attribute.001"].outputs[0],
        gn_proxypoints_1.nodes["Capture Attribute"].inputs[1]
    )
    # capture_attribute.Attribute -> group.Prev Pos
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Capture Attribute"].outputs[1],
        gn_proxypoints_1.nodes["Group"].inputs[1]
    )
    # named_attribute.Attribute -> capture_attribute.Attribute.001
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Named Attribute"].outputs[0],
        gn_proxypoints_1.nodes["Capture Attribute"].inputs[2]
    )
    # capture_attribute.Attribute.001 -> group.Prev Vel
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Capture Attribute"].outputs[2],
        gn_proxypoints_1.nodes["Group"].inputs[2]
    )
    # capture_attribute.Geometry -> group.Geometry
    gn_proxypoints_1.links.new(
        gn_proxypoints_1.nodes["Capture Attribute"].outputs[0],
        gn_proxypoints_1.nodes["Group"].inputs[0]
    )

    return gn_proxypoints_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    gn_drone_errorcheck = gn_drone_errorcheck_1_node_group(node_tree_names)
    node_tree_names[gn_drone_errorcheck_1_node_group] = gn_drone_errorcheck.name

    gn_proxypoints = gn_proxypoints_1_node_group(node_tree_names)
    node_tree_names[gn_proxypoints_1_node_group] = gn_proxypoints.name

