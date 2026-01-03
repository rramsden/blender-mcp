import bpy

# Add a single cube at origin
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))

# Print info about what was created
print("Objects in scene:")
for obj in bpy.data.objects:
    print(f"  {obj.name}: {obj.type}")

print("Basic cube test completed.")
