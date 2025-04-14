import trimesh
from trimesh.creation import icosphere

sphere = icosphere(subdivisions=6, radius=1.0)

print(f"Number of vertices: {len(sphere.vertices)}")
print(f"Number of faces: {len(sphere.faces)}")

sphere.export('sphere.glb')
