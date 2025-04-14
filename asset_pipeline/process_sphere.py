import argparse
import os
import sys
import trimesh
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

LOD1_TARGET_FACES = 1000

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

    print(f"Simplifying mesh to target approx {LOD1_TARGET_FACES} faces for LOD 1...")

    try:
        mesh_lod1 = mesh_lod0.simplify_quadric_decimation(face_count=LOD1_TARGET_FACES)
        print(f"LOD 1 mesh created: {len(mesh_lod1.vertices)} vertices, {len(mesh_lod1.faces)} faces")
    except Exception as e:
        print(f"Error simplifying mesh: {e}")
        sys.exit(1)

    base_filename = os.path.splitext(os.path.basename(input_glb_path))[0]
    s3_key_lod0 = f"lod_0/{base_filename}.glb"
    s3_key_lod1 = f"lod_1/{base_filename}.glb"

    print(f"Attempting to upload to S3 bucket: {bucket_name}...")
    try:
        s3_client = boto3.client("s3")

        print(f"Uploading LOD 0 to s3://{bucket_name}/{s3_key_lod0} ...")
        s3_client.upload_file(input_glb_path, bucket_name, s3_key_lod0)
        print("LOD 0 uploaded successfully")

        print(f"Uploading LOD 1 to s3://{bucket_name}/{s3_key_lod1} ...")
        export_data = mesh_lod1.export(file_type="glb")
        s3_client.put_object(Bucket=bucket_name, Key=s3_key_lod1, Body=export_data)
        print("LOD 1 uploaded successfully")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process 3D mesh into LODs and upload to S3")
    parser.add_argument("--input-file", required=True, help="Path to input GLB file")
    parser.add_argument("--bucket-name", required=True, help="Name of target bucket")

    args = parser.parse_args()

    process_and_upload(args.input_file, args.bucket_name)
