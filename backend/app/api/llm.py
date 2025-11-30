# backend/app/api/llm.py

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional, Tuple

import boto3
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.models.image import Image

from google import genai
from google.genai import types

log = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Config / client
# --------------------------------------------------------------------

settings = get_settings()

if not getattr(settings, "GEMINI_API_KEY", None):
    raise RuntimeError("GEMINI_API_KEY is not set in environment / .env")

GEMINI_MODEL = getattr(settings, "GEMINI_MODEL_NAME", None) or "gemini-2.0-flash"

gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

router = APIRouter(prefix="/llm", tags=["llm"])

# --------------------------------------------------------------------
# Pydantic models
# --------------------------------------------------------------------

FieldType = Literal["string", "number"]


class FieldSpec(BaseModel):
    name: str = Field(..., description="Field name to extract")
    type: FieldType = Field(..., description="Type of the field: string or number")


class LLMStructuredRequest(BaseModel):
    prompt: str
    fields: List[FieldSpec]
    image_id: Optional[int] = None  # optional: link to uploaded image


class LLMStructuredResponse(BaseModel):
    data: Dict[str, Any]
    from_cache: bool = False  # keep for possible future caching


# --------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------

def _s3_client():
    """
    MinIO S3 client.

    Prefers S3_* vars, falls back to MINIO_ROOT_*.
    """
    access_key = getattr(settings, "S3_ACCESS_KEY", None) or settings.MINIO_ROOT_USER
    secret_key = getattr(settings, "S3_SECRET_KEY", None) or settings.MINIO_ROOT_PASSWORD

    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

def build_response_schema(fields: List[FieldSpec]) -> dict:
    """
    Build a JSON schema-like structure for Gemini response_schema.
    Types use STRING / NUMBER as Gemini expects.
    """
    props: Dict[str, Any] = {}
    required: List[str] = []

    for f in fields:
        t = "STRING" if f.type == "string" else "NUMBER"
        props[f.name] = {"type": t}
        required.append(f.name)

    return {
        "type": "OBJECT",
        "properties": props,
        "required": required,
    }


def load_image_content(
    db: Session,
    user_id: int,
    image_id: int,
) -> Optional[Tuple[bytes, str]]:
    """
    Load image bytes + mime type from MinIO for given user + image_id.

    Returns:
        (data, mime_type) or None if not found.
    Raises:
        HTTPException on unauthorized access.
    """
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        log.warning("image_id=%s not found", image_id)
        return None

    if img.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Image does not belong to this user",
        )

    bucket = settings.MINIO_BUCKET

    # img.url looks like: http://minio:9000/llm-images/user_1/...
    try:
        key = img.url.split(f"/{bucket}/", 1)[1]
    except Exception:
        log.error("Failed to parse S3 key from url=%s", img.url)
        return None

    s3 = _s3_client()
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()
    mime = obj.get("ContentType") or "image/png"

    log.info(
        "Loaded image bytes: image_id=%s user_id=%s size=%d mime=%s",
        image_id,
        user_id,
        len(data),
        mime,
    )
    return data, mime


def call_structured_llm(
    prompt: str,
    fields: List[FieldSpec],
    image_bytes: Optional[bytes],
    image_mime: Optional[str],
) -> Dict[str, Any]:
    """
    Call Gemini with text (+ optional image) and request JSON matching
    the schema built from `fields`.
    """

    schema = build_response_schema(fields)

    parts: List[types.Part] = [types.Part.from_text(prompt)]

    if image_bytes is not None:
        mt = image_mime or "image/png"
        log.info("Calling Gemini with image, mime=%s, bytes=%d", mt, len(image_bytes))
        parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mt))
    else:
        log.info("Calling Gemini without image (text-only)")

    contents = [types.Content(role="user", parts=parts)]

    try:
        resp = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
    except Exception as e:
        log.exception("Gemini API call failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API call failed: {e}",
        )

    # If response_schema is used, resp.parsed should already be a dict
    parsed = getattr(resp, "parsed", None)
    if isinstance(parsed, dict):
        return parsed

    text = (getattr(resp, "text", "") or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Empty response from Gemini",
        )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.error("Gemini returned non-JSON text: %s", text[:200])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini returned non-JSON output",
        )


# --------------------------------------------------------------------
# Public endpoint
# --------------------------------------------------------------------

@router.post(
    "/structured",
    response_model=LLMStructuredResponse,
)
def get_structured_response(
    body: LLMStructuredRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Main endpoint:

    - Optional: resolve image by id (must belong to current user) and load bytes from MinIO.
    - Call Gemini with (prompt, optional image) and field schema.
    - Return `{ "data": { ... }, "from_cache": false }`.
    """

    image_bytes: Optional[bytes] = None
    image_mime: Optional[str] = None

    if body.image_id is not None:
        content = load_image_content(db, current_user.id, body.image_id)
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image not found or could not be loaded",
            )
        image_bytes, image_mime = content

    data = call_structured_llm(body.prompt, body.fields, image_bytes, image_mime)

    return LLMStructuredResponse(data=data, from_cache=False)
