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

    # Socket CircleMat
    circlemat_socket = gn_previewdrone_1.interface.new_socket(name="CircleMat", in_out='INPUT', socket_type='NodeSocketMaterial')
    circlemat_socket.attribute_domain = 'POINT'

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
    collection_info.transform_space = 'RELATIVE'
    # Separate Children
    collection_info.inputs[1].default_value = False
    # Reset Children
    collection_info.inputs[2].default_value = False

    # Node Sample Index.001
    sample_index_001 = gn_previewdrone_1.nodes.new("GeometryNodeSampleIndex")
    sample_index_001.name = "Sample Index.001"
    sample_index_001.clamp = False
    sample_index_001.data_type = 'FLOAT_VECTOR'
    sample_index_001.domain = 'POINT'

    # Node Position.001
    position_001 = gn_previewdrone_1.nodes.new("GeometryNodeInputPosition")
    position_001.name = "Position.001"

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

    # Node Transform Geometry.001
    transform_geometry_001 = gn_previewdrone_1.nodes.new("GeometryNodeTransform")
    transform_geometry_001.name = "Transform Geometry.001"
    transform_geometry_001.mode = 'COMPONENTS'
    # Translation
    transform_geometry_001.inputs[1].default_value = (0.0, 0.0, -0.09999999403953552)
    # Rotation
    transform_geometry_001.inputs[2].default_value = (0.0, 0.0, 0.0)
    # Scale
    transform_geometry_001.inputs[3].default_value = (1.5, 1.5, 1.5)

    # Node Set Material.001
    set_material_001 = gn_previewdrone_1.nodes.new("GeometryNodeSetMaterial")
    set_material_001.name = "Set Material.001"
    # Selection
    set_material_001.inputs[1].default_value = True

    # Node Realize Instances.001
    realize_instances_001 = gn_previewdrone_1.nodes.new("GeometryNodeRealizeInstances")
    realize_instances_001.name = "Realize Instances.001"
    # Selection
    realize_instances_001.inputs[1].default_value = True
    # Realize All
    realize_instances_001.inputs[2].default_value = True
    # Depth
    realize_instances_001.inputs[3].default_value = 0

    # Node Mesh to Points
    mesh_to_points = gn_previewdrone_1.nodes.new("GeometryNodeMeshToPoints")
    mesh_to_points.name = "Mesh to Points"
    mesh_to_points.mode = 'VERTICES'
    # Selection
    mesh_to_points.inputs[1].default_value = True
    # Position
    mesh_to_points.inputs[2].default_value = (0.0, 0.0, 0.0)
    # Radius
    mesh_to_points.inputs[3].default_value = 0.05000000074505806

    # Set locations
    gn_previewdrone_1.nodes["Group Input"].location = (-1126.33203125, -240.55227661132812)
    gn_previewdrone_1.nodes["Group Output"].location = (792.6171875, -150.07821655273438)
    gn_previewdrone_1.nodes["Instance on Points"].location = (449.28497314453125, -181.92042541503906)
    gn_previewdrone_1.nodes["Switch"].location = (55.83498001098633, -462.8209228515625)
    gn_previewdrone_1.nodes["Scale Elements"].location = (-517.0735473632812, -429.4473876953125)
    gn_previewdrone_1.nodes["Join Geometry"].location = (-122.07010650634766, -584.0868530273438)
    gn_previewdrone_1.nodes["Transform Geometry"].location = (262.3005676269531, -421.5835876464844)
    gn_previewdrone_1.nodes["Align Rotation to Vector"].location = (58.21506118774414, -645.13818359375)
    gn_previewdrone_1.nodes["Object Info"].location = (-119.12115478515625, -685.4043579101562)
    gn_previewdrone_1.nodes["Active Camera"].location = (-290.80133056640625, -807.9295654296875)
    gn_previewdrone_1.nodes["Set Material"].location = (-289.2684631347656, -450.8121337890625)
    gn_previewdrone_1.nodes["Realize Instances"].location = (613.0159912109375, -159.64720153808594)
    gn_previewdrone_1.nodes["Collection Info"].location = (-879.483154296875, -41.66184997558594)
    gn_previewdrone_1.nodes["Sample Index.001"].location = (-140.5871124267578, 107.73624420166016)
    gn_previewdrone_1.nodes["Position.001"].location = (-326.22943115234375, -53.466949462890625)
    gn_previewdrone_1.nodes["Set Position.001"].location = (266.11163330078125, -192.95562744140625)
    gn_previewdrone_1.nodes["Named Attribute.002"].location = (-527.2001953125, -212.91635131835938)
    gn_previewdrone_1.nodes["Sample Index.002"].location = (-311.8916015625, -108.08781433105469)
    gn_previewdrone_1.nodes["ID.001"].location = (-526.3309326171875, -355.38836669921875)
    gn_previewdrone_1.nodes["Object Info.002"].location = (-141.48519897460938, 327.1990051269531)
    gn_previewdrone_1.nodes["Transform Geometry.001"].location = (-500.722900390625, -639.0758056640625)
    gn_previewdrone_1.nodes["Set Material.001"].location = (-297.6289367675781, -613.995361328125)
    gn_previewdrone_1.nodes["Realize Instances.001"].location = (-694.5936279296875, -15.515670776367188)
    gn_previewdrone_1.nodes["Mesh to Points"].location = (-510.11358642578125, 21.371109008789062)

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

    gn_previewdrone_1.nodes["Set Material"].width  = 140.0
    gn_previewdrone_1.nodes["Set Material"].height = 100.0

    gn_previewdrone_1.nodes["Realize Instances"].width  = 140.0
    gn_previewdrone_1.nodes["Realize Instances"].height = 100.0

    gn_previewdrone_1.nodes["Collection Info"].width  = 140.0
    gn_previewdrone_1.nodes["Collection Info"].height = 100.0

    gn_previewdrone_1.nodes["Sample Index.001"].width  = 140.0
    gn_previewdrone_1.nodes["Sample Index.001"].height = 100.0

    gn_previewdrone_1.nodes["Position.001"].width  = 140.0
    gn_previewdrone_1.nodes["Position.001"].height = 100.0

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

    gn_previewdrone_1.nodes["Transform Geometry.001"].width  = 140.0
    gn_previewdrone_1.nodes["Transform Geometry.001"].height = 100.0

    gn_previewdrone_1.nodes["Set Material.001"].width  = 140.0
    gn_previewdrone_1.nodes["Set Material.001"].height = 100.0

    gn_previewdrone_1.nodes["Realize Instances.001"].width  = 140.0
    gn_previewdrone_1.nodes["Realize Instances.001"].height = 100.0

    gn_previewdrone_1.nodes["Mesh to Points"].width  = 140.0
    gn_previewdrone_1.nodes["Mesh to Points"].height = 100.0


    # Initialize gn_previewdrone_1 links

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
    # group_input.Geometry -> scale_elements.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[0],
        gn_previewdrone_1.nodes["Scale Elements"].inputs[0]
    )
    # position_001.Position -> sample_index_001.Value
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Position.001"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.001"].inputs[1]
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
    # switch.Output -> transform_geometry.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Switch"].outputs[0],
        gn_previewdrone_1.nodes["Transform Geometry"].inputs[0]
    )
    # join_geometry.Geometry -> switch.True
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Join Geometry"].outputs[0],
        gn_previewdrone_1.nodes["Switch"].inputs[2]
    )
    # transform_geometry.Geometry -> instance_on_points.Instance
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Transform Geometry"].outputs[0],
        gn_previewdrone_1.nodes["Instance on Points"].inputs[2]
    )
    # instance_on_points.Instances -> realize_instances.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Instance on Points"].outputs[0],
        gn_previewdrone_1.nodes["Realize Instances"].inputs[0]
    )
    # scale_elements.Geometry -> set_material.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Scale Elements"].outputs[0],
        gn_previewdrone_1.nodes["Set Material"].inputs[0]
    )
    # set_material.Geometry -> switch.False
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Set Material"].outputs[0],
        gn_previewdrone_1.nodes["Switch"].inputs[1]
    )
    # group_input.Geometry -> transform_geometry_001.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[0],
        gn_previewdrone_1.nodes["Transform Geometry.001"].inputs[0]
    )
    # set_material_001.Geometry -> join_geometry.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Set Material.001"].outputs[0],
        gn_previewdrone_1.nodes["Join Geometry"].inputs[0]
    )
    # transform_geometry_001.Geometry -> set_material_001.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Transform Geometry.001"].outputs[0],
        gn_previewdrone_1.nodes["Set Material.001"].inputs[0]
    )
    # group_input.CircleMat -> set_material_001.Material
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Group Input"].outputs[6],
        gn_previewdrone_1.nodes["Set Material.001"].inputs[2]
    )
    # sample_index_001.Value -> set_position_001.Position
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Sample Index.001"].outputs[0],
        gn_previewdrone_1.nodes["Set Position.001"].inputs[2]
    )
    # collection_info.Instances -> realize_instances_001.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Collection Info"].outputs[0],
        gn_previewdrone_1.nodes["Realize Instances.001"].inputs[0]
    )
    # set_position_001.Geometry -> instance_on_points.Points
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Set Position.001"].outputs[0],
        gn_previewdrone_1.nodes["Instance on Points"].inputs[0]
    )
    # realize_instances_001.Geometry -> mesh_to_points.Mesh
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Realize Instances.001"].outputs[0],
        gn_previewdrone_1.nodes["Mesh to Points"].inputs[0]
    )
    # realize_instances.Geometry -> group_output.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Realize Instances"].outputs[0],
        gn_previewdrone_1.nodes["Group Output"].inputs[0]
    )
    # mesh_to_points.Points -> sample_index_001.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Mesh to Points"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.001"].inputs[0]
    )
    # object_info_002.Geometry -> set_position_001.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Object Info.002"].outputs[4],
        gn_previewdrone_1.nodes["Set Position.001"].inputs[0]
    )
    # mesh_to_points.Points -> sample_index_002.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Mesh to Points"].outputs[0],
        gn_previewdrone_1.nodes["Sample Index.002"].inputs[0]
    )
    # set_material.Geometry -> join_geometry.Geometry
    gn_previewdrone_1.links.new(
        gn_previewdrone_1.nodes["Set Material"].outputs[0],
        gn_previewdrone_1.nodes["Join Geometry"].inputs[0]
    )

    return gn_previewdrone_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    gn_previewdrone = gn_previewdrone_1_node_group(node_tree_names)
    node_tree_names[gn_previewdrone_1_node_group] = gn_previewdrone.name

