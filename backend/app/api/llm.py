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
from app.models.image import Image
from app.models.user import User

from google import genai
from google.genai import types

log = logging.getLogger(__name__)
router = APIRouter(prefix="/llm", tags=["llm"])

s = get_settings()
if not s.GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set")

GEMINI_MODEL = s.GEMINI_MODEL_NAME or "gemini-2.0-flash"
gemini_client = genai.Client(api_key=s.GEMINI_API_KEY)

FieldType = Literal["string", "number"]

class FieldSpec(BaseModel):
    name: str = Field(..., description="Field name to extract")
    type: FieldType = Field(..., description="string | number")

class LLMStructuredRequest(BaseModel):
    prompt: str
    fields: List[FieldSpec]
    image_id: Optional[int] = None

class LLMStructuredResponse(BaseModel):
    data: Dict[str, Any]
    from_cache: bool = False  # hook for future caching

def _s3():
    return boto3.client(
        "s3",
        endpoint_url=s.S3_ENDPOINT,
        aws_access_key_id=s.S3_ACCESS_KEY,
        aws_secret_access_key=s.S3_SECRET_KEY,
    )

def _build_schema(fields: List[FieldSpec]) -> dict:
    props: Dict[str, Any] = {}
    req: List[str] = []
    for f in fields:
        t = "STRING" if f.type == "string" else "NUMBER"
        props[f.name] = {"type": t}
        req.append(f.name)
    return {"type": "OBJECT", "properties": props, "required": req}

def _load_image(db: Session, user_id: int, image_id: int) -> Optional[Tuple[bytes, str]]:
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        log.warning("image_id=%s not found", image_id)
        return None
    if img.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Image does not belong to user")

    bucket = s.MINIO_BUCKET
    try:
        key = img.url.split(f"/{bucket}/", 1)[1]
    except Exception:
        log.error("Cannot parse key from url=%s", img.url)
        return None

    cli = _s3()
    obj = cli.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()
    mime = obj.get("ContentType") or "image/png"
    return data, mime

def _call_llm(prompt: str, fields: List[FieldSpec], img: Optional[Tuple[bytes, str]]) -> Dict[str, Any]:
    schema = _build_schema(fields)
    parts: List[types.Part] = [types.Part(text=prompt)]

    if img:
        data, mime = img
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))

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
        log.exception("Gemini call failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Gemini call failed: {e}")

    parsed = getattr(resp, "parsed", None)
    if isinstance(parsed, dict):
        return parsed

    text = (getattr(resp, "text", "") or "").strip()
    if not text:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Empty LLM response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.error("Non-JSON LLM response: %s", text[:200])
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "LLM returned non-JSON output")

@router.post("/structured", response_model=LLMStructuredResponse)
def get_structured_response(
    body: LLMStructuredRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    img: Optional[Tuple[bytes, str]] = None
    if body.image_id is not None:
        img = _load_image(db, current_user.id, body.image_id)
        if img is None:
            raise HTTPException(400, "Image not found or cannot be loaded")

    data = _call_llm(body.prompt, body.fields, img)
    # from_cache = False for now; hook for later
    return LLMStructuredResponse(data=data, from_cache=False)
