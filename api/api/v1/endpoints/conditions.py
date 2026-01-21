"""
Public endpoints for condition lookup data.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import condition as condition_crud
from api.schemas.condition import ConditionResponse
from api.utils.cache_decorator import cached

router = APIRouter()


@router.get(
    "",
    response_model=list[ConditionResponse],
    openapi_extra=openapi_lifecycle("beta", note="List all condition codes"),
)
@cached(
    resource_type="conditions", ttl=86400
)  # 24 hours - conditions don't change often
def list_conditions(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List all trigpoint condition codes.

    Conditions are ordered by sort_order. Each condition includes:
    - code: Single letter identifier (e.g., 'G' for Good)
    - name: Human-readable name
    - description: Detailed description
    - icon_file: Filename for the condition icon
    - trig_colour: Colour used for trig display
    - log_colour: Colour used for log display
    - similar_codes: Related condition codes
    - wiki_url: Link to wiki documentation
    - sort_order: Display ordering
    """
    conditions = condition_crud.get_all_conditions(db)
    return [ConditionResponse.model_validate(c) for c in conditions]


@router.get(
    "/{code}",
    response_model=ConditionResponse,
    openapi_extra=openapi_lifecycle("beta", note="Get a specific condition by code"),
)
@cached(resource_type="condition", ttl=86400)
def get_condition(
    code: str,
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Get a specific condition by its code.

    The code is case-insensitive (e.g., 'g', 'G' both work).
    """
    condition = condition_crud.get_condition_by_code(db, code.upper())
    if not condition:
        raise HTTPException(status_code=404, detail=f"Condition '{code}' not found")

    return ConditionResponse.model_validate(condition)
