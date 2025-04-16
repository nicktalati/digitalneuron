import trimesh
import numpy as np
from neuron import Neuron, Node
import sys


def create_segment_frustum(node1: Node, node2: Node, sections=16) -> trimesh.Trimesh:
    p1 = np.array([node1.x, node1.y, node1.z])
    p2 = np.array([node2.x, node2.y, node2.z])
    r1, r2 = node1.r, node2.r
    vector = p2 - p1
    length = np.linalg.norm(vector)

    if length < 1e-6:
        print("problem")
        return trimesh.creation.icosphere(subdivisions=2, radius=(r1 + r2)/2)

    vector_norm = vector / length

    vertices = []

    angles = np.linspace(0, 2 * np.pi, sections, endpoint=False)

    if np.abs(vector_norm[0]) > 0.99 or np.abs(vector_norm[1]) > 0.99:
        perp1 = np.cross(vector_norm, [0, 0, 1])
    else:
        perp1 = np.cross(vector_norm, [1, 0, 0])
    perp1 /= np.linalg.norm(perp1)
    perp2 = np.cross(vector_norm, perp1)

    vertices.append(p1)
    for angle in angles:
        vertices.append(p1 + r1 * (np.cos(angle) * perp1 + np.sin(angle) * perp2))

    vertices.append(p2)
    for angle in angles:
        vertices.append(p2 + r2 * (np.cos(angle) * perp1 + np.sin(angle) * perp2))

    vertices_np = np.array(vertices)
    faces = []
    cap1_center_idx = 0
    cap1_start_idx = 1
    cap2_center_idx = 1 + sections
    cap2_start_idx = 1 + sections + 1

    for i in range(sections):
        v1 = cap1_start_idx + i
        v2 = cap1_start_idx + (i + 1) % sections
        v3 = cap2_start_idx + (i + 1) % sections
        v4 = cap2_start_idx + i
        faces.append([v1, v2, v4])
        faces.append([v2, v3, v4])
        faces.append([cap1_center_idx, v2, v1])
        faces.append([cap2_center_idx, v4, v3])

    faces_np = np.array(faces)

    frustum_mesh = trimesh.Trimesh(vertices=vertices_np, faces=faces_np)
    frustum_mesh.process(validate=True)
    return frustum_mesh
    
def generate_mesh_sequential_boolean(neuron: Neuron) -> trimesh.Trimesh:
    current_neuron_mesh = trimesh.primitives.Sphere(
        radius=neuron.root_node.r,
        center=(neuron.root_node.x, neuron.root_node.y, neuron.root_node.z)
    )
    print(current_neuron_mesh.is_volume)
    processed_nodes = {neuron.root_node.id}

    i = 1

    def process_node_recursive(parent_node):
        nonlocal current_neuron_mesh
        nonlocal i
        print(f"processing node {i}/{len(neuron.nodes)}")
        i += 1
        children = neuron.get_children(parent_node)
        for child_node in children:
            if child_node.id in processed_nodes:
                continue
            processed_nodes.add(child_node.id)
            child_sphere = trimesh.primitives.Sphere(
                radius=child_node.r,
                center=(child_node.x, child_node.y, child_node.z)
            )
            segment_frustum = create_segment_frustum(parent_node, child_node)
            current_neuron_mesh = trimesh.util.concatenate(current_neuron_mesh, segment_frustum)
            current_neuron_mesh = trimesh.util.concatenate(current_neuron_mesh, child_sphere)
            process_node_recursive(child_node)


    process_node_recursive(neuron.root_node)
    return current_neuron_mesh

if __name__ == "__main__":
    neuron = Neuron("H16-06-013-05-03-04_597701859_m_DendriteAxon.CNG.swc")
    mesh = generate_mesh_sequential_boolean(neuron)
    mesh.export("neuron_mesh.glb")

