import bpy
import mathutils
import os
import typing


def geometry_nodes_002_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize Geometry Nodes.002 node group"""
    geometry_nodes_002_1 = bpy.data.node_groups.new(type='GeometryNodeTree', name="Geometry Nodes.002")

    geometry_nodes_002_1.color_tag = 'NONE'
    geometry_nodes_002_1.description = ""
    geometry_nodes_002_1.default_group_node_width = 140
    geometry_nodes_002_1.is_modifier = True

    # geometry_nodes_002_1 interface

    # Socket Geometry
    geometry_socket = geometry_nodes_002_1.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    # Socket Geometry
    geometry_socket_1 = geometry_nodes_002_1.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'

    # Socket Material
    material_socket = geometry_nodes_002_1.interface.new_socket(name="Material", in_out='INPUT', socket_type='NodeSocketMaterial')
    material_socket.attribute_domain = 'POINT'

    # Socket Object
    object_socket = geometry_nodes_002_1.interface.new_socket(name="Object", in_out='INPUT', socket_type='NodeSocketObject')
    object_socket.attribute_domain = 'POINT'

    # Socket Scale
    scale_socket = geometry_nodes_002_1.interface.new_socket(name="Scale", in_out='INPUT', socket_type='NodeSocketFloat')
    scale_socket.default_value = 0.4000000059604645
    scale_socket.min_value = 0.0
    scale_socket.max_value = 3.4028234663852886e+38
    scale_socket.subtype = 'NONE'
    scale_socket.attribute_domain = 'POINT'

    # Socket ShowRing
    showring_socket = geometry_nodes_002_1.interface.new_socket(name="ShowRing", in_out='INPUT', socket_type='NodeSocketBool')
    showring_socket.default_value = False
    showring_socket.attribute_domain = 'POINT'

    # Initialize geometry_nodes_002_1 nodes

    # Node Group Input
    group_input = geometry_nodes_002_1.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Group Output
    group_output = geometry_nodes_002_1.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Instance on Points
    instance_on_points = geometry_nodes_002_1.nodes.new("GeometryNodeInstanceOnPoints")
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
    switch = geometry_nodes_002_1.nodes.new("GeometryNodeSwitch")
    switch.name = "Switch"
    switch.input_type = 'GEOMETRY'

    # Node Scale Elements
    scale_elements = geometry_nodes_002_1.nodes.new("GeometryNodeScaleElements")
    scale_elements.name = "Scale Elements"
    scale_elements.domain = 'FACE'
    scale_elements.scale_mode = 'UNIFORM'
    # Selection
    scale_elements.inputs[1].default_value = True
    # Center
    scale_elements.inputs[3].default_value = (0.0, 0.0, 0.0)

    # Node Join Geometry
    join_geometry = geometry_nodes_002_1.nodes.new("GeometryNodeJoinGeometry")
    join_geometry.name = "Join Geometry"

    # Node Transform Geometry
    transform_geometry = geometry_nodes_002_1.nodes.new("GeometryNodeTransform")
    transform_geometry.name = "Transform Geometry"
    transform_geometry.mode = 'COMPONENTS'
    # Translation
    transform_geometry.inputs[1].default_value = (0.0, 0.0, 0.0)
    # Scale
    transform_geometry.inputs[3].default_value = (1.0, 1.0, 1.0)

    # Node Align Rotation to Vector
    align_rotation_to_vector = geometry_nodes_002_1.nodes.new("FunctionNodeAlignRotationToVector")
    align_rotation_to_vector.name = "Align Rotation to Vector"
    align_rotation_to_vector.axis = 'Y'
    align_rotation_to_vector.pivot_axis = 'Y'
    # Factor
    align_rotation_to_vector.inputs[1].default_value = 1.0
    # Vector
    align_rotation_to_vector.inputs[2].default_value = (1.0, 0.0, 0.0)

    # Node Object Info
    object_info = geometry_nodes_002_1.nodes.new("GeometryNodeObjectInfo")
    object_info.name = "Object Info"
    object_info.transform_space = 'ORIGINAL'
    # As Instance
    object_info.inputs[1].default_value = False

    # Node Active Camera
    active_camera = geometry_nodes_002_1.nodes.new("GeometryNodeInputActiveCamera")
    active_camera.name = "Active Camera"

    # Node Curve to Mesh
    curve_to_mesh = geometry_nodes_002_1.nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.name = "Curve to Mesh"
    # Fill Caps
    curve_to_mesh.inputs[2].default_value = False

    # Node Curve Circle
    curve_circle = geometry_nodes_002_1.nodes.new("GeometryNodeCurvePrimitiveCircle")
    curve_circle.name = "Curve Circle"
    curve_circle.mode = 'RADIUS'
    # Resolution
    curve_circle.inputs[0].default_value = 24
    # Radius
    curve_circle.inputs[4].default_value = 0.7799999713897705

    # Node Curve Circle.001
    curve_circle_001 = geometry_nodes_002_1.nodes.new("GeometryNodeCurvePrimitiveCircle")
    curve_circle_001.name = "Curve Circle.001"
    curve_circle_001.mode = 'RADIUS'
    # Resolution
    curve_circle_001.inputs[0].default_value = 3
    # Radius
    curve_circle_001.inputs[4].default_value = 0.004999999888241291

    # Node Set Material
    set_material = geometry_nodes_002_1.nodes.new("GeometryNodeSetMaterial")
    set_material.name = "Set Material"
    # Selection
    set_material.inputs[1].default_value = True

    # Node Object Info.001
    object_info_001 = geometry_nodes_002_1.nodes.new("GeometryNodeObjectInfo")
    object_info_001.name = "Object Info.001"
    object_info_001.transform_space = 'ORIGINAL'
    # As Instance
    object_info_001.inputs[1].default_value = False

    # Node Store Named Attribute
    store_named_attribute = geometry_nodes_002_1.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute.name = "Store Named Attribute"
    store_named_attribute.data_type = 'FLOAT_COLOR'
    store_named_attribute.domain = 'POINT'
    # Selection
    store_named_attribute.inputs[1].default_value = True
    # Name
    store_named_attribute.inputs[2].default_value = "color"

    # Node Named Attribute
    named_attribute = geometry_nodes_002_1.nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute.name = "Named Attribute"
    named_attribute.data_type = 'FLOAT_COLOR'
    # Name
    named_attribute.inputs[0].default_value = "color"

    # Node Sample Index
    sample_index = geometry_nodes_002_1.nodes.new("GeometryNodeSampleIndex")
    sample_index.name = "Sample Index"
    sample_index.clamp = False
    sample_index.data_type = 'FLOAT_COLOR'
    sample_index.domain = 'POINT'

    # Node ID
    id = geometry_nodes_002_1.nodes.new("GeometryNodeInputID")
    id.name = "ID"

    # Set locations
    geometry_nodes_002_1.nodes["Group Input"].location = (-1432.6986083984375, -195.94091796875)
    geometry_nodes_002_1.nodes["Group Output"].location = (1266.35693359375, -402.2463684082031)
    geometry_nodes_002_1.nodes["Instance on Points"].location = (541.8675537109375, -252.1837158203125)
    geometry_nodes_002_1.nodes["Switch"].location = (357.25885009765625, -435.17657470703125)
    geometry_nodes_002_1.nodes["Scale Elements"].location = (-55.24286651611328, -446.0585632324219)
    geometry_nodes_002_1.nodes["Join Geometry"].location = (163.46734619140625, -605.8854370117188)
    geometry_nodes_002_1.nodes["Transform Geometry"].location = (-428.240234375, -595.8190307617188)
    geometry_nodes_002_1.nodes["Align Rotation to Vector"].location = (-820.0733642578125, -625.8809204101562)
    geometry_nodes_002_1.nodes["Object Info"].location = (-1013.34375, -600.9940795898438)
    geometry_nodes_002_1.nodes["Active Camera"].location = (-1259.0733642578125, -717.1326904296875)
    geometry_nodes_002_1.nodes["Curve to Mesh"].location = (-813.9481201171875, -431.56982421875)
    geometry_nodes_002_1.nodes["Curve Circle"].location = (-1043.841064453125, -290.50164794921875)
    geometry_nodes_002_1.nodes["Curve Circle.001"].location = (-1001.628662109375, -434.71600341796875)
    geometry_nodes_002_1.nodes["Set Material"].location = (974.3298950195312, -317.53582763671875)
    geometry_nodes_002_1.nodes["Object Info.001"].location = (-486.33837890625, -57.20703125)
    geometry_nodes_002_1.nodes["Store Named Attribute"].location = (720.8192749023438, -34.24755859375)
    geometry_nodes_002_1.nodes["Named Attribute"].location = (-170.59185791015625, -57.06007385253906)
    geometry_nodes_002_1.nodes["Sample Index"].location = (200.31686401367188, 18.6944580078125)
    geometry_nodes_002_1.nodes["ID"].location = (-173.86659240722656, -207.24859619140625)

    # Set dimensions
    geometry_nodes_002_1.nodes["Group Input"].width  = 140.0
    geometry_nodes_002_1.nodes["Group Input"].height = 100.0

    geometry_nodes_002_1.nodes["Group Output"].width  = 140.0
    geometry_nodes_002_1.nodes["Group Output"].height = 100.0

    geometry_nodes_002_1.nodes["Instance on Points"].width  = 140.0
    geometry_nodes_002_1.nodes["Instance on Points"].height = 100.0

    geometry_nodes_002_1.nodes["Switch"].width  = 140.0
    geometry_nodes_002_1.nodes["Switch"].height = 100.0

    geometry_nodes_002_1.nodes["Scale Elements"].width  = 140.0
    geometry_nodes_002_1.nodes["Scale Elements"].height = 100.0

    geometry_nodes_002_1.nodes["Join Geometry"].width  = 140.0
    geometry_nodes_002_1.nodes["Join Geometry"].height = 100.0

    geometry_nodes_002_1.nodes["Transform Geometry"].width  = 140.0
    geometry_nodes_002_1.nodes["Transform Geometry"].height = 100.0

    geometry_nodes_002_1.nodes["Align Rotation to Vector"].width  = 140.0
    geometry_nodes_002_1.nodes["Align Rotation to Vector"].height = 100.0

    geometry_nodes_002_1.nodes["Object Info"].width  = 140.0
    geometry_nodes_002_1.nodes["Object Info"].height = 100.0

    geometry_nodes_002_1.nodes["Active Camera"].width  = 140.0
    geometry_nodes_002_1.nodes["Active Camera"].height = 100.0

    geometry_nodes_002_1.nodes["Curve to Mesh"].width  = 140.0
    geometry_nodes_002_1.nodes["Curve to Mesh"].height = 100.0

    geometry_nodes_002_1.nodes["Curve Circle"].width  = 179.333740234375
    geometry_nodes_002_1.nodes["Curve Circle"].height = 100.0

    geometry_nodes_002_1.nodes["Curve Circle.001"].width  = 140.0
    geometry_nodes_002_1.nodes["Curve Circle.001"].height = 100.0

    geometry_nodes_002_1.nodes["Set Material"].width  = 140.0
    geometry_nodes_002_1.nodes["Set Material"].height = 100.0

    geometry_nodes_002_1.nodes["Object Info.001"].width  = 140.0
    geometry_nodes_002_1.nodes["Object Info.001"].height = 100.0

    geometry_nodes_002_1.nodes["Store Named Attribute"].width  = 140.0
    geometry_nodes_002_1.nodes["Store Named Attribute"].height = 100.0

    geometry_nodes_002_1.nodes["Named Attribute"].width  = 140.0
    geometry_nodes_002_1.nodes["Named Attribute"].height = 100.0

    geometry_nodes_002_1.nodes["Sample Index"].width  = 140.0
    geometry_nodes_002_1.nodes["Sample Index"].height = 100.0

    geometry_nodes_002_1.nodes["ID"].width  = 140.0
    geometry_nodes_002_1.nodes["ID"].height = 100.0


    # Initialize geometry_nodes_002_1 links

    # scale_elements.Geometry -> switch.False
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Scale Elements"].outputs[0],
        geometry_nodes_002_1.nodes["Switch"].inputs[1]
    )
    # join_geometry.Geometry -> switch.True
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Join Geometry"].outputs[0],
        geometry_nodes_002_1.nodes["Switch"].inputs[2]
    )
    # transform_geometry.Geometry -> join_geometry.Geometry
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Transform Geometry"].outputs[0],
        geometry_nodes_002_1.nodes["Join Geometry"].inputs[0]
    )
    # align_rotation_to_vector.Rotation -> transform_geometry.Rotation
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Align Rotation to Vector"].outputs[0],
        geometry_nodes_002_1.nodes["Transform Geometry"].inputs[2]
    )
    # object_info.Rotation -> align_rotation_to_vector.Rotation
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Object Info"].outputs[2],
        geometry_nodes_002_1.nodes["Align Rotation to Vector"].inputs[0]
    )
    # active_camera.Active Camera -> object_info.Object
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Active Camera"].outputs[0],
        geometry_nodes_002_1.nodes["Object Info"].inputs[0]
    )
    # curve_to_mesh.Mesh -> transform_geometry.Geometry
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Curve to Mesh"].outputs[0],
        geometry_nodes_002_1.nodes["Transform Geometry"].inputs[0]
    )
    # curve_circle.Curve -> curve_to_mesh.Curve
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Curve Circle"].outputs[0],
        geometry_nodes_002_1.nodes["Curve to Mesh"].inputs[0]
    )
    # curve_circle_001.Curve -> curve_to_mesh.Profile Curve
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Curve Circle.001"].outputs[0],
        geometry_nodes_002_1.nodes["Curve to Mesh"].inputs[1]
    )
    # group_input.Material -> set_material.Material
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Group Input"].outputs[1],
        geometry_nodes_002_1.nodes["Set Material"].inputs[2]
    )
    # group_input.Object -> object_info_001.Object
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Group Input"].outputs[2],
        geometry_nodes_002_1.nodes["Object Info.001"].inputs[0]
    )
    # group_input.Scale -> scale_elements.Scale
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Group Input"].outputs[3],
        geometry_nodes_002_1.nodes["Scale Elements"].inputs[2]
    )
    # group_input.ShowRing -> switch.Switch
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Group Input"].outputs[4],
        geometry_nodes_002_1.nodes["Switch"].inputs[0]
    )
    # instance_on_points.Instances -> store_named_attribute.Geometry
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Instance on Points"].outputs[0],
        geometry_nodes_002_1.nodes["Store Named Attribute"].inputs[0]
    )
    # switch.Output -> instance_on_points.Instance
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Switch"].outputs[0],
        geometry_nodes_002_1.nodes["Instance on Points"].inputs[2]
    )
    # group_input.Geometry -> scale_elements.Geometry
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Group Input"].outputs[0],
        geometry_nodes_002_1.nodes["Scale Elements"].inputs[0]
    )
    # store_named_attribute.Geometry -> set_material.Geometry
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Store Named Attribute"].outputs[0],
        geometry_nodes_002_1.nodes["Set Material"].inputs[0]
    )
    # object_info_001.Geometry -> sample_index.Geometry
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Object Info.001"].outputs[4],
        geometry_nodes_002_1.nodes["Sample Index"].inputs[0]
    )
    # id.ID -> sample_index.Index
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["ID"].outputs[0],
        geometry_nodes_002_1.nodes["Sample Index"].inputs[2]
    )
    # named_attribute.Attribute -> sample_index.Value
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Named Attribute"].outputs[0],
        geometry_nodes_002_1.nodes["Sample Index"].inputs[1]
    )
    # sample_index.Value -> store_named_attribute.Value
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Sample Index"].outputs[0],
        geometry_nodes_002_1.nodes["Store Named Attribute"].inputs[3]
    )
    # object_info_001.Geometry -> instance_on_points.Points
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Object Info.001"].outputs[4],
        geometry_nodes_002_1.nodes["Instance on Points"].inputs[0]
    )
    # set_material.Geometry -> group_output.Geometry
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Set Material"].outputs[0],
        geometry_nodes_002_1.nodes["Group Output"].inputs[0]
    )
    # scale_elements.Geometry -> join_geometry.Geometry
    geometry_nodes_002_1.links.new(
        geometry_nodes_002_1.nodes["Scale Elements"].outputs[0],
        geometry_nodes_002_1.nodes["Join Geometry"].inputs[0]
    )

    return geometry_nodes_002_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    geometry_nodes_002 = geometry_nodes_002_1_node_group(node_tree_names)
    node_tree_names[geometry_nodes_002_1_node_group] = geometry_nodes_002.name

