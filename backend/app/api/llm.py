# backend/app/api/llm.py

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.models.image import Image  # you already use this in image upload

from google import genai
from google.genai import types

# --------------------------------------------------------------------
# Config / client
# --------------------------------------------------------------------

settings = get_settings()

if not settings.GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in environment / .env")

GEMINI_MODEL = settings.GEMINI_MODEL_NAME or "gemini-2.0-flash"

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


def build_response_schema(fields: List[FieldSpec]) -> dict:
    """
    Build a JSON schema-like structure for Gemini response_schema.
    Types here follow Gemini’s expected STRING / NUMBER enums.
    """
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for f in fields:
        if f.type == "string":
            field_type = "STRING"
        else:
            field_type = "NUMBER"

        properties[f.name] = {"type": field_type}
        required.append(f.name)

    return {
        "type": "OBJECT",
        "properties": properties,
        "required": required,
    }


def call_structured_llm(
    prompt: str,
    fields: List[FieldSpec],
    image_url: Optional[str],
) -> Dict[str, Any]:
    """
    Call Gemini and ask it to return JSON that matches the schema generated
    from `fields`. We use response_mime_type=application/json so
    response.text should already be JSON.
    """

    schema = build_response_schema(fields)

    user_text = prompt
    if image_url:
        user_text += (
            "\n\nYou may also use this image (describe or interpret it if useful):\n"
            f"{image_url}"
        )

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API call failed: {e}",
        )

    text = (response.text or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Empty response from Gemini",
        )

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # For debugging you could log `text`, but don’t expose it fully to clients.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini returned non-JSON output: {text[:200]}",
        )

    return data


def resolve_image_url(
    db: Session,
    current_user: User,
    image_id: Optional[int],
) -> Optional[str]:
    """
    If image_id is provided, look up the Image row and make sure it belongs
    to the user. Return its URL or raise HTTP 404/403 on problems.
    """
    if image_id is None:
        return None

    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    if image.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Image does not belong to this user",
        )

    return image.url


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

    - Optional: resolve image by id (must belong to current user).
    - Ask Gemini to return JSON with exactly the fields described in `body.fields`.
    - Return `{ "data": { ... }, "from_cache": false }`.
    """

    image_url = resolve_image_url(db, current_user, body.image_id)

    # (Optional caching could go here; for now we always call Gemini.)
    data = call_structured_llm(body.prompt, body.fields, image_url)

    return LLMStructuredResponse(data=data, from_cache=False)
