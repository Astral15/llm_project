import hashlib
from uuid import uuid4

import boto3
from botocore.client import Config
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.image import Image
from app.models.user import User

router = APIRouter(prefix="/images", tags=["images"])

def _s3_client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.MINIO_ENDPOINT,
        aws_access_key_id=s.MINIO_ROOT_USER,
        aws_secret_access_key=s.MINIO_ROOT_PASSWORD,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

def _ensure_bucket(s3, bucket: str):
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image/* uploads are allowed")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    h = hashlib.sha256(data).hexdigest()

    existing = (
        db.query(Image)
        .filter(Image.user_id == current_user.id, Image.content_hash == h)
        .first()
    )
    if existing:
        return {"id": existing.id, "url": existing.url, "content_hash": h, "deduplicated": True}

    s = get_settings()
    s3 = _s3_client()
    _ensure_bucket(s3, s.MINIO_BUCKET)

    name = file.filename or "upload"
    dot = name.rfind(".")
    ext = name[dot:] if dot != -1 else ""
    key = f"user_{current_user.id}/{h}_{uuid4().hex}{ext}"

    try:
        s3.put_object(
            Bucket=s.MINIO_BUCKET,
            Key=key,
            Body=data,
            ContentType=file.content_type,
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"MinIO upload failed: {e}")

    url = f"{s.MINIO_ENDPOINT}/{s.MINIO_BUCKET}/{key}"

    img = Image(user_id=current_user.id, storage_key=key, url=url, content_hash=h)
    db.add(img)
    db.commit()
    db.refresh(img)

    return {"id": img.id, "url": img.url, "content_hash": h, "deduplicated": False}
