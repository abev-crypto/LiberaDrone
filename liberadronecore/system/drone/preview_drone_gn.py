import bpy
import mathutils
import os
import typing


def geometry_nodes_002_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize GN_PreviewDrone node group"""
    gn_previewdrone_1 = bpy.data.node_groups.new(type='GeometryNodeTree', name="GN_PreviewDrone")

    gn_previewdrone_1.color_tag = 'NONE'
    gn_previewdrone_1.description = ""
    gn_previewdrone_1.default_group_node_width = 140
    gn_previewdrone_1.is_modifier = True

    # gn_previewdrone_1 interface

    # Socket Geometry
    geometry_socket = gn_previewdrone_1.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    # Socket Geometry
    geometry_socket_1 = gn_previewdrone_1.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'

    # Socket Material
    material_socket = gn_previewdrone_1.interface.new_socket(name="Material", in_out='INPUT', socket_type='NodeSocketMaterial')
    material_socket.attribute_domain = 'POINT'

    # Socket ColorVerts
    colorverts_socket = gn_previewdrone_1.interface.new_socket(name="ColorVerts", in_out='INPUT', socket_type='NodeSocketObject')
    colorverts_socket.attribute_domain = 'POINT'

    # Socket Scale
    scale_socket = gn_previewdrone_1.interface.new_socket(name="Scale", in_out='INPUT', socket_type='NodeSocketFloat')
    scale_socket.default_value = 0.4000000059604645
    scale_socket.min_value = 0.0
    scale_socket.max_value = 3.4028234663852886e+38
    scale_socket.subtype = 'NONE'
    scale_socket.attribute_domain = 'POINT'

    # Socket ShowRing
    showring_socket = gn_previewdrone_1.interface.new_socket(name="ShowRing", in_out='INPUT', socket_type='NodeSocketBool')
    showring_socket.default_value = False
    showring_socket.attribute_domain = 'POINT'

    # Socket Collection
    collection_socket = gn_previewdrone_1.interface.new_socket(name="Collection", in_out='INPUT', socket_type='NodeSocketCollection')
    collection_socket.attribute_domain = 'POINT'

    # Initialize gn_previewdrone_1 nodes

    # Node Group Input
    group_input = gn_previewdrone_1.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Group Output
    group_output = gn_previewdrone_1.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Instance on Points
    instance_on_points = gn_previewdrone_1.nodes.new("GeometryNodeInstanceOnPoints")
    instance_on_points.name = "Instance on Points"
    # Selection
    instance_on_points.inputs[1].default_value = True
    # Pick Instance
    instance_on_points.inputs[3].default_value = False
    # Instance Index
    instance_on_points.inputs[4].default_value = 0
    # Rotation
    instance_on_points.inputs[5].default_value = (0.0, 0.0, 0.0)
    # Scale
    instance_on_points.inputs[6].default_value = (1.0, 1.0, 1.0)

    # Node Switch
    switch = gn_previewdrone_1.nodes.new("GeometryNodeSwitch")
    switch.name = "Switch"
    switch.input_type = 'GEOMETRY'

    # Node Scale Elements
    scale_elements = gn_previewdrone_1.nodes.new("GeometryNodeScaleElements")
    scale_elements.name = "Scale Elements"
    scale_elements.domain = 'FACE'
    scale_elements.scale_mode = 'UNIFORM'
    # Selection
    scale_elements.inputs[1].default_value = True
    # Center
    scale_elements.inputs[3].default_value = (0.0, 0.0, 0.0)

    # Node Join Geometry
    join_geometry = gn_previewdrone_1.nodes.new("GeometryNodeJoinGeometry")
    join_geometry.name = "Join Geometry"

    # Node Transform Geometry
    transform_geometry = gn_previewdrone_1.nodes.new("GeometryNodeTransform")
    transform_geometry.name = "Transform Geometry"
    transform_geometry.mode = 'COMPONENTS'
    # Translation
    transform_geometry.inputs[1].default_value = (0.0, 0.0, 0.0)
    # Scale
    transform_geometry.inputs[3].default_value = (1.0, 1.0, 1.0)

    # Node Align Rotation to Vector
    align_rotation_to_vector = gn_previewdrone_1.nodes.new("FunctionNodeAlignRotationToVector")
    align_rotation_to_vector.name = "Align Rotation to Vector"
    align_rotation_to_vector.axis = 'Y'
    align_rotation_to_vector.pivot_axis = 'Y'
    # Factor
    align_rotation_to_vector.inputs[1].default_value = 1.0
    # Vector
    align_rotation_to_vector.inputs[2].default_value = (1.0, 0.0, 0.0)

    # Node Object Info
    object_info = gn_previewdrone_1.nodes.new("GeometryNodeObjectInfo")
    object_info.name = "Object Info"
    object_info.transform_space = 'ORIGINAL'
    # As Instance
    object_info.inputs[1].default_value = False

    # Node Active Camera
    active_camera = gn_previewdrone_1.nodes.new("GeometryNodeInputActiveCamera")
    active_camera.name = "Active Camera"

    # Node Curve to Mesh
    curve_to_mesh = gn_previewdrone_1.nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.name = "Curve to Mesh"
    # Fill Caps
    curve_to_mesh.inputs[2].default_value = False

    # Node Curve Circle
    curve_circle = gn_previewdrone_1.nodes.new("GeometryNodeCurvePrimitiveCircle")
    curve_circle.name = "Curve Circle"
    curve_circle.mode = 'RADIUS'
    # Resolution
    curve_circle.inputs[0].default_value = 24
    # Radius
    curve_circle.inputs[4].default_value = 0.7799999713897705

    # Node Curve Circle.001
    curve_circle_001 = gn_previewdrone_1.nodes.new("GeometryNodeCurvePrimitiveCircle")
    curve_circle_001.name = "Curve Circle.001"
    curve_circle_001.mode = 'RADIUS'
    # Resolution
    curve_circle_001.inputs[0].default_value = 3
    # Radius
    curve_circle_001.inputs[4].default_value = 0.004999999888241291

    # Node Set Material
    set_material = gn_previewdrone_1.nodes.new("GeometryNodeSetMaterial")
    set_material.name = "Set Material"
    # Selection
    set_material.inputs[1].default_value = True

    # Node Realize Instances
    realize_instances = gn_previewdrone_1.nodes.new("GeometryNodeRealizeInstances")
    realize_instances.name = "Realize Instances"
    # Selection
    realize_instances.inputs[1].default_value = True
    # Realize All
    realize_instances.inputs[2].default_value = True
    # Depth
    realize_instances.inputs[3].default_value = 0

    # Node Collection Info
    collection_info = gn_previewdrone_1.nodes.new("GeometryNodeCollectionInfo")
    collection_info.name = "Collection Info"
    collection_info.transform_space = 'ORIGINAL'
    # Separate Children
    collection_info.inputs[1].default_value = False
    # Reset Children
    collection_info.inputs[2].default_value = False

    # Node Mesh to Points
    mesh_to_points = gn_previewdrone_1.nodes.new("GeometryNodeMeshToPoints")
    mesh_to_points.name = "Mesh to Points"
    mesh_to_points.mode = 'VERTICES'
    # Selection
    mesh_to_points.inputs[1].default_value = True
    # Position
    mesh_to_points.inputs[2].default_value = (0.0, 0.0, 0.0)
    # Radius
    mesh_to_points.inputs[3].default_value = 0.0

    # Node Sample Index.001
    sample_index_001 = gn_previewdrone_1.nodes.new("GeometryNodeSampleIndex")
    sample_index_001.name = "Sample Index.001"
    sample_index_001.clamp = False
    sample_index_001.data_type = 'FLOAT_VECTOR'
    sample_index_001.domain = 'POINT'

    # Node Position.001
    position_001 = gn_previewdrone_1.nodes.new("GeometryNodeInputPosition")
    position_001.name = "Position.001"

    # Node Realize Instances.001
    realize_instances_001 = gn_previewdrone_1.nodes.new("GeometryNodeRealizeInstances")
    realize_instances_001.name = "Realize Instances.001"
    # Selection
    realize_instances_001.inputs[1].default_value = True
    # Realize All
    realize_instances_001.inputs[2].default_value = True
    # Depth
    realize_instances_001.inputs[3].default_value = 0

    # Node Set Position.001
    set_position_001 = gn_previewdrone_1.nodes.new("GeometryNodeSetPosition")
    set_position_001.name = "Set Position.001"
    # Selection
    set_position_001.inputs[1].default_value = True
    # Offset
    set_position_001.inputs[3].default_value = (0.0, 0.0, 0.0)

    # Node Named Attribute.002
    named_attribute_002 = gn_previewdrone_1.nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute_002.name = "Named Attribute.002"
    named_attribute_002.data_type = 'INT'
    # Name
    named_attribute_002.inputs[0].default_value = "pair_id"

    # Node Sample Index.002
    sample_index_002 = gn_previewdrone_1.nodes.new("GeometryNodeSampleIndex")
    sample_index_002.name = "Sample Index.002"
    sample_index_002.clamp = False
    sample_index_002.data_type = 'INT'
    sample_index_002.domain = 'POINT'

    # Node ID.001
    id_001 = gn_previewdrone_1.nodes.new("GeometryNodeInputID")
    id_001.name = "ID.001"

    # Node Object Info.002
    object_info_002 = gn_previewdrone_1.nodes.new("GeometryNodeObjectInfo")
    object_info_002.name = "Object Info.002"
    object_info_002.transform_space = 'ORIGINAL'
    # As Instance
    object_info_002.inputs[1].default_value = False

    # Node Sample Index.003
    sample_index_003 = gn_previewdrone_1.nodes.new("GeometryNodeSampleIndex")
    sample_index_003.name = "Sample Index.003"
    sample_index_003.clamp = False
    sample_index_003.data_type = 'FLOAT_COLOR'
    sample_index_003.domain = 'POINT'

    # Node Named Attribute.003
    named_attribute_003 = gn_previewdrone_1.nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute_003.name = "Named Attribute.003"
    named_attribute_003.data_type = 'FLOAT_COLOR'
    # Name
    named_attribute_003.inputs[0].default_value = "color"

    # Node Store Named Attribute.002
    store_named_attribute_002 = gn_previewdrone_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_002.name = "Store Named Attribute.002"
    store_named_attribute_002.data_type = 'FLOAT_COLOR'
    store_named_attribute_002.domain = 'POINT'
    # Selection
    store_named_attribute_002.inputs[1].default_value = True
    # Name
    store_named_attribute_002.inputs[2].default_value = "color"

    # Set locations
    gn_previewdrone_1.nodes["Group Input"].location = (-1432.6986083984375, -195.94091796875)
    gn_previewdrone_1.nodes["Group Output"].location = (1387.057373046875, -226.60000610351562)
    gn_previewdrone_1.nodes["Instance on Points"].location = (523.25341796875, -190.7473907470703)
    gn_previewdrone_1.nodes["Switch"].location = (357.25885009765625, -435.17657470703125)
    gn_previewdrone_1.nodes["Scale Elements"].location = (-55.24286651611328, -446.0585632324219)
    gn_previewdrone_1.nodes["Join Geometry"].location = (163.46734619140625, -605.8854370117188)
    gn_previewdrone_1.nodes["Transform Geometry"].location = (-428.240234375, -595.8190307617188)
    gn_previewdrone_1.nodes["Align Rotation to Vector"].location = (-820.0733642578125, -625.8809204101562)
    gn_previewdrone_1.nodes["Object Info"].location = (-1043.7431640625, -677.852294921875)
    gn_previewdrone_1.nodes["Active Camera"].location = (-1259.0733642578125, -717.1326904296875)
    gn_previewdrone_1.nodes["Curve to Mesh"].location = (-813.9481201171875, -431.56982421875)
    gn_previewdrone_1.nodes["Curve Circle"].location = (-1106.529052734375, -392.12493896484375)
    gn_previewdrone_1.nodes["Curve Circle.001"].location = (-1013.5692138671875, -488.5165710449219)
    gn_previewdrone_1.nodes["Set Material"].location = (762.8192138671875, -171.77645874023438)
    gn_previewdrone_1.nodes["Realize Instances"].location = (1087.3343505859375, 111.81198120117188)
    gn_previewdrone_1.nodes["Collection Info"].location = (-872.1196899414062, 179.70042419433594)
    gn_previewdrone_1.nodes["Mesh to Points"].location = (-488.7879333496094, 248.0230712890625)
    gn_previewdrone_1.nodes["Sample Index.001"].location = (-102.45191192626953, 158.53439331054688)
    gn_previewdrone_1.nodes["Position.001"].location = (-317.8730773925781, 122.717529296875)
    gn_previewdrone_1.nodes["Realize Instances.001"].location = (-669.91357421875, 193.93832397460938)
    gn_previewdrone_1.nodes["Set Position.001"].location = (81.63373565673828, 140.4084014892578)
    gn_previewdrone_1.nodes["Named Attribute.002"].location = (-494.51153564453125, 53.61726379394531)
    gn_previewdrone_1.nodes["Sample Index.002"].location = (-306.16131591796875, 34.87187194824219)
    gn_previewdrone_1.nodes["ID.001"].location = (-493.95587158203125, -97.29049682617188)
    gn_previewdrone_1.nodes["Object Info.002"].location = (-816.2116088867188, -37.546546936035156)
    gn_previewdrone_1.nodes["Sample Index.003"].location = (-5.7613067626953125, -85.14237213134766)
    gn_previewdrone_1.nodes["Named Attribute.003"].location = (-625.8030395507812, -121.86918640136719)
    gn_previewdrone_1.nodes["Store Named Attribute.002"].location = (254.76429748535156, 26.838600158691406)

    # Set dimensions
    gn_previewdrone_1.nodes["Group Input"].width  = 140.0
    gn_previewdrone_1.nodes["Group Input"].height = 100.0

    gn_previewdrone_1.nodes["Group Output"].width  = 140.0
    gn_previewdrone_1.nodes["Group Output"].height = 100.0

    gn_previewdrone_1.nodes["Instance on Points"].width  = 140.0
    gn_previewdrone_1.nodes["Instance on Points"].height = 100.0

    gn_previewdrone_1.nodes["Switch"].width  = 140.0
    gn_previewdrone_1.nodes["Switch"].height = 100.0

    gn_previewdrone_1.nodes["Scale Elements"].width  = 140.0
    gn_previewdrone_1.nodes["Scale Elements"].height = 100.0

    gn_previewdrone_1.nodes["Join Geometry"].width  = 140.0
    gn_previewdrone_1.nodes["Join Geometry"].height = 100.0

    gn_previewdrone_1.nodes["Transform Geometry"].width  = 140.0
    gn_previewdrone_1.nodes["Transform Geometry"].height = 100.0

    gn_previewdrone_1.nodes["Align Rotation to Vector"].width  = 140.0
    gn_previewdrone_1.nodes["Align Rotation to Vector"].height = 100.0

    gn_previewdrone_1.nodes["Object Info"].width  = 140.0
    gn_previewdrone_1.nodes["Object Info"].height = 100.0

    gn_previewdrone_1.nodes["Active Camera"].width  = 140.0
    gn_previewdrone_1.nodes["Active Camera"].height = 100.0

    gn_previewdrone_1.nodes["Curve to Mesh"].width  = 140.0
    gn_previewdrone_1.nodes["Curve to Mesh"].height = 100.0

    gn_previewdrone_1.nodes["Curve Circle"].width  = 179.333740234375
    gn_previewdrone_1.nodes["Curve Circle"].height = 100.0

    gn_previewdrone_1.nodes["Curve Circle.001"].width  = 140.0
    gn_previewdrone_1.nodes["Curve Circle.001"].height = 100.0

    gn_previewdrone_1.nodes["Set Material"].width  = 140.0
    gn_previewdrone_1.nodes["Set Material"].height = 100.0

    gn_previewdrone_1.nodes["Realize Instances"].width  = 140.0
    gn_previewdrone_1.nodes["Realize Instances"].height = 100.0

    gn_previewdrone_1.nodes["Collection Info"].width  = 140.0
    gn_previewdrone_1.nodes["Collection Info"].height = 100.0

    gn_previewdrone_1.nodes["Mesh to Points"].width  = 140.0
    gn_previewdrone_1.nodes["Mesh to Points"].height = 100.0

    gn_previewdrone_1.nodes["Sample Index.001"].width  = 140.0
    gn_previewdrone_1.nodes["Sample Index.001"].height = 100.0

    gn_previewdrone_1.nodes["Position.001"].width  = 140.0
    gn_previewdrone_1.nodes["Position.001"].height = 100.0

    gn_previewdrone_1.nodes["Realize Instances.001"].width  = 140.0
    gn_previewdrone_1.nodes["Realize Instances.001"].height = 100.0

    gn_previewdrone_1.nodes["Set Position.001"].width  = 140.0
    gn_previewdrone_1.nodes["Set Position.001"].height = 100.0

    gn_previewdrone_1.nodes["Named Attribute.002"].width  = 140.0
    gn_previewdrone_1.nodes["Named Attribute.002"].height = 100.0

    gn_previewdrone_1.nodes["Sample Index.002"].width  = 140.0
    gn_previewdrone_1.nodes["Sample Index.002"].height = 100.0

    gn_previewdrone_1.nodes["ID.001"].width  = 140.0
    gn_previewdrone_1.nodes["ID.001"].height = 100.0

    gn_previewdrone_1.nodes["Object Info.002"].width  = 140.0
    gn_previewdrone_1.nodes["Object Info.002"].height = 100.0

    gn_previewdrone_1.nodes["Sample Index.003"].width  = 140.0
    gn_previewdrone_1.nodes["Sample Index.003"].height = 100.0

    gn_previewdrone_1.nodes["Named Attribute.003"].width  = 140.0
    gn_previewdrone_1.nodes["Named Attribute.003"].height = 100.0

    gn_previewdrone_1.nodes["Store Named Attribute.002"].width  = 140.0
    gn_previewdrone_1.nodes["Store Named Attribute.002"].height = 100.0


    # Initialize gn_previewdrone_1 links

    # scale_elements.Geometry -> switch.False
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Scale Elements"].outputs[0],
        gn_previewdrone_1.nodes["Switch"].inputs[1]
    )
    # join_geometry.Geometry -> switch.True
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Join Geometry"].outputs[0],
        gn_previewdrone_1.nodes["Switch"].inputs[2]
    )
    # transform_geometry.Geometry -> join_geometry.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Transform Geometry"].outputs[0],
        gn_previewdrone_1.nodes["Join Geometry"].inputs[0]
    )
    # align_rotation_to_vector.Rotation -> transform_geometry.Rotation
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Align Rotation to Vector"].outputs[0],
        gn_previewdrone_1.nodes["Transform Geometry"].inputs[2]
    )
    # object_info.Rotation -> align_rotation_to_vector.Rotation
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Object Info"].outputs[2],
        gn_previewdrone_1.nodes["Align Rotation to Vector"].inputs[0]
    )
    # active_camera.Active Camera -> object_info.Object
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Active Camera"].outputs[0],
        gn_previewdrone_1.nodes["Object Info"].inputs[0]
    )
    # curve_to_mesh.Mesh -> transform_geometry.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Curve to Mesh"].outputs[0],
        gn_previewdrone_1.nodes["Transform Geometry"].inputs[0]
    )
    # curve_circle.Curve -> curve_to_mesh.Curve
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Curve Circle"].outputs[0],
        gn_previewdrone_1.nodes["Curve to Mesh"].inputs[0]
    )
    # curve_circle_001.Curve -> curve_to_mesh.Profile Curve
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Curve Circle.001"].outputs[0],
        gn_previewdrone_1.nodes["Curve to Mesh"].inputs[1]
    )
    # group_input.Material -> set_material.Material
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[1],
        gn_previewdrone_1.nodes["Set Material"].inputs[2]
    )
    # group_input.Scale -> scale_elements.Scale
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[3],
        gn_previewdrone_1.nodes["Scale Elements"].inputs[2]
    )
    # group_input.ShowRing -> switch.Switch
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[4],
        gn_previewdrone_1.nodes["Switch"].inputs[0]
    )
    # switch.Output -> instance_on_points.Instance
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Switch"].outputs[0],
        gn_previewdrone_1.nodes["Instance on Points"].inputs[2]
    )
    # group_input.Geometry -> scale_elements.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[0],
        gn_previewdrone_1.nodes["Scale Elements"].inputs[0]
    )
    # mesh_to_points.Points -> sample_index_001.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Mesh to Points"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.001"].inputs[0]
    )
    # position_001.Position -> sample_index_001.Value
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Position.001"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.001"].inputs[1]
    )
    # collection_info.Instances -> realize_instances_001.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Collection Info"].outputs[0],
        gn_previewdrone_1.nodes["Realize Instances.001"].inputs[0]
    )
    # realize_instances_001.Geometry -> mesh_to_points.Mesh
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Realize Instances.001"].outputs[0],
        gn_previewdrone_1.nodes["Mesh to Points"].inputs[0]
    )
    # sample_index_001.Value -> set_position_001.Position
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Sample Index.001"].outputs[0],
        gn_previewdrone_1.nodes["Set Position.001"].inputs[2]
    )
    # named_attribute_002.Attribute -> sample_index_002.Value
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Named Attribute.002"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.002"].inputs[1]
    )
    # id_001.ID -> sample_index_002.Index
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["ID.001"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.002"].inputs[2]
    )
    # sample_index_002.Value -> sample_index_001.Index
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Sample Index.002"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.001"].inputs[2]
    )
    # mesh_to_points.Points -> sample_index_002.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Mesh to Points"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.002"].inputs[0]
    )
    # object_info_002.Geometry -> sample_index_003.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Object Info.002"].outputs[4],
        gn_previewdrone_1.nodes["Sample Index.003"].inputs[0]
    )
    # named_attribute_003.Attribute -> sample_index_003.Value
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Named Attribute.003"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.003"].inputs[1]
    )
    # store_named_attribute_002.Geometry -> instance_on_points.Points
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Store Named Attribute.002"].outputs[0],
        gn_previewdrone_1.nodes["Instance on Points"].inputs[0]
    )
    # mesh_to_points.Points -> set_position_001.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Mesh to Points"].outputs[0],
        gn_previewdrone_1.nodes["Set Position.001"].inputs[0]
    )
    # sample_index_002.Value -> sample_index_003.Index
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Sample Index.002"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.003"].inputs[2]
    )
    # set_position_001.Geometry -> store_named_attribute_002.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Set Position.001"].outputs[0],
        gn_previewdrone_1.nodes["Store Named Attribute.002"].inputs[0]
    )
    # sample_index_003.Value -> store_named_attribute_002.Value
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Sample Index.003"].outputs[0],
        gn_previewdrone_1.nodes["Store Named Attribute.002"].inputs[3]
    )
    # instance_on_points.Instances -> set_material.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Instance on Points"].outputs[0],
        gn_previewdrone_1.nodes["Set Material"].inputs[0]
    )
    # set_material.Geometry -> realize_instances.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Set Material"].outputs[0],
        gn_previewdrone_1.nodes["Realize Instances"].inputs[0]
    )
    # realize_instances.Geometry -> group_output.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Realize Instances"].outputs[0],
        gn_previewdrone_1.nodes["Group Output"].inputs[0]
    )
    # group_input.Collection -> collection_info.Collection
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[5],
        gn_previewdrone_1.nodes["Collection Info"].inputs[0]
    )
    # group_input.ColorVerts -> object_info_002.Object
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[2],
        gn_previewdrone_1.nodes["Object Info.002"].inputs[0]
    )
    # scale_elements.Geometry -> join_geometry.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Scale Elements"].outputs[0],
        gn_previewdrone_1.nodes["Join Geometry"].inputs[0]
    )

    return gn_previewdrone_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    gn_previewdrone = geometry_nodes_002_1_node_group(node_tree_names)
    node_tree_names[geometry_nodes_002_1_node_group] = gn_previewdrone.name

