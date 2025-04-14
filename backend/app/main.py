import os
import logging
import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Path, Query
from mangum import Mangum
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TILE_BUCKET_NAME = os.getenv("TILE_BUCKET_NAME")

URL_EXPIRATION = 3600

app = FastAPI(
    title="Digital Neuron Tile API",
    description="API to receive pre-signed URLs for mesh tiles",
    version="0.1.0"
)

s3_client = boto3.client("s3")

@app.get("/")
async def read_root():
    return {"message": "Digital Neuron Tile API is running."}

@app.get(
    "/api/v1/tile/{lod}/{tile_key}",
    summary="Get pre-signed URL for mesh tile"
)
async def get_tile_presigned_url(
    lod: int = Path(..., title="Level of Detail", description="LOD index (e.g. 0 for highest detail)", ge=0),
    tile_key: str = Path(..., title="Tile Key", description="Identifier for the tile (e.g. 'sphere')")
):
    if not TILE_BUCKET_NAME:
        logger.error("TILE_BUCKET_NAME environment variable is not set.")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: Tile bucket not specified."
        )
    s3_object_key = f"lod_{lod}/{tile_key}.glb"
    logger.info(f"Requesting pre-signed URL for object: {s3_object_key} in bucket: {TILE_BUCKET_NAME}")

    try:
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": TILE_BUCKET_NAME, "Key": s3_object_key},
            ExpiresIn=URL_EXPIRATION,
            HttpMethod="GET"
        )
        logger.info(f"Successfully generated pre-signed URL for {s3_object_key}")
        return {"tileUrl": presigned_url}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        logger.error(f"Boto3 ClientError generating URL for {s3_object_key}: {e} (Code: {error_code})")
        raise HTTPException(
            status_code=404,
            detail=f"Could not generate URL for tile '{tile_key}' at LOD {lod}. Check if tile exists and permissions are correct."
        )
    except Exception as e:
        logger.exception(f"Unexpected error generating URL for {s3_object_key}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal server error occured while generating the tile URL."
        )

handler = Mangum(app, lifespan="off")


if __name__ == "__main__":
    import uvicorn
    print("Running Uvicorn locally. Access docs at http://localhost:8000/docs")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
