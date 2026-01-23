"""
Admin endpoints for OS Net station comparison.

Provides functionality to compare OS Net active GPS stations with
the database to identify differences and new/removed stations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.logging import get_logger
from api.models.user import User
from api.schemas.osnet import (
    SECTION_NAMES,
    DBStationData,
    OSNetComparisonResponse,
    OSNetStationData,
    StationDifferenceResponse,
)
from api.services.osnet_service import compare_osnet_with_db

logger = get_logger(__name__)
router = APIRouter()
ADMIN_SCOPE_DEPENDENCY = require_admin()


@router.get(
    "/comparison",
    response_model=OSNetComparisonResponse,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Compare OS Net active stations with database to identify differences.",
    ),
)
def get_osnet_comparison(
    force_refresh: bool = Query(
        False,
        description="Force refresh of OS Net data (bypass cache)",
    ),
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
    db: Session = Depends(get_db),
) -> OSNetComparisonResponse:
    """
    Compare OS Net active GPS stations with database active stations.

    This endpoint fetches the OS Net coordinates file from Ordnance Survey,
    compares it against active stations in the database, and returns any
    differences found.

    Differences include:
    - **new_in_osnet**: Stations in OS Net but not in the database
    - **missing_from_osnet**: Database stations not found in OS Net (may be destroyed)
    - **coordinate_mismatch**: Stations with coordinate differences > 5 metres
    - **unmatched_db**: Database active stations without stn_number_active set

    The OS Net data is cached for 1 hour. Use `force_refresh=true` to bypass cache.

    Requires `api:admin` scope.
    """
    logger.info(
        "OS Net comparison requested",
        extra={
            "admin_user_id": int(admin_user.id),
            "force_refresh": force_refresh,
        },
    )

    try:
        result = compare_osnet_with_db(db, force_refresh=force_refresh)
    except RuntimeError as e:
        logger.error("OS Net comparison failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch OS Net data: {e}",
        ) from e
    except Exception as e:
        logger.error("OS Net comparison error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during comparison",
        ) from e

    # Convert dataclasses to response models
    differences = [
        StationDifferenceResponse(
            station_code=d.station_code,
            difference_type=d.difference_type,
            description=d.description,
            osnet_data=OSNetStationData(**d.osnet_data) if d.osnet_data else None,
            db_data=DBStationData(**d.db_data) if d.db_data else None,
            distance_metres=d.distance_metres,
            osnet_section=d.osnet_section,
            osnet_section_name=(
                SECTION_NAMES.get(d.osnet_section) if d.osnet_section else None
            ),
        )
        for d in result.differences
    ]

    # Calculate summary counts
    new_in_osnet_count = sum(
        1 for d in differences if d.difference_type == "new_in_osnet"
    )
    missing_from_osnet_count = sum(
        1 for d in differences if d.difference_type == "missing_from_osnet"
    )
    coordinate_mismatch_count = sum(
        1 for d in differences if d.difference_type == "coordinate_mismatch"
    )
    unmatched_db_count = sum(
        1 for d in differences if d.difference_type == "unmatched_db"
    )
    destroyed_not_in_db_count = sum(
        1 for d in differences if d.difference_type == "destroyed_not_in_db"
    )
    legacy_not_in_db_count = sum(
        1 for d in differences if d.difference_type == "legacy_not_in_db"
    )

    logger.info(
        "OS Net comparison complete",
        extra={
            "osnet_count": result.osnet_count,
            "osnet_current": result.osnet_current_count,
            "osnet_legacy": result.osnet_legacy_count,
            "osnet_destroyed": result.osnet_destroyed_count,
            "db_count": result.db_count,
            "matched_count": result.matched_count,
            "differences_count": len(differences),
            "new_in_osnet": new_in_osnet_count,
            "missing_from_osnet": missing_from_osnet_count,
            "coordinate_mismatch": coordinate_mismatch_count,
            "unmatched_db": unmatched_db_count,
            "destroyed_not_in_db": destroyed_not_in_db_count,
            "legacy_not_in_db": legacy_not_in_db_count,
        },
    )

    return OSNetComparisonResponse(
        osnet_count=result.osnet_count,
        osnet_current_count=result.osnet_current_count,
        osnet_legacy_count=result.osnet_legacy_count,
        osnet_destroyed_count=result.osnet_destroyed_count,
        db_count=result.db_count,
        matched_count=result.matched_count,
        differences=differences,
        osnet_fetch_time=result.osnet_fetch_time,
        changelog_entries=result.changelog_entries,
        new_in_osnet_count=new_in_osnet_count,
        missing_from_osnet_count=missing_from_osnet_count,
        coordinate_mismatch_count=coordinate_mismatch_count,
        unmatched_db_count=unmatched_db_count,
        destroyed_not_in_db_count=destroyed_not_in_db_count,
        legacy_not_in_db_count=legacy_not_in_db_count,
    )


@router.post(
    "/cache/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Clear the OS Net data cache to force a fresh fetch on next comparison.",
    ),
)
def clear_osnet_cache(
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
) -> None:
    """
    Clear the OS Net data cache.

    Forces the next comparison request to fetch fresh data from Ordnance Survey.

    Requires `api:admin` scope.
    """
    from api.services.osnet_service import OSNetCache

    logger.info(
        "OS Net cache cleared",
        extra={"admin_user_id": int(admin_user.id)},
    )
    OSNetCache.get_instance().clear()
