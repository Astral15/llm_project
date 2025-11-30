import hashlib
import json
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from openai import OpenAI

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.models.image import Image
from app.models.llm import LLMRequest, LLMResponse

router = APIRouter(prefix="/llm", tags=["llm"])

settings = get_settings()
if not settings.OPENAI_API_KEY:
    # You can also just let it be None and raise later
    client: Optional[OpenAI] = None
else:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)


class FieldSpec(BaseModel):
    name: str
    type: Literal["string", "number"]


class StructuredRequest(BaseModel):
    prompt: str
    fields: List[FieldSpec]
    image_id: Optional[int] = None


class StructuredResponse(BaseModel):
    data: Dict[str, Any]
    from_cache: bool = False


def build_json_schema(fields: List[FieldSpec]) -> Dict[str, Any]:
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for f in fields:
        if f.type == "string":
            schema_type = "string"
        else:
            schema_type = "number"

        properties[f.name] = {"type": schema_type}
        required.append(f.name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def compute_cache_key(
    prompt: str,
    fields: List[FieldSpec],
    image_hash: Optional[str],
) -> str:
    fields_payload = [{"name": f.name, "type": f.type} for f in sorted(fields, key=lambda x: x.name)]
    payload = {
        "prompt": prompt,
        "fields": fields_payload,
        "image_hash": image_hash,
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def coerce_response_types(
    data: Dict[str, Any],
    fields: List[FieldSpec],
) -> Dict[str, Any]:
    """
    Ensure each field is present and type-correct.
    Strings -> str, numbers -> float (or int when clean).
    """
    result: Dict[str, Any] = {}

    for f in fields:
        if f.name not in data:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM missing field '{f.name}' in response",
            )
        raw_value = data[f.name]

        if f.type == "string":
            result[f.name] = str(raw_value)
        else:
            # Try to parse as number
            try:
                # accept strings like "1912" or "1912.0"
                num = float(raw_value)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"LLM returned non-numeric value for field '{f.name}': {raw_value}",
                )

            # You can decide whether to keep as float or cast to int if whole
            if num.is_integer():
                result[f.name] = int(num)
            else:
                result[f.name] = num

    return result


def call_structured_llm(
    prompt: str,
    fields: List[FieldSpec],
    image_url: Optional[str],
) -> Dict[str, Any]:
    """
    Call OpenAI with a JSON schema for structured output.
    We just stuff the image URL into the text prompt for now.
    """
    if client is None:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server.",
        )

    schema = build_json_schema(fields)

    instructions = (
        "You are a helpful assistant that returns ONLY a JSON object obeying the given schema.\n"
        "Do not include any extra keys. Do not include explanations.\n"
    )

    if image_url:
        instructions += f"\nYou are also given an image at this URL: {image_url}\n"
        instructions += "Use both the prompt and the image to fill the fields.\n"

    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": prompt},
    ]

    # New OpenAI client (>=1.0) style
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "StructuredOutput",
                "schema": schema,
                "strict": True,
            },
        },
    )

    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM returned invalid JSON.",
        )


@router.post("/structured", response_model=StructuredResponse)
def get_structured_response(
    body: StructuredRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Main endpoint:

    - Validates fields
    - Optionally loads image + hash
    - Computes cache key
    - Returns cached result if available
    - Otherwise calls LLM, validates/coerces types, stores in DB, and returns.
    """
    if not body.fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field is required.",
        )

    # Ensure unique field names
    names = [f.name for f in body.fields]
    if len(names) != len(set(names)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field names must be unique.",
        )

    # Load image and hash (if provided)
    image_url: Optional[str] = None
    image_hash: Optional[str] = None

    if body.image_id is not None:
        image = (
            db.query(Image)
            .filter(
                Image.id == body.image_id,
                Image.user_id == current_user.id,
            )
            .first()
        )
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found for this user.",
            )
        image_url = image.url
        image_hash = image.content_hash

    # Compute cache key for (prompt + fields + image_hash)
    cache_key = compute_cache_key(body.prompt, body.fields, image_hash)

    # Try cache: find any previous response with same cache_key
    cached_request = (
        db.query(LLMRequest)
        .filter(LLMRequest.cache_key == cache_key)
        .order_by(LLMRequest.created_at.desc())
        .first()
    )
    if cached_request and cached_request.responses:
        # Take the latest response for this request
        latest_resp = sorted(
            cached_request.responses,
            key=lambda r: r.created_at,
            reverse=True,
        )[0]
        return StructuredResponse(
            data=latest_resp.validated_response,
            from_cache=True,
        )

    # No cache → call LLM
    raw = call_structured_llm(body.prompt, body.fields, image_url)
    validated = coerce_response_types(raw, body.fields)

    # Persist request & response
    req = LLMRequest(
        user_id=current_user.id,
        prompt=body.prompt,
        field_structure=[f.model_dump() for f in body.fields],
        image_id=body.image_id,
        cache_key=cache_key,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    resp = LLMResponse(
        request_id=req.id,
        raw_response=raw,
        validated_response=validated,
    )
    db.add(resp)
    db.commit()
    db.refresh(resp)

    return StructuredResponse(
        data=validated,
        from_cache=False,
    )
