"""
Shared trig filter parameters for the trig list, map points and download endpoints.

Keeping the filter set in one FastAPI dependency means every endpoint that
lists trigs accepts the same query parameters with the same meaning, and the
CRUD layer receives them in one consistent shape.
"""

from typing import Any, Optional

from fastapi import HTTPException, Query
from sqlalchemy.orm import Session

from api.models.user import User


def _split_csv(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _split_csv_ints(value: Optional[str], param: str) -> Optional[list[int]]:
    items = _split_csv(value)
    if items is None:
        return None
    try:
        return [int(item) for item in items]
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"{param} must be a comma-separated list of IDs"
        )


class TrigFilters:
    """Query parameters that narrow a set of trigs. Use as `Depends()`."""

    def __init__(
        self,
        name: Optional[str] = Query(None, description="Filter by trig name (contains)"),
        county: Optional[str] = Query(None, description="Filter by county (exact)"),
        lat: Optional[float] = Query(None, description="Centre latitude (WGS84)"),
        lon: Optional[float] = Query(None, description="Centre longitude (WGS84)"),
        max_km: Optional[float] = Query(
            None, ge=0, description="Max distance from centre (km)"
        ),
        types: Optional[str] = Query(
            None,
            description="Comma-separated type codes to include (e.g., 'HOTINE,FBM')",
        ),
        categories: Optional[str] = Query(
            None,
            description="Comma-separated category codes to include (e.g., 'PILLAR,FBM')",
        ),
        area_id: Optional[int] = Query(
            None, description="Filter to trigpoints within the specified area"
        ),
        area_ids: Optional[str] = Query(
            None, description="Comma-separated area IDs (multi-select)"
        ),
        historic_use: Optional[str] = Query(
            None, description="Comma-separated historic use values to include"
        ),
        current_use: Optional[str] = Query(
            None, description="Comma-separated current use values to include"
        ),
        conditions: Optional[str] = Query(
            None, description="Comma-separated condition codes to include"
        ),
        variants: Optional[str] = Query(
            None,
            description=(
                "Comma-separated variant codes to include "
                "(e.g., 'CONCRETE_RING,BRONZE_RING'); NOT_RECORDED includes "
                "trigs with no variant"
            ),
        ),
        logged_by: Optional[int] = Query(
            None,
            description=(
                "User ID whose logs the log filters (only_found, exclude_found, "
                "logged_conditions) and the 'logged' sort refer to. "
                "Defaults to the authenticated user."
            ),
        ),
        only_found: bool = Query(
            False, description="Include only trigpoints logged by the log user"
        ),
        exclude_found: bool = Query(
            False, description="Exclude trigpoints logged by the log user"
        ),
        logged_conditions: Optional[str] = Query(
            None,
            description=(
                "Comma-separated condition codes - with only_found, show trigs "
                "the log user logged with these conditions"
            ),
        ),
        in_lists: Optional[str] = Query(
            None,
            description=(
                "Comma-separated trig list IDs - include only trigs in any of "
                "them. Each list must be visible to the caller."
            ),
        ),
        not_in_lists: Optional[str] = Query(
            None,
            description=(
                "Comma-separated trig list IDs - exclude trigs in any of them. "
                "Each list must be visible to the caller."
            ),
        ),
    ):
        self.name = name
        self.county = county
        self.lat = lat
        self.lon = lon
        self.max_km = max_km
        self.types = _split_csv(types)
        self.categories = _split_csv(categories)
        self.area_id = area_id
        self.area_ids = _split_csv_ints(area_ids, "area_ids")
        self.historic_use = _split_csv(historic_use)
        self.current_use = _split_csv(current_use)
        self.conditions = _split_csv(conditions)
        self.variants = _split_csv(variants)
        self.logged_by = logged_by
        self.only_found = only_found
        self.exclude_found = exclude_found
        self.logged_conditions = _split_csv(logged_conditions)
        self.in_lists = _split_csv_ints(in_lists, "in_lists")
        self.not_in_lists = _split_csv_ints(not_in_lists, "not_in_lists")

    @property
    def has_centre(self) -> bool:
        return self.lat is not None and self.lon is not None

    @property
    def cacheable(self) -> bool:
        """
        False when results depend on trig list contents. List edits don't
        invalidate the trig caches, so those responses mustn't be cached.
        """
        return not (self.in_lists or self.not_in_lists)

    def cache_key_params(self) -> dict[str, Any]:
        """Stable, JSON-serialisable form for cache-key hashing."""
        return {k: v for k, v in vars(self).items() if v is not None and v is not False}

    def query_string_parts(self) -> list[str]:
        """`key=value` pairs for rebuilding pagination links."""
        parts = []
        for key, value in self.cache_key_params().items():
            if isinstance(value, list):
                value = ",".join(str(v) for v in value)
            elif value is True:
                value = "true"
            parts.append(f"{key}={value}")
        return parts

    def resolve_log_user_id(
        self, db: Session, current_user: Optional[User]
    ) -> Optional[int]:
        """
        The user the log filters refer to: `logged_by` if given (404 if no such
        user), otherwise the authenticated user, otherwise nobody.
        """
        if self.logged_by is not None:
            exists = db.query(User.id).filter(User.id == self.logged_by).first()
            if not exists:
                raise HTTPException(status_code=404, detail="logged_by user not found")
            return self.logged_by
        if current_user is not None:
            return int(current_user.id)
        return None

    def check_list_access(self, db: Session, current_user: Optional[User]) -> None:
        """404 for any list filter naming a list the caller can't see."""
        from api.api.v1.endpoints.lists import require_list_visible

        for list_id in (self.in_lists or []) + (self.not_in_lists or []):
            require_list_visible(list_id, db, current_user)

    def crud_kwargs(self, log_user_id: Optional[int]) -> dict[str, Any]:
        """Keyword arguments for the trig CRUD list/count/points functions."""
        return {
            "name": self.name,
            "county": self.county,
            "center_lat": self.lat,
            "center_lon": self.lon,
            "max_km": self.max_km,
            "type_codes": self.types,
            "category_codes": self.categories,
            "exclude_found_by_user_id": (log_user_id if self.exclude_found else None),
            "only_found_by_user_id": log_user_id if self.only_found else None,
            "exclude_soft_deleted": True,  # Always exclude status_id >= 90
            "area_id": self.area_id,
            "area_ids": self.area_ids,
            "historic_use": self.historic_use,
            "current_use": self.current_use,
            "conditions": self.conditions,
            "variant_codes": self.variants,
            "logged_conditions": self.logged_conditions,
            "in_list_ids": self.in_lists,
            "not_in_list_ids": self.not_in_lists,
        }


TRIG_ORDER_KEYS = {"id", "name", "distance", "height", "score", "logged"}


def validate_trig_order(order: Optional[str], log_user_id: Optional[int]) -> None:
    """Reject unknown sort keys, and 'logged' when there's no log user."""
    if not order:
        return
    key = order.lstrip("-")
    if key not in TRIG_ORDER_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"order must be one of {', '.join(sorted(TRIG_ORDER_KEYS))} "
            "(prefix with - to reverse)",
        )
    if key == "logged" and log_user_id is None:
        raise HTTPException(
            status_code=422,
            detail="order=logged needs logged_by, or an authenticated user",
        )
