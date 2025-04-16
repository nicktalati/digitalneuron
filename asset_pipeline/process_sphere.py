import argparse
import os
import sys
import trimesh
import boto3
from botocore.exceptions import NoCredentialsError, ClientError


LOD_TARGET_FACES = [4096, 2048, 1024, 512]

def simplify_mesh(initial_mesh: trimesh.Trimesh, target_faces: int) -> trimesh.Trimesh:
    print(f"Simplifying mesh to target approx {target_faces} faces...")
    try:
        simplified_mesh = initial_mesh.simplify_quadric_decimation(face_count=target_faces)
        print(f"Mesh created: {len(simplified_mesh.vertices)} vertices, {len(simplified_mesh.faces)} faces")
    except Exception as e:
        print(f"Error simplifying mesh: {e}")
        sys.exit(1)
    return simplified_mesh

def upload_mesh(mesh: trimesh.Trimesh, lod: int, base_filename: str, bucket_name: str) -> None:
    s3_key = f"lod_{lod}/{base_filename}.glb"
    try:
        s3_client = boto3.client("s3")
        print(f"Uploading LOD {lod} to s3://{bucket_name}/{s3_key} ...")
        export_data = mesh.export(file_type="glb")
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=export_data)
        print(f"LOD {lod} uploaded successfully")
    except NoCredentialsError:
        print("Error: AWS credentials not found.")
        sys.exit(1)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "NoSuchBucket":
            print(f"Error: S3 Bucket '{bucket_name}' not found.")
        elif error_code == "AccessDenied":
            print(f"Error: Access Denied when trying to upload to bucket '{bucket_name}'.")
        else:
            print(f"Error uploading to S3: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occured during upload: {e}")
        sys.exit(1)

def process_and_upload(input_glb_path, bucket_name):
    """
    Loads a GLB mech, creates low-detail LOD, uploads both to S3
    """
    if not os.path.exists(input_glb_path):
        print(f"Error: File not found at '{input_glb_path}'")
        sys.exit(1)

    print(f"Loading mesh from '{input_glb_path}'")

    try:
        mesh_lod0 = trimesh.load_mesh(input_glb_path)
        print(f"LOD 0 mesh loaded: {len(mesh_lod0.vertices)} vertices, {len(mesh_lod0.faces)} faces")
    except Exception as e:
        print(f"Error loading mesh: {e}")
        sys.exit(1)

    base_filename = os.path.splitext(os.path.basename(input_glb_path))[0]
    upload_mesh(mesh_lod0, 0, base_filename, bucket_name)

    for lod, target_faces in enumerate(LOD_TARGET_FACES):
        lod += 1
        mesh = simplify_mesh(mesh_lod0, target_faces)
        upload_mesh(mesh, lod, base_filename, bucket_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process 3D mesh into LODs and upload to S3")
    parser.add_argument("--input-file", required=True, help="Path to input GLB file")
    parser.add_argument("--bucket-name", required=True, help="Name of target bucket")

    args = parser.parse_args()

    process_and_upload(args.input_file, args.bucket_name)
