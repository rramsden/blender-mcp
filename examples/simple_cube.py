import bpy

# Add a single cube
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))

# Get the newly created cube
cube = bpy.data.objects[-1]

# Make sure it's a mesh and assign a material
if cube.type == 'MESH':
    cube.name = "My_Cube"
    
    # Create and assign a material
    mat = bpy.data.materials.new(name="Red_Material")
    mat.diffuse_color = (1.0, 0.0, 0.0, 1.0)  # Red color
    cube.data.materials.append(mat)

print("Created a red cube")
