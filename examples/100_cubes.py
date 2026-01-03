# Clear existing objects
import bpy

# Select and delete all objects
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Create a grid of 100 cubes (10x10)
grid_size = 10
spacing = 2.0
total_cubes = grid_size * grid_size

for i in range(grid_size):
    for j in range(grid_size):
        # Calculate position
        x = (i - grid_size / 2) * spacing
        y = (j - grid_size / 2) * spacing
        z = 0

        # Add cube at position
        bpy.ops.mesh.primitive_cube_add(location=(x, y, z))

        # Get the newly created cube
        cube = bpy.context.active_object
        cube.name = f"Cube_{i}_{j}"

        # Only assign materials to mesh objects (not lights, cameras, etc.)
        if hasattr(cube.data, "materials"):
            # Create and assign a material with a unique color
            mat = bpy.data.materials.new(name=f"Cube_Material_{i}_{j}")
            # Set a unique color based on position
            hue = (i + j) / (grid_size * 2)
            mat.diffuse_color = (hue, 1.0 - hue, 1.0 - hue, 1.0)
            cube.data.materials.append(mat)

print(f"Created {total_cubes} cubes in a grid pattern")
