"""
Reference data endpoints for lookup values.

Provides distinct values for filter dropdowns.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import trig_use as trig_use_crud
from api.crud.trig_use import TrigUseKind, TrigUseModel
from api.models.trig_variant import TrigVariant
from api.utils.cache_decorator import cached

router = APIRouter()


class ReferenceValue(BaseModel):
    """A single reference value for filtering."""

    value: str
    label: str


class ReferenceValuesResponse(BaseModel):
    """Response containing a list of reference values."""

    values: list[ReferenceValue]


def _use_values(values: list[TrigUseModel]) -> ReferenceValuesResponse:
    return ReferenceValuesResponse(
        values=[ReferenceValue(value=str(v.name), label=str(v.name)) for v in values]
    )


@router.get(
    "/historic-use",
    response_model=ReferenceValuesResponse,
    openapi_extra=openapi_lifecycle("beta", note="List historic use values"),
)
@cached(resource_type="reference_historic_use", ttl=86400)  # 24 hours
def list_historic_use_values(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List the historic use values, in the order set in the admin screen.
    """
    return _use_values(trig_use_crud.get_all(db, TrigUseKind.HISTORIC))


@router.get(
    "/current-use",
    response_model=ReferenceValuesResponse,
    openapi_extra=openapi_lifecycle("beta", note="List current use values"),
)
@cached(resource_type="reference_current_use", ttl=86400)  # 24 hours
def list_current_use_values(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List the current ("recent") use values, in the order set in the admin
    screen.
    """
    return _use_values(trig_use_crud.get_all(db, TrigUseKind.CURRENT))


class VariantGroup(BaseModel):
    """A variant group and its values (see trig_variant)."""

    code: str
    name: str
    values: list[ReferenceValue]


@router.get(
    "/variant-groups",
    response_model=list[VariantGroup],
    openapi_extra=openapi_lifecycle(
        "beta", note="List trig variant groups and their values"
    ),
)
@cached(resource_type="reference_variant_groups", ttl=86400)  # 24 hours
def list_variant_groups(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List variant groups (e.g. Detector material) with their values in display
    order. Value is the variant code (used by the `variants` filter); label is
    its display name. Types opt in to a group via trig_type.variant_group.
    """
    variants = (
        db.query(TrigVariant)
        .order_by(TrigVariant.group_name, TrigVariant.sort_order)
        .all()
    )

    groups: dict[str, VariantGroup] = {}
    for v in variants:
        group = groups.setdefault(
            str(v.group_code),
            VariantGroup(code=str(v.group_code), name=str(v.group_name), values=[]),
        )
        group.values.append(ReferenceValue(value=str(v.code), label=str(v.name)))
    return list(groups.values())
