"""
Reference data endpoints for lookup values.

Provides distinct values for filter dropdowns.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.models.trig import Trig
from api.utils.cache_decorator import cached

router = APIRouter()


class ReferenceValue(BaseModel):
    """A single reference value for filtering."""

    value: str
    label: str


class ReferenceValuesResponse(BaseModel):
    """Response containing a list of reference values."""

    values: list[ReferenceValue]


@router.get(
    "/historic-use",
    response_model=ReferenceValuesResponse,
    openapi_extra=openapi_lifecycle("beta", note="List distinct historic use values"),
)
@cached(resource_type="reference_historic_use", ttl=86400)  # 24 hours
def list_historic_use_values(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List all distinct historic_use values from the trig table.

    Values are sorted alphabetically for display in filter UIs.
    """
    # Get distinct values, excluding soft-deleted trigs
    values = (
        db.query(distinct(Trig.historic_use))
        .filter(Trig.status_id < 90)
        .order_by(Trig.historic_use)
        .all()
    )

    return ReferenceValuesResponse(
        values=[
            ReferenceValue(value=v[0] or "", label=v[0] or "(Not specified)")
            for v in values
            if v[0] is not None
        ]
    )


@router.get(
    "/current-use",
    response_model=ReferenceValuesResponse,
    openapi_extra=openapi_lifecycle("beta", note="List distinct current use values"),
)
@cached(resource_type="reference_current_use", ttl=86400)  # 24 hours
def list_current_use_values(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List all distinct current_use values from the trig table.

    Values are sorted alphabetically for display in filter UIs.
    """
    # Get distinct values, excluding soft-deleted trigs
    values = (
        db.query(distinct(Trig.current_use))
        .filter(Trig.status_id < 90)
        .order_by(Trig.current_use)
        .all()
    )

    return ReferenceValuesResponse(
        values=[
            ReferenceValue(value=v[0] or "", label=v[0] or "(Not specified)")
            for v in values
            if v[0] is not None
        ]
    )
