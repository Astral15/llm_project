from uuid import uuid4
import hashlib

import boto3
from botocore.client import Config
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.image import Image  # you will create this model

router = APIRouter(prefix="/images", tags=["images"])


def get_s3_client():
    """
    Create a boto3 client for MinIO (S3-compatible).
    """
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket_exists(s3_client, bucket_name: str):
    """
    Make sure the bucket exists. If not, create it.
    Called lazily on first upload.
    """
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except Exception:
        # If head_bucket fails (e.g., 404), try to create the bucket
        s3_client.create_bucket(Bucket=bucket_name)


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload an image to MinIO with per-user deduplication.

    - Only accepts image/* mime types.
    - Computes SHA256 hash of the content.
    - If the same user has already uploaded an image with the same hash,
      we DO NOT upload again; we just return the existing Image record.
    - Otherwise, we store the object in MinIO and create an Image row.
    """
    settings = get_settings()

    # 1) Basic validation
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image uploads are allowed",
        )

    # Read all bytes (OK for typical image sizes in this project)
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    # 2) Compute content hash for deduplication
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    # 3) Check if this user already has this image
    existing = (
        db.query(Image)
        .filter(
            Image.user_id == current_user.id,
            Image.content_hash == content_hash,
        )
        .first()
    )
    if existing:
        # Per-user dedup hit: return existing record, no new upload
        return {
            "id": existing.id,
            "url": existing.url,
            "content_hash": existing.content_hash,
            "deduplicated": True,
        }

    # 4) Prepare S3 / MinIO client and bucket
    s3_client = get_s3_client()
    bucket_name = settings.MINIO_BUCKET
    ensure_bucket_exists(s3_client, bucket_name)

    # 5) Build object key: group by user + keep extension if any
    original_filename = file.filename or "upload"
    # simple extension extraction
    dot_idx = original_filename.rfind(".")
    ext = original_filename[dot_idx:] if dot_idx != -1 else ""
    object_key = f"user_{current_user.id}/{content_hash}_{uuid4().hex}{ext}"

    # 6) Upload to MinIO
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_bytes,
            ContentType=file.content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload to MinIO: {e}",
        )

    # 7) Construct URL (path-style, works inside Docker network)
    object_url = f"{settings.MINIO_ENDPOINT}/{bucket_name}/{object_key}"

    # 8) Persist Image metadata in DB
    image = Image(
        user_id=current_user.id,
        storage_key=object_key,
        url=object_url,
        content_hash=content_hash,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    # 9) Return response
    return {
        "id": image.id,
        "url": image.url,
        "content_hash": image.content_hash,
        "deduplicated": False,
    }
