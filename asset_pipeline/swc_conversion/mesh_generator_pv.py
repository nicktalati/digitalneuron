import numpy as np
import pyvista as pv
import trimesh
# Import *your* Neuron and Node classes
from neuron import Neuron, Node # Make sure neuron.py is importable
import os
import traceback

# --- Configuration ---
DEFAULT_VOXEL_SIZE_FACTOR = 1.5 # Voxel size relative to min radius (adjust!)
MIN_VOXEL_SIZE = 0.1 # Prevent excessively small voxels
MAX_VOXEL_SIZE = 5.0 # Prevent excessively large voxels
DEFAULT_SECTIONS = 8 # Sections for tubes/spheres primitives
SMOOTHING_ITERATIONS = 10 # Iterations for final mesh smoothing
SMOOTHING_RELAXATION = 0.1 # Relaxation factor for smoothing

# --- Helper Function using your Neuron/Node classes ---
def create_pyvista_primitives(neuron: Neuron) -> pv.PolyData | None:
    """
    Creates simple PyVista primitives (spheres, tubes) representing the neuron
    using the provided Neuron object. Serves as input for voxelization.
    """
    print("  Creating PyVista primitives from Neuron object...")
    primitives = []
    processed_nodes = set() # Keep track using node IDs

    # 1. Soma Sphere
    root = neuron.root_node
    if not root:
        print("  -> ERROR: Neuron object has no root node.")
        return None
    soma_sphere = pv.Sphere(center=(root.x, root.y, root.z), radius=root.r)
    primitives.append(soma_sphere)
    processed_nodes.add(root.id)
    print(f"  Added soma sphere for root node {root.id}")

    # 2. Recursive function to traverse and create segments/nodes
    def process_node_recursive(parent_node: Node):
        children = neuron.get_children(parent_node)
        # print(f"    Processing children of {parent_node.id}: {[c.id for c in children]}") # Debug

        for child_node in children:
            # Basic cycle check / already processed check
            # Note: processed_nodes ideally prevents infinite loops from bad SWC,
            # but the add() below handles standard traversal.
            if child_node.id in processed_nodes:
                # print(f"    Skipping already processed node {child_node.id}")
                continue

            # --- Create Tube for the Segment ---
            p1 = np.array([parent_node.x, parent_node.y, parent_node.z])
            p2 = np.array([child_node.x, child_node.y, child_node.z])
            r1, r2 = parent_node.r, child_node.r
            avg_radius = (r1 + r2) / 2.0

            # Skip zero-radius segments
            if avg_radius < 1e-6:
                 print(f"    -> Warning: Skipping zero-radius segment {parent_node.id}->{child_node.id}")
                 processed_nodes.add(child_node.id) # Mark as processed to avoid issues
                 continue

            # Create tube using PyVista Line + tube filter
            try:
                # Ensure points are distinct enough for line creation
                if np.linalg.norm(p2 - p1) > 1e-6:
                     line = pv.Line(p1, p2)
                     tube = line.tube(radius=avg_radius, n_sides=DEFAULT_SECTIONS, capping=True)
                     if tube.n_points > 0:
                         primitives.append(tube)
                    # else:
                    #     print(f"    -> Warning: Tube generation resulted in empty mesh for {parent_node.id}->{child_node.id}")
                # else: # Points are coincident, maybe add just the child sphere?
                #     print(f"    -> Warning: Coincident points for segment {parent_node.id}->{child_node.id}")
                #     pass # Sphere added below

            except Exception as e:
                print(f"    -> Warning: Failed to create tube for segment {parent_node.id}->{child_node.id}: {e}")

            # --- Add Sphere at Child Node (Optional but good for junctions) ---
            # You could rely solely on tube capping, but explicit spheres are safer
            # if child_node.r > 1e-6: # Only add sphere if it has radius
            #     child_sphere = pv.Sphere(center=p2, radius=child_node.r)
            #     primitives.append(child_sphere)

            # Mark child as processed and recurse
            processed_nodes.add(child_node.id)
            process_node_recursive(child_node) # Recurse AFTER processing segment

    # Start traversal from the root
    process_node_recursive(root)

    if not primitives:
        print("  -> ERROR: No primitives were generated.")
        return None

    # Combine all primitives into one PolyData object
    print(f"  Concatenating {len(primitives)} primitives...")
    try:
        # Use pyvista.merge - more robust for list of meshes
        combined_mesh = pv.merge(primitives)
        if combined_mesh is None or combined_mesh.n_points == 0:
             print("  -> ERROR: Merging primitives resulted in empty mesh.")
             return None
    except Exception as e:
         print(f"  -> ERROR: Failed to merge primitives: {e}")
         traceback.print_exc()
         return None

    print(f"  Primitive mesh created: {combined_mesh.n_points} points, {combined_mesh.n_cells} cells")
    return combined_mesh


# --- Main Meshing Function ---

def generate_mesh_pyvista(
    swc_filepath: str,
    voxel_size: float | None = None # Allow overriding voxel size
) -> trimesh.Trimesh | None:
    """
    Generates a mesh from SWC using PyVista's voxelize and extract_surface.

    Args:
        swc_filepath: Path to the input SWC file.
        voxel_size: The size of the voxels for grid generation. If None,
                    it's estimated based on minimum radius.

    Returns:
        The final Trimesh object or None if failed.
    """
    print(f"Generating mesh from: {swc_filepath} using PyVista...")

    # 1. Load SWC using your Neuron class
    try:
        neuron = Neuron(swc_filepath)
        print(f"  Neuron loaded using Neuron class. Root: {neuron.root_node.id}, Nodes: {len(neuron.nodes)}")
        # Get all radii to estimate voxel size if not provided
        all_radii = [node.r for node in neuron.nodes if node.r > 1e-6]
        if not all_radii:
             print("  -> ERROR: Neuron contains no nodes with positive radius.")
             return None
        min_radius = min(all_radii)
    except Exception as e:
        print(f"  -> ERROR: Failed to load SWC file with Neuron class: {e}")
        traceback.print_exc()
        return None

    # 2. Determine Voxel Size (Same as before)
    if voxel_size is None:
        voxel_size = min_radius * DEFAULT_VOXEL_SIZE_FACTOR
        voxel_size = max(MIN_VOXEL_SIZE, min(MAX_VOXEL_SIZE, voxel_size)) # Clamp
    print(f"  Using voxel size: {voxel_size:.4f} (estimated from min radius: {min_radius:.4f})")


    # 3. Create Primitive Representation using your Neuron object
    primitive_mesh = create_pyvista_primitives(neuron)
    if primitive_mesh is None:
        # Error message printed within the helper function
        return None

    # 4. Voxelize the Primitive Mesh (Same as before)
    print(f"  Voxelizing primitive mesh with voxel size {voxel_size}...")
    try:
        voxel_grid = pv.voxelize(primitive_mesh, density=voxel_size, check_surface=False)
        print(f"  Voxel grid created: Dimensions {voxel_grid.dimensions}")
    except Exception as e:
        print(f"  -> ERROR: PyVista voxelization failed: {e}")
        traceback.print_exc()
        return None

    # 5. Extract Isosurface (Same as before)
    print("  Extracting surface (Marching Cubes)...")
    try:
        surface = voxel_grid.extract_surface(progress_bar=True)
        if surface.n_points == 0 or surface.n_faces == 0:
             print("  -> ERROR: Surface extraction resulted in empty mesh.")
             return None
        print(f"  Surface extracted: {surface.n_points} points, {surface.n_faces} faces")
    except Exception as e:
        print(f"  -> ERROR: Surface extraction failed: {e}")
        traceback.print_exc()
        return None

    # 6. Optional Post-Processing (Smoothing) (Same as before)
    print(f"  Smoothing surface ({SMOOTHING_ITERATIONS} iterations)...")
    try:
        surface.smooth(n_iter=SMOOTHING_ITERATIONS, relaxation_factor=SMOOTHING_RELAXATION, inplace=True)
        print(f"  Surface smoothed.")
    except Exception as e:
        print(f"  -> Warning: Smoothing failed: {e}")


    # 7. Convert PyVista Mesh to Trimesh (Same as before)
    print("  Converting to Trimesh object...")
    try:
        faces_pv = surface.faces # Get face array (e.g., [4, 0, 1, 2, 4, 1, 2, 3, ...])
        # Check if it's already simple triangles or needs reshaping
        if faces_pv.size % 4 == 0 and np.all(faces_pv.reshape(-1, 4)[:, 0] == 3):
             # Standard PyVista format (N=3, v0, v1, v2)
             faces = faces_pv.reshape(-1, 4)[:, 1:]
        elif faces_pv.size % 3 == 0:
             # Might already be simple triangles (n_faces, 3)
             faces = faces_pv.reshape(-1, 3)
        else:
             raise ValueError("Unrecognized PyVista face array format.")

        final_mesh = trimesh.Trimesh(vertices=surface.points, faces=faces)
        if final_mesh.is_empty:
             print("  -> ERROR: Final Trimesh object is empty.")
             return None
        print("  Performing final processing...")
        final_mesh.process(validate=True) # Attempt basic processing
        if not final_mesh.is_volume:
             print("  -> Warning: Final mesh not a volume. Attempting fill_holes.")
             final_mesh.fill_holes()
             final_mesh.process(validate=True) # Reprocess after filling

    except Exception as e:
        print(f"  -> ERROR: Failed to convert or process final Trimesh mesh: {e}")
        traceback.print_exc()
        return None

    print(f"PyVista mesh generation complete. Final Vertices: {len(final_mesh.vertices)}, Faces: {len(final_mesh.faces)}")
    return final_mesh

swc_file = "H16-06-013-05-03-04_597701859_m_DendriteAxon.CNG.swc"
generated_mesh = generate_mesh_pyvista(swc_file)
generated_mesh.export("neuron_pv.glb")
