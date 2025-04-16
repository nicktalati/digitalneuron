import trimesh
from trimesh.creation import icosphere

sphere = icosphere(subdivisions=5, radius=1.0)

print(f"Number of vertices: {len(sphere.vertices)}")
print(f"Number of faces: {len(sphere.faces)}")

sphere.export('source_assets/sphere.glb')
