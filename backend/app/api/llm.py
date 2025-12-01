from __future__ import annotations

import json, logging, hashlib
from typing import Any, Dict, List, Literal, Optional, Tuple

import boto3
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.image import Image
from app.models.llm import LLMRequest, LLMResponse
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
    from_cache: bool = False  # now actually used

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

def _load_image(db: Session, user_id: int, image_id: int) -> Optional[Tuple[bytes, str, Optional[str]]]:
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
    return data, mime, img.content_hash

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

def _cache_key(prompt: str, fields: List[FieldSpec], image_hash: Optional[str]) -> str:
    # small, deterministic payload; same key across users for same prompt+fields+image
    payload = {
        "p": prompt,
        "f": [{"n": f.name, "t": f.type} for f in fields],
        "i": image_hash,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

def _get_cached(db: Session, ck: str) -> Optional[Dict[str, Any]]:
    req = db.query(LLMRequest).filter(LLMRequest.cache_key == ck).order_by(LLMRequest.id.desc()).first()
    if not req:
        return None
    resp = db.query(LLMResponse).filter(LLMResponse.request_id == req.id).order_by(LLMResponse.id.desc()).first()
    return None if not resp else resp.validated_response

def _store_cache(
    db: Session,
    user_id: int,
    body: LLMStructuredRequest,
    fields: List[FieldSpec],
    cache_key: str,
    data: Dict[str, Any],
) -> None:
    # raw_response and validated_response are the same for now; hook for future validation layer
    req = LLMRequest(
        user_id=user_id,
        prompt=body.prompt,
        field_structure=[f.model_dump() for f in fields],
        image_id=body.image_id,
        cache_key=cache_key,
    )
    db.add(req)
    db.flush()  # assign req.id without committing yet

    resp = LLMResponse(
        request_id=req.id,
        raw_response=data,
        validated_response=data,
    )
    db.add(resp)
    db.commit()

@router.post("/structured", response_model=LLMStructuredResponse)
def get_structured_response(
    body: LLMStructuredRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    img_bytes: Optional[Tuple[bytes, str]] = None
    img_hash: Optional[str] = None

    if body.image_id is not None:
        loaded = _load_image(db, current_user.id, body.image_id)
        if loaded is None:
            raise HTTPException(400, "Image not found or cannot be loaded")
        data, mime, img_hash = loaded
        img_bytes = (data, mime)

    # build cache key across ALL users for identical (prompt, fields, image_bytes)
    ck = _cache_key(body.prompt, body.fields, img_hash)

    cached = _get_cached(db, ck)
    if cached is not None:
        return LLMStructuredResponse(data=cached, from_cache=True)

    data = _call_llm(body.prompt, body.fields, img_bytes)
    _store_cache(db, current_user.id, body, body.fields, ck, data)

    return LLMStructuredResponse(data=data, from_cache=False)
